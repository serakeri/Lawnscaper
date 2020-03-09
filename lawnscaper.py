#!/usr/bin/env python3

import os
import sys
from tkinter import filedialog
from tkinter import Tk, Canvas, Frame, BOTH

if len(sys.argv) < 2:
	print("Please pass the lawn mower rom as an argument.")
	print("note: Map changes will not overwrite the specified rom.")
	exit(1)

root = Tk()

class Lawnscaper(Frame):

	def __init__(self, argRomFile):
		super().__init__()

		self.master.title("Lawnscaper")

		self.initialized = False

		self.pressing_m1 = False

		self.tile_size = 50

		self.map_width = 16
		self.map_height = 11

		self.stage_rom_offset = 0x5010
		self.tile_data_size = 0x58
		self.stage_data_size = self.tile_data_size + 7

		self.current_brush = 1

		self.orig_rom_filename = argRomFile

		self.custom_file_name = "Lawn_Mower_custom.nes"

		self.current_lawn = None

		self.load_rom(argRomFile)
		self.load_lawn(0)

	def load_next_lawn(self, event):
		self.load_lawn(self.current_lawn+1)

	def load_prev_lawn(self, event):
		self.load_lawn(self.current_lawn-1)

	def save_as(self, event):
		# save the current rom in memory to the specified file.

		target_rom_dir = os.path.dirname(self.orig_rom_filename)

		file_name = filedialog.asksaveasfilename(initialdir=target_rom_dir, initialfile=self.custom_file_name,
			title = "Select file", filetypes = (("nes","*.nes"),("all files","*.*")))

		if file_name is not None:

			self.custom_file_name = os.path.basename(file_name)

			with open(file_name, "wb") as file:
				file.write(self.rom)

	def set_tile_brush(self, argBrush):
		print("set brush {}".format(argBrush))
		sys.stdout.flush()
		self.current_brush = argBrush

	def handle_click(self, event):
		clicked_x = int(event.x / self.tile_size)
		clicked_y = int(event.y / self.tile_size)
		# print("clicked at", clicked_x, clicked_y)
		sys.stdout.flush()

		self.pressing_m1 = True

		self.set_tile(clicked_x, clicked_y, self.current_brush)

	def handle_release(self, event):
		self.pressing_m1 = False

	def mouse_motion(self, event):
		if self.pressing_m1:
			motion_x = int(event.x / self.tile_size)
			motion_y = int(event.y / self.tile_size)
			self.set_tile(motion_x, motion_y, self.current_brush)

	def load_rom(self, argFilename):
		# loads the specified rom into memory for editing
		with open(argFilename, "rb") as rom:
			self.rom = bytearray(rom.read())

		expected_size = 24592
		if len(self.rom) != expected_size:
			print("Read {} bytes expecting {}".format(len(self.rom), expected_size))

	def update_current_lawn_rom(self):
		# sync the rom in memory with tile_data

		# self.print_current_lawn()
		# sys.stdout.flush()

		current_stage_base = self.stage_rom_offset + self.stage_data_size * self.current_lawn
		tile_offset = current_stage_base

		tall_grass = 0

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
					tall_grass += 1

				# self.tile_data.append(data_byte >> (6 - (tile * 2)) & 3)

			self.rom[tile_offset] = data_byte
			tile_offset += 1

		# metadata after tile data, one byte each
		# width, start x, start y, tile mowed goal, zero, tile percent value low, tile percent value high
		metadata_offset = current_stage_base + self.tile_data_size
		self.rom[metadata_offset + 3] = tall_grass

		# print("tall grass {}".format(tall_grass))

		# calculate the hi/lo percent value for each mowed tile for the stage metadata
		if tall_grass > 0:
			lo_value = int(100/tall_grass*255)
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

	def load_lawn(self, argLawn):
		# load lawn number (argLawn) into the editor based on the rom

		if argLawn < 0 or argLawn > 9:
			return

		self.current_lawn = argLawn

		self.master.title("Lawnscaper - Lawn {}".format(self.current_lawn+1))

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

		if not self.initialized:
			self.initialized = True
			self.init_frame()

		root.geometry("{}x{}".format(self.tile_size * self.map_width, self.tile_size * self.map_height))
		self.render_all_tiles()

	def print_current_lawn(self):
		# print current lawn's internal data for debugging
		for i in range(len(self.tile_data)):
			sys.stdout.write(str(self.tile_data[i]))
			if (i+1) % (32) == 0:
				print()
		print("lawn {}".format(self.current_lawn+1))
		print(len(self.tile_data))
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

			self.render_tile(argX, argY)

	def get_tile_data_offset(self, argX, argY):
		# add one to X to hide the left border
		return (argX + 1) + 32 * argY

	def init_frame(self):
		self.pack(fill=BOTH, expand=1)

		self.canvas = Canvas(self)

		root.geometry("{}x{}".format(self.tile_size * self.map_width, self.tile_size * self.map_height))

		self.canvas.pack(fill=BOTH, expand=1)

		self.render_all_tiles()

	def render_all_tiles(self):

		# note: the tile data includes room for the border but it will not be rendered in the UI.
		# 		since the left border is ignored need to render one further than the width
		for x in range(self.map_width+1):
			for y in range(self.map_height):
				self.render_tile(x, y)

	def render_tile(self, argX, argY):
			xpos = argX * self.tile_size
			ypos = argY * self.tile_size

			fill_color = "#1f1"

			tile_id = self.get_tile(argX, argY)

			colors = ["#00ff00", "#00a500", "#fc7460", "#bcbcbc"]

			fill_color = colors[tile_id]

			self.canvas.create_rectangle(xpos, ypos, 
				xpos + self.tile_size, ypos + self.tile_size, 
				outline="#ffffff", fill=fill_color, width=1)

			# compare the spawn with the tile render offset (1,3) that ignores the borders
			if self.spawn_x == argX+1 and self.spawn_y == argY+3:
				spawn_size = 15
				xpos += spawn_size
				ypos += spawn_size
				self.canvas.create_rectangle(xpos, ypos, 
					xpos + self.tile_size - spawn_size * 2,
					ypos + self.tile_size- spawn_size * 2, 
					outline="#000000", fill="#ff0000", width=1)

def main():

	target_rom = sys.argv[1]

	ex = Lawnscaper(target_rom)

	root.bind("<Control-s>", ex.save_as)
	root.bind("<Button-1>", ex.handle_click)
	root.bind("<ButtonRelease-1>", ex.handle_release)
	root.bind('<Motion>', ex.mouse_motion)
	root.bind("1", lambda event, brush=0: ex.set_tile_brush(brush))
	root.bind("2", lambda event, brush=1: ex.set_tile_brush(brush))
	root.bind("3", lambda event, brush=2: ex.set_tile_brush(brush))
	root.bind("4", lambda event, brush=3: ex.set_tile_brush(brush))
	root.bind("<Prior>", ex.load_prev_lawn)
	root.bind("<Next>", ex.load_next_lawn)


	root.resizable(0, 0)

	root.geometry("+200+200")
	root.mainloop()

if __name__ == '__main__':
	main()

