#!/usr/bin/env python3

import os
import sys
from tkinter import filedialog
from tkinter import Tk, Canvas, Frame, BOTH

class Lawnscaper(Frame):

	def __init__(self, argRoot):

		super().__init__()

		self.root = argRoot

		self.master.title("Lawnscaper")

		self.initialized = False

		self.pressing_m1 = False

		self.tile_size = 50

		# the game counts the border as tiles. store these offsets to make the top left coord (0, 0)
		self.spawn_x_offset = 1
		self.spawn_y_offset = 3

		self.map_width = 16
		self.map_height = 11

		self.stage_rom_offset = 0x5010
		self.tile_data_size = 0x58
		self.stage_data_size = self.tile_data_size + 7

		self.current_brush = 1

		self.custom_file_name = "Lawn_Mower_custom.nes"

		self.current_lawn = None

		self.root.bind("<Control-s>", self.save_as)
		self.root.bind("<Button-1>", self.handle_click)
		self.root.bind("<Button-3>", self.handle_rclick)
		self.root.bind("<ButtonRelease-1>", self.handle_release)
		self.root.bind('<Motion>', self.mouse_motion)
		self.root.bind("1", lambda event, brush=0: self.set_tile_brush(brush))
		self.root.bind("2", lambda event, brush=1: self.set_tile_brush(brush))
		self.root.bind("3", lambda event, brush=2: self.set_tile_brush(brush))
		self.root.bind("4", lambda event, brush=3: self.set_tile_brush(brush))
		self.root.bind("<Prior>", self.load_prev_lawn)
		self.root.bind("<Next>", self.load_next_lawn)
		self.root.bind("-", lambda event, offset=-1: self.change_lawn_width(offset))
		self.root.bind("+", lambda event, offset=1: self.change_lawn_width(offset))

		self.root.resizable(0, 0)

		self.root.geometry("+640+480")

	def load_next_lawn(self, event):
		self.load_lawn(self.current_lawn+1)

	def load_prev_lawn(self, event):
		self.load_lawn(self.current_lawn-1)

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
		# print("set brush {}".format(argBrush))
		# sys.stdout.flush()
		self.current_brush = argBrush

	def handle_click(self, event):
		clicked_x = int(event.x / self.tile_size)
		clicked_y = int(event.y / self.tile_size)
		# print("clicked at", clicked_x, clicked_y)
		# sys.stdout.flush()

		self.pressing_m1 = True

		self.set_tile(clicked_x, clicked_y, self.current_brush)

	def handle_rclick(self, event):

		clicked_x = int(event.x / self.tile_size)
		clicked_y = int(event.y / self.tile_size)
		self.set_spawn_point(clicked_x, clicked_y)

	def set_spawn_point(self, argX, argY):

		# print("spawn {}, {}".format(argX, argY))
		# sys.stdout.flush()

		if argX < self.map_width and argY < self.map_height:

			self.spawn_x = argX + self.spawn_x_offset
			self.spawn_y = argY + self.spawn_y_offset

			self.render_all_tiles()

			self.update_current_lawn_rom()

	def handle_release(self, event):
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

	def resize_and_render_frame(self):

		if not self.initialized:
			self.initialized = True
			self.init_frame()

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

	def render_all_tiles(self):

		# clear existing canvas objects before creating new rectangles on canvas
		self.canvas.delete('all')

		# note: the tile data includes room for the border but it will not be rendered in the UI.
		# 		since the left border is ignored need to render one further than the width
		for x in range(self.map_width+1):
			for y in range(self.map_height):

				xpos = x * self.tile_size
				ypos = y * self.tile_size

				fill_color = "#1f1"

				tile_id = self.get_tile(x, y)

				colors = ["#00ff00", "#00a500", "#fc7460", "#bcbcbc"]

				fill_color = colors[tile_id]

				self.canvas.create_rectangle(xpos, ypos,
					xpos + self.tile_size, ypos + self.tile_size,
					outline="#ffffff", fill=fill_color, width=1)

				# compare the spawn with the tile render offset (1,3) that ignores the borders
				if self.spawn_x == x+self.spawn_x_offset and self.spawn_y == y+self.spawn_y_offset:
					spawn_size = 15
					xpos += spawn_size
					ypos += spawn_size
					self.canvas.create_rectangle(xpos, ypos, 
						xpos + self.tile_size - spawn_size * 2,
						ypos + self.tile_size- spawn_size * 2,
						outline="#000000", fill="#ff0000", width=1)

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

