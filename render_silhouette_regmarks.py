#
# Copyright (C) 2021 miLORD1337
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110, USA.
#
"""
Base module for rendering regmarks for Silhouette CAMEO products in Inkscape.
"""

import inkex
from inkex import EffectExtension, Boolean, Rectangle, Line, PathElement, Layer, Group, TextElement, Polygon, Transform
from gettext import gettext

REGMARK_LAYERNAME = 'Regmarks'
REGMARK_LAYER_ID = 'regmark'
REGMARK_TOP_LEFT_ID = 'regmark-tl'
REGMARK_TOP_RIGHT_ID = 'regmark-tr'
REGMARK_BOTTOM_LEFT_ID = 'regmark-bl'
REGMARK_SAFE_AREA_ID = 'regmark-safe-area'

REG_SQUARE_MM = 5
REG_LINE_MM = 20
REG_SAFE_AREA_MM = 20

# https://www.reddit.com/r/silhouettecutters/comments/wcdnzy/the_key_to_print_and_cut_success_an_extensive/
# > The registration mark thickness is actually very important. For some reason, 0.3 mm marks work perfectly. 
# > The thicker you get, the less accurate registration will be. ~~~ galaxyman47
REG_MARK_LINE_WIDTH_MM = 0.3

REG_MARK_INFO_FONT_SIZE_PT = 2.5

class InsertRegmark(EffectExtension):
	def __init__(self):
		EffectExtension.__init__(self)

	def add_arguments(self, pars):
		# Parse arguments
		pars.add_argument("-X", "--reg-x", "--regwidth",  type = float, dest = "regwidth",   default = 180.0, help="X mark distance [mm]")
		pars.add_argument("-Y", "--reg-y", "--reglength", type = float, dest = "reglength",  default = 230.0, help="Y mark distance [mm]")
		pars.add_argument("--rego-x",  "--regoriginx",    type = float, dest = "regoriginx", default = 15.0,  help="X mark origin from left [mm]")
		pars.add_argument("--rego-y", "--regoriginy",     type = float, dest = "regoriginy", default = 20.0,  help="X mark origin from top [mm]")
		pars.add_argument("--verbose", dest = "verbose",  type = Boolean, default = False, help="enable log messages")

	#SVG SVGd from (x,y) dimentional points
	def points_to_svgd(self, p, capped=False):
		f = p[0]
		p = p[1:]
		svgd = "M{:.5f},{:.5f}".format(f[0], f[1])
		for x in p:
			svgd += " L{:.5f},{:.5f}".format(x[0], x[1])
		if capped:
			svgd += "z"
		return svgd

	def effect(self):
		reg_origin_X = self.options.regoriginx
		reg_origin_Y = self.options.regoriginy
		reg_width = self.options.regwidth if self.options.regwidth else int(self.svg.get("width").rstrip("mm")) - reg_origin_X*2
		reg_length = self.options.reglength if self.options.reglength else int(self.svg.get("height").rstrip("mm")) - reg_origin_Y*2

		if self.options.verbose == True:
			self.msg(gettext("[INFO]: page width ")+str(self.svg.get("width").rstrip("mm")))
			self.msg(gettext("[INFO]: page height ")+str(self.svg.get("height").rstrip("mm")))
			self.msg(gettext("[INFO]: regmark from document left ")+str(reg_origin_X))
			self.msg(gettext("[INFO]: regmark from document top ")+str(reg_origin_Y))
			self.msg(gettext("[INFO]: regmark to regmark spacing X ")+str(reg_width))
			self.msg(gettext("[INFO]: regmark to regmark spacing Y ")+str(reg_length))

		# Register Mark #
		mm_to_user_unit = self.svg.unittouu('1mm')

		# Create a new register mark layer
		regmark_layer = self.svg.add(Layer.new(REGMARK_LAYERNAME, id=REGMARK_LAYER_ID))
		regmark_layer.transform = Transform(f"scale({mm_to_user_unit}, {mm_to_user_unit})")

		# Create square in top left corner
		regmark_layer.append(Rectangle.new(left=reg_origin_X, top=reg_origin_Y, width=REG_SQUARE_MM, height=REG_SQUARE_MM, id=REGMARK_TOP_LEFT_ID, style='fill:black;'))

		# Create horizontal and vertical lines in group for top right corner
		top_right_x = reg_origin_X+reg_width
		top_right_path = [(top_right_x-REG_LINE_MM,reg_origin_Y), (top_right_x,reg_origin_Y), (top_right_x,reg_origin_Y + REG_LINE_MM)]
		regmark_layer.append(PathElement.new(path=self.points_to_svgd(top_right_path), id=REGMARK_TOP_RIGHT_ID, style=f"fill:none; stroke:black; stroke-width:{REG_MARK_LINE_WIDTH_MM}"))

		# Create horizontal and vertical lines in group for bottom left corner
		bottom_left_y = reg_origin_Y+reg_length
		bottom_left_path = [(reg_origin_X+REG_LINE_MM,bottom_left_y), (reg_origin_X,bottom_left_y), (reg_origin_X,bottom_left_y - REG_LINE_MM)]
		regmark_layer.append(PathElement.new(path=self.points_to_svgd(bottom_left_path), id=REGMARK_BOTTOM_LEFT_ID, style=f"fill:none; stroke:black; stroke-width:{REG_MARK_LINE_WIDTH_MM}"))

		# Safe Area Marker #
		# This draws the safe drawing area
		top_left_safearea_origin_x = reg_origin_X+REG_LINE_MM
		top_left_safearea_origin_y = reg_origin_Y+REG_LINE_MM
		top_right_safearea_origin_x = reg_origin_X+reg_width-REG_LINE_MM
		top_right_safearea_origin_y = reg_origin_Y+REG_LINE_MM
		bottom_left_safearea_origin_x = reg_origin_X+REG_LINE_MM
		bottom_left_safearea_origin_y = reg_origin_Y+reg_length-REG_LINE_MM
		safe_area_points = [
			(top_left_safearea_origin_x-REG_SAFE_AREA_MM,top_left_safearea_origin_y),
			(top_left_safearea_origin_x,top_left_safearea_origin_y),
			(top_left_safearea_origin_x,top_left_safearea_origin_y-REG_SAFE_AREA_MM),
			(top_right_safearea_origin_x,top_right_safearea_origin_y-REG_SAFE_AREA_MM),
			(top_right_safearea_origin_x,top_right_safearea_origin_y),
			(top_right_safearea_origin_x+REG_SAFE_AREA_MM,top_right_safearea_origin_y),
			(top_right_safearea_origin_x+REG_SAFE_AREA_MM,bottom_left_safearea_origin_y+REG_SAFE_AREA_MM),
			(bottom_left_safearea_origin_x,bottom_left_safearea_origin_y+REG_SAFE_AREA_MM),
			(bottom_left_safearea_origin_x,bottom_left_safearea_origin_y),
			(bottom_left_safearea_origin_x-REG_SAFE_AREA_MM,bottom_left_safearea_origin_y),
		]
		regmark_layer.append(PathElement.new(path=self.points_to_svgd(safe_area_points), id=REGMARK_SAFE_AREA_ID, style='fill:white;stroke:none'))

		# Add some settings reminders to the print layer as a reminder
		safe_area_note = f"mark distance from document: Left={reg_origin_X}mm, Top={reg_origin_Y}mm; mark to mark distance: X={reg_width}mm, Y={reg_length}mm; "
		regmark_layer.append(TextElement(safe_area_note, x=f"{(bottom_left_safearea_origin_x+3)}", y=f"{(bottom_left_safearea_origin_y+(REG_SAFE_AREA_MM+reg_origin_Y/2))}", id = 'RegMarkNotes', style=f"font-size:{REG_MARK_INFO_FONT_SIZE_PT}px"))

		# Lock Layer
		regmark_layer.set_sensitive(False)
		
if __name__ == '__main__':
	InsertRegmark().run()