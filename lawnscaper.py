#!/usr/bin/env python3

import os
import sys
import time
from tkinter import filedialog
from tkinter import Tk, Canvas, PhotoImage, Label, Frame, BOTH

class Lawnscaper(Frame):

	def __init__(self, argRoot):

		super().__init__()

		self.root = argRoot

		self.master.title("Lawnscaper")

		self.initialized = False

		self.pressing_m1 = False

		self.tile_size = 48

		# the game counts the border as tiles. store these offsets to make the top left coord (0, 0)
		self.spawn_x_offset = 1
		self.spawn_y_offset = 3

		self.map_width = 16
		self.map_height = 11

		self.pattern_table_offset = 0x4010
		self.stage_rom_offset = 0x5010
		self.tile_data_size = 0x58
		self.stage_data_size = self.tile_data_size + 7

		self.current_brush = 1

		self.custom_file_name = "Lawn_Mower_custom.nes"

		self.current_lawn = None

		self.pattern_table_width = 128
		self.pattern_table_height = 128

		self.show_images = True
		self.show_grid = True
		self.show_animation = True

		self.decrease_lawn_width = lambda event, offset=-1: self.change_lawn_width(offset)
		self.increase_lawn_width = lambda event, offset=1: self.change_lawn_width(offset)

		self.root.bind("<Control-s>", self.save_as)
		self.root.bind("<Button-1>", self.handle_click)
		self.root.bind("<Button-3>", self.handle_rclick)
		self.root.bind("<ButtonRelease-1>", self.handle_mouse_release)
		self.root.bind('<Motion>', self.mouse_motion)
		self.root.bind("1", lambda event, brush=0: self.set_tile_brush(brush))
		self.root.bind("2", lambda event, brush=1: self.set_tile_brush(brush))
		self.root.bind("3", lambda event, brush=2: self.set_tile_brush(brush))
		self.root.bind("4", lambda event, brush=3: self.set_tile_brush(brush))

		self.root.bind("i", self.toggle_show_images)
		self.root.bind("g", self.toggle_show_grid)
		self.root.bind("a", self.toggle_show_animation)

		self.root.bind("<Prior>", self.load_prev_lawn)
		self.root.bind("<Next>", self.load_next_lawn)
		self.root.bind("<Up>", self.load_prev_lawn)
		self.root.bind("<Down>", self.load_next_lawn)

		self.root.bind("-", self.decrease_lawn_width)
		self.root.bind("+", self.increase_lawn_width)
		self.root.bind("<Left>", self.decrease_lawn_width)
		self.root.bind("<Right>", self.increase_lawn_width)

		self.root.resizable(0, 0)

		self.root.geometry("+640+480")

	def load_next_lawn(self, event):
		self.load_lawn(self.current_lawn+1)

	def load_prev_lawn(self, event):
		self.load_lawn(self.current_lawn-1)

	def toggle_show_images(self, event):
		self.show_images = not self.show_images
		self.render_all_tiles()

	def toggle_show_grid(self, event):
		self.show_grid = not self.show_grid
		self.render_all_tiles()

	def toggle_show_animation(self, event):
		self.show_animation = not self.show_animation

	def save_as(self, event):
		# save the current rom in memory to the specified file.

		target_rom_dir = os.path.dirname(self.orig_rom_filename)

		file_name = filedialog.asksaveasfilename(initialdir=target_rom_dir, initialfile=self.custom_file_name,
			title = "Select file", filetypes = (("nes","*.nes"),("all files","*.*")))

		if file_name is not None and len(file_name) > 0:

			self.custom_file_name = os.path.basename(file_name)

			with open(file_name, "wb") as file:
				file.write(self.rom)

	def set_tile_brush(self, argBrush):
		self.current_brush = argBrush

	def handle_click(self, event):
		clicked_x = int(event.x / self.tile_size)
		clicked_y = int(event.y / self.tile_size)

		self.pressing_m1 = True

		self.set_tile(clicked_x, clicked_y, self.current_brush)

	def handle_rclick(self, event):

		clicked_x = int(event.x / self.tile_size)
		clicked_y = int(event.y / self.tile_size)
		self.set_spawn_point(clicked_x, clicked_y)

	def set_spawn_point(self, argX, argY):

		if argX < self.map_width and argY < self.map_height:

			self.spawn_x = argX + self.spawn_x_offset
			self.spawn_y = argY + self.spawn_y_offset

			self.render_all_tiles()

			self.update_current_lawn_rom()

	def handle_mouse_release(self, event):
		self.pressing_m1 = False

	def mouse_motion(self, event):
		if self.pressing_m1:
			motion_x = int(event.x / self.tile_size)
			motion_y = int(event.y / self.tile_size)
			self.set_tile(motion_x, motion_y, self.current_brush)

	def load_rom(self, argFilename):

		self.orig_rom_filename = argFilename

		# loads the specified rom into memory for editing
		with open(argFilename, "rb") as rom:
			self.rom = bytearray(rom.read())

		expected_size = 24592
		if len(self.rom) != expected_size:
			print("Read {} bytes expecting {}".format(len(self.rom), expected_size))

		self.load_lawn(0)

	def update_current_lawn_rom(self):
		# sync the rom in memory with tile_data

		# self.print_current_lawn()
		# sys.stdout.flush()

		current_stage_base = self.stage_rom_offset + self.stage_data_size * self.current_lawn
		tile_offset = current_stage_base

		self.grass_count = 0

		for i in range(self.tile_data_size):

			data_byte = 0

			for tile in range(4):
				data_byte <<= 2
				data_byte |= self.tile_data[i*4 + tile]

				# if this tile is on the left border (not count) 
				# or beyond the width of the map do not count grass on it
				x_offset = (i*4+tile) % 32
				if x_offset == 0 or x_offset > self.map_width:
					continue

				if self.tile_data[i*4 + tile] == 1:
					self.grass_count += 1

				# self.tile_data.append(data_byte >> (6 - (tile * 2)) & 3)

			self.rom[tile_offset] = data_byte
			tile_offset += 1

		# metadata after tile data, one byte each
		# width, start x, start y, tile mowed goal, zero, tile percent value low, tile percent value high
		metadata_offset = current_stage_base + self.tile_data_size
		self.rom[metadata_offset] = self.map_width

		self.rom[metadata_offset+1] = self.spawn_x
		self.rom[metadata_offset+2] = self.spawn_y

		# update the title with the overflow grass count before limiting it to 1 byte (255)
		self.update_title()

		# grass count cannot exceed one byte (255).
		# if more than 255 grass is on the level it will be complete before completely mowed
		if self.grass_count > 255:
			self.grass_count = 255

		self.rom[metadata_offset + 3] = self.grass_count

		# print("tall grass {}".format(self.grass_count))

		# calculate the hi/lo percent value for each mowed tile for the stage metadata
		if self.grass_count > 0:
			lo_value = int(100/self.grass_count*255)
		else:
			lo_value = 0
		hi_value = 0
		while lo_value > 256:
			hi_value += 1
			lo_value -= 256

		self.rom[metadata_offset + 5] = lo_value
		self.rom[metadata_offset + 6] = hi_value
		# print("value lo {}".format(self.rom[metadata_offset + 5]))
		# print("value hi {}".format(self.rom[metadata_offset + 6]))
		# sys.stdout.flush()

		# TODO: (REMOVE THIS) reload current lawn for debugging (visually check that it was updated correctly)
		# self.set_lawn(self.current_lawn)

	def update_title(self):
		self.master.title("Lawnscaper by serakeri - Lawn {} - Grass {} / 255".format(self.current_lawn+1, self.grass_count))

	def change_lawn_width(self, argOffset):
		# changes the current lawn with by the target offset (should be +1 or -1 increments ideally)
		self.map_width += argOffset

		if self.map_width < 14:
			self.map_width = 14

		if self.map_width > 30:
			self.map_width = 30

		self.resize_and_render_frame()

	def load_lawn(self, argLawn):
		# load lawn number (argLawn) into the editor based on the rom

		if argLawn < 0 or argLawn > 9:
			return

		self.current_lawn = argLawn

		# for stage_number in range(10):

		current_stage_base = self.stage_rom_offset + self.stage_data_size * self.current_lawn

		metadata_offset = current_stage_base + self.tile_data_size
		self.map_width = self.rom[metadata_offset]
		self.spawn_x = self.rom[metadata_offset+1]
		self.spawn_y = self.rom[metadata_offset+2]

		# The remaining metadata (3 bytes) stores how many tiles need mowed
		# and how much percent completion each time is worth. These
		# should be calculated upon saving and not set manually

		print("map_width: {}".format(self.map_width))
		print("spawn_x: {}".format(self.spawn_x))
		print("spawn_y: {}".format(self.spawn_y))

		self.tile_data = []
		tile_offset = current_stage_base
		for i in range(self.tile_data_size):
			data_byte = self.rom[tile_offset]

			for tile in range(4):
				self.tile_data.append(data_byte >> (6 - (tile * 2)) & 3)

			tile_offset += 1

		self.print_current_lawn()

		self.resize_and_render_frame()

	def process_animation(self):
		if self.show_animation:
			self.render_all_tiles()
		self.after(100, self.process_animation)

	def resize_and_render_frame(self):

		if not self.initialized:
			self.initialized = True
			self.initialize_tile_images()
			self.init_frame()
			self.root.after(100, self.process_animation)

		self.root.geometry("{}x{}".format(self.tile_size * self.map_width, self.tile_size * self.map_height))
		self.render_all_tiles()

		# counts the grass and updates the internal structure
		self.update_current_lawn_rom()

	def print_current_lawn(self):
		# print current lawn's internal data for debugging
		for i in range(len(self.tile_data)):
			sys.stdout.write(str(self.tile_data[i]))
			if (i+1) % (32) == 0:
				print()
		print("lawn {}".format(self.current_lawn+1))
		# print(len(self.tile_data))
		sys.stdout.flush()

	def get_tile(self, argX, argY):
		tile_offset = self.get_tile_data_offset(argX, argY)
		# print(tile_offset)
		# sys.stdout.flush()
		return self.tile_data[tile_offset]

	def set_tile(self, argX, argY, argBrush):
		tile_offset = self.get_tile_data_offset(argX, argY)

		# verify tile offset since the user can click outside of the playable area in the window
		if tile_offset < len(self.tile_data):
			self.tile_data[tile_offset] = argBrush
			# update the lawn in memory
			self.update_current_lawn_rom()
			self.render_all_tiles()

	def get_tile_data_offset(self, argX, argY):
		# add one to X to hide the left border
		return (argX + 1) + 32 * argY

	def init_frame(self):
		self.pack(fill=BOTH, expand=1)

		self.canvas = Canvas(self)

		self.root.geometry("{}x{}".format(self.tile_size * self.map_width, self.tile_size * self.map_height))

		self.canvas.pack(fill=BOTH, expand=1)

		self.render_all_tiles()

	def image_for_tile(self, x, y):
		tile_id = self.get_tile(x, y)
		tile_img = [self.img_cut_grass, self.img_tall_grass, self.img_flower_1, self.img_rock]
		if tile_id == 0:
			return self.img_cut_grass if (x + y) % 2 else self.img_cut_grass_2
		elif tile_id == 1:
			return self.img_tall_grass if (x + y) % 2 else self.img_tall_grass_2
		elif tile_id == 2:
			if self.show_animation:
				current_time = time.time() % 1
				anim_frames = [0, 1, 0]
				anim_timing = [0.33, 0.66, 1]
				this_frame = 0
				while current_time > anim_timing[this_frame]:
					this_frame += 1
				return [self.img_flower_1, self.img_flower_2][anim_frames[this_frame]]
			else:
				return self.img_flower_2
		else:
			return tile_img[tile_id]

	def render_all_tiles(self):

		# clear existing canvas objects before creating new rectangles on canvas
		self.canvas.delete('all')

		# note: the tile data includes room for the border but it will not be rendered in the UI.
		# 		since the left border is ignored need to render one further than the width
		for x in range(self.map_width+1):
			for y in range(self.map_height):

				xpos = x * self.tile_size
				ypos = y * self.tile_size

				tile_id = self.get_tile(x, y)

				if self.show_images:
					self.canvas.create_image((xpos, ypos), image=self.image_for_tile(x, y), state="normal", anchor="nw")
				else:
					colors = ["#00a500", "#00ff00", "#fc7460", "#bcbcbc"]
					fill_color = colors[tile_id]

					grid_width = 1 if self.show_grid else 0
					self.canvas.create_rectangle(xpos, ypos,
						xpos + self.tile_size, ypos + self.tile_size,
						outline="#ffffff", fill=fill_color, width=grid_width)

				# compare the spawn with the tile render offset (1,3) that ignores the borders
				if self.spawn_x == x+self.spawn_x_offset and self.spawn_y == y+self.spawn_y_offset:
					spawn_size = 15
					xpos += spawn_size
					ypos += spawn_size
					self.canvas.create_rectangle(xpos, ypos, 
						xpos + self.tile_size - spawn_size * 2,
						ypos + self.tile_size- spawn_size * 2,
						outline="#000000", fill="#ff0000", width=1)

		# for image mode grid the grid is drawn after the borderless images
		if self.show_images and self.show_grid:
			for y in range(self.map_height):
				ypos = y * self.tile_size
				for x in range(self.map_width):
					xpos = x * self.tile_size
					self.canvas.create_line(xpos, 0, xpos, self.map_height * self.tile_size, fill="#ffffff")
				self.canvas.create_line(0, ypos, self.map_width * self.tile_size, ypos, fill="#ffffff")

	def initialize_tile_images(self):
		# create images from the rom's pattern table
		width = self.pattern_table_width
		height = self.pattern_table_height
		image_scale = 2

		pattern_table_data = [bytearray(width*height), bytearray(width*height)]

		# img = [PhotoImage(width=width, height=height), PhotoImage(width=width, height=height)]
		# for x in range(width):
		# 	for y in range(height):
		# 		img.put("#FF0000" if (x + y) % 2 == 0 else "#FFFFFF", (x, y))

		current_offset = self.pattern_table_offset

		for pattern_table_id in range(2):
			for pattern_table_y in range(16):
				for pattern_table_x in range(16):
					# each 8x8 tile's palette is represented by 2 bit planes
					for plane in range(2):
						for y in range(8):
							data_byte = self.rom[current_offset]

							for x in range(8):
								pixel_x = pattern_table_x * 8 + x
								pixel_y = pattern_table_y * 8 + y
								pattern_table_data[pattern_table_id][pixel_x + pixel_y * width] |= (plane+1) * ((data_byte >> (7 - x)) & 1)

							current_offset += 1

		# background letter palette
		palette_0 = ["#000000", "#9D5400", "#FA9E00", "#FFFFFF"]
		# flower tile palette
		palette_1 = ["#000000", "#005C00", "#E9E681", "#FF7757"]
		# grass tile palette
		palette_2 = ["#000000", "#005C00", "#00A300", "#7AE700"]
		# rock tile palette
		palette_3 = ["#000000", "#005C00", "#ABABAB", "#FFFFFF"]

		# for pattern_table_id in range(2):
		# 	for i in range(width * height):
		# 		palette_bits = pattern_table_data[pattern_table_id][i]
		# 		# print(f"{int(current_pixel % width)} : {int(current_pixel / width)}")
		# 		img[pattern_table_id].put(palette_2[palette_bits], (i % width, i // width))
		# 		# print(f'put {(int(i % width), int(i / width))} : {palette_color}')

		# 	img[pattern_table_id] = img[pattern_table_id].zoom(image_scale)
		# 	self.canvas.create_image((8 + pattern_table_id * width * image_scale, 8), image=img[pattern_table_id], state="normal", anchor="nw")

		# create a reference to the image so it is kept in memory
		# self.img_ref = img

		self.img_cut_grass = self.image_from_pattern_table(pattern_table_data[0], 0, 8, palette_2)
		self.img_cut_grass = self.img_cut_grass.zoom(3)
		# self.canvas.create_image((0, 0), image=self.img_cut_grass, state="normal", anchor="nw")

		self.img_cut_grass_2 = self.image_from_pattern_table(pattern_table_data[0], 2, 8, palette_2)
		self.img_cut_grass_2 = self.img_cut_grass_2.zoom(3)
		# self.canvas.create_image((0, 64), image=self.img_cut_grass_2, state="normal", anchor="nw")

		self.img_tall_grass = self.image_from_pattern_table(pattern_table_data[0], 4, 8, palette_2)
		self.img_tall_grass = self.img_tall_grass.zoom(3)
		# self.canvas.create_image((64, 0), image=self.img_tall_grass, state="normal", anchor="nw")

		self.img_tall_grass_2 = self.image_from_pattern_table(pattern_table_data[0], 6, 8, palette_2)
		self.img_tall_grass_2 = self.img_tall_grass_2.zoom(3)
		# self.canvas.create_image((64, 64), image=self.img_tall_grass_2, state="normal", anchor="nw")

		self.img_flower_1 = self.image_from_pattern_table(pattern_table_data[0], 8, 8, palette_1)
		self.img_flower_1 = self.img_flower_1.zoom(3)
		# self.canvas.create_image((128, 0), image=self.img_flower_1, state="normal", anchor="nw")

		self.img_flower_2 = self.image_from_pattern_table(pattern_table_data[1], 8, 8, palette_1)
		self.img_flower_2 = self.img_flower_2.zoom(3)
		# self.canvas.create_image((128, 64), image=self.img_flower_2, state="normal", anchor="nw")

		self.img_rock = self.image_from_pattern_table(pattern_table_data[0], 12, 8, palette_3)
		self.img_rock = self.img_rock.zoom(3)
		# self.canvas.create_image((192, 0), image=self.img_rock, state="normal", anchor="nw")

	def image_from_pattern_table(self, pattern_table_data, tile_x, tile_y, palette):
		# return tkinter PhotoImage for a 2x2 pattern tile at the specificated location for the given pattern table
		game_tile_width = 16
		game_tile_height = 16
		tile_img = PhotoImage(width=game_tile_width, height=game_tile_height)
		for y in range(game_tile_height):
			pattern_table_y = tile_y * 8 + y
			for x in range(game_tile_width):
				pattern_table_x = tile_x * 8 + x
				palette_bits = pattern_table_data[pattern_table_x + pattern_table_y * self.pattern_table_width]
				tile_img.put(palette[palette_bits], (x, y))
		return tile_img

def main():

	# initialize and hide the tk window so a blank one does not appear during rom selection
	root = Tk()
	root.withdraw()

	if len(sys.argv) > 1:
		target_rom = sys.argv[1]
	else:
		target_rom = filedialog.askopenfilename(title = "Select Lawn Mower rom", filetypes = (("nes","*.nes"),("all files","*.*")))

		if target_rom is None or target_rom == "":
			print("No lawn mower rom selected")
			exit(1)

	ex = Lawnscaper(root)

	# show the window after it has been initialized
	root.deiconify()

	ex.load_rom(target_rom)

	root.mainloop()

if __name__ == '__main__':
	main()
