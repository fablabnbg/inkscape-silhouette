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

import sys, os
# Enables stand alone mode and helps for tests #
# We append the directory where this script lives and inkscape extension folder to sys.path
sys.path.append(os.path.dirname(os.path.abspath(sys.argv[0])))
sys_platform = sys.platform.lower()
if sys_platform.startswith("win"):
    sys.path.append(r"C:\Program Files\Inkscape\share\inkscape\extensions")
elif sys_platform.startswith("darwin"):
    sys.path.append("/Applications/Inkscape.app/Contents/Resources/share/inkscape/extensions")
else:   # linux
    sys.path.append("/usr/share/inkscape/extensions")

import inkex
from inkex import EffectExtension, Boolean, Rectangle, PathElement, Layer, Group, TextElement, Transform, BaseElement
from gettext import gettext

# Temporary Monkey Patches to support functions that exist only after v1.2
# TODO: If support for Inkscape v1.1 is dropped then this backport can be removed
if not hasattr(inkex, "__version__") or inkex.__version__[0:3] < "1.2":
	# backport svg._base_scale()
	SvgDocumentElement.viewport_width = property(lambda self: convert_unit(self.get("width"), "px") or self.get_viewbox()[2])
	SvgDocumentElement.viewport_height = property(lambda self: convert_unit(self.get("height"), "px") or self.get_viewbox()[3])
	SvgDocumentElement._base_scale = lambda self, unit="px": (convert_unit(1, unit) or 1.0) if not all(self.get_viewbox()[2:]) else max([convert_unit(self.viewport_width, unit) / self.get_viewbox()[2], convert_unit(self.viewport_height, unit) / self.get_viewbox()[3]]) or convert_unit(1, unit) or 1.0
	SvgDocumentElement.to_dimensional = staticmethod(lambda self, value, to_unit="px": convert_unit(value, to_unit))

REGMARK_LAYERNAME = 'Regmarks'
REGMARK_LAYER_ID = 'regmark'
REGMARK_TOP_LEFT_ID = 'regmark-tl'
REGMARK_TOP_RIGHT_ID = 'regmark-tr'
REGMARK_BOTTOM_LEFT_ID = 'regmark-bl'
REGMARK_SAFE_AREA_ID = 'regmark-safe-area'
REGMARK_NOTES_ID = 'regmark-notes'

REG_SQUARE_MM = 5
REG_LINE_MM = 20
REG_SAFE_AREA_MM = 20

# https://www.reddit.com/r/silhouettecutters/comments/wcdnzy/the_key_to_print_and_cut_success_an_extensive/
# > The registration mark thickness is actually very important. For some reason, 0.3 mm marks work perfectly. 
# > The thicker you get, the less accurate registration will be. ~~~ galaxyman47
REG_MARK_LINE_WIDTH_MM = 0.3

REG_MARK_INFO_FONT_SIZE_PX = 2.5

ENABLE_CHECKERBOARD = True

class InsertRegmark(EffectExtension):
	def add_arguments(self, pars):
		# Parse arguments
		pars.add_argument("-X", "--reg-x", "--regwidth",  type = float, dest = "regwidth",   default = 0.0, help="X mark to mark distance [mm]")
		pars.add_argument("-Y", "--reg-y", "--reglength", type = float, dest = "reglength",  default = 0.0, help="Y mark to mark distance [mm]")
		pars.add_argument("--rego-x",  "--regoriginx",    type = float, dest = "regoriginx", default = 10.0,  help="X mark origin from left [mm]")
		pars.add_argument("--rego-y", "--regoriginy",     type = float, dest = "regoriginy", default = 10.0,  help="X mark origin from top [mm]")
		pars.add_argument("--verbose", dest = "verbose",  type = Boolean, default = False, help="enable log messages")

	def effect(self):
		reg_origin_X = self.options.regoriginx
		reg_origin_Y = self.options.regoriginy
		reg_width = self.options.regwidth or self.svg.to_dimensional(self.svg.viewport_width, "mm") - reg_origin_X * 2
		reg_length = self.options.reglength or self.svg.to_dimensional(self.svg.viewport_height, "mm") - reg_origin_Y * 2

		if self.options.verbose == True:
			self.msg(gettext("[INFO]: page width ")+str(self.svg.to_dimensional(self.svg.viewport_width, "mm")))
			self.msg(gettext("[INFO]: page height ")+str(self.svg.to_dimensional(self.svg.viewport_height, "mm")))
			self.msg(gettext("[INFO]: regmark from document left ")+str(reg_origin_X))
			self.msg(gettext("[INFO]: regmark from document top ")+str(reg_origin_Y))
			self.msg(gettext("[INFO]: regmark to regmark spacing X ")+str(reg_width))
			self.msg(gettext("[INFO]: regmark to regmark spacing Y ")+str(reg_length))

		# Check if existing regmark layer exist and delete it
		old_regmark_layer = self.svg.getElementById(REGMARK_LAYER_ID)
		if old_regmark_layer is not None:
			old_regmark_layer.delete()

		# Register Mark #
		mm_to_user_unit = self.svg.viewport_to_unit('1mm')

		# Create a new register mark layer
		regmark_layer = Layer.new(REGMARK_LAYERNAME, id=REGMARK_LAYER_ID)
		regmark_layer.transform = Transform(scale=mm_to_user_unit)

		# Create square in top left corner
		regmark_layer.append(Rectangle.new(left=reg_origin_X, top=reg_origin_Y, width=REG_SQUARE_MM, height=REG_SQUARE_MM, id=REGMARK_TOP_LEFT_ID, style='fill:black;'))

		# Create horizontal and vertical lines in group for top right corner
		top_right_x = reg_origin_X+reg_width
		top_right_path = [(top_right_x-REG_LINE_MM,reg_origin_Y), (top_right_x,reg_origin_Y), (top_right_x,reg_origin_Y + REG_LINE_MM)]
		regmark_layer.append(PathElement.new(path="M"+str(top_right_path), id=REGMARK_TOP_RIGHT_ID, style=f"fill:none; stroke:black; stroke-width:{REG_MARK_LINE_WIDTH_MM};"))

		# Create horizontal and vertical lines in group for bottom left corner
		bottom_left_y = reg_origin_Y+reg_length
		bottom_left_path = [(reg_origin_X+REG_LINE_MM,bottom_left_y), (reg_origin_X,bottom_left_y), (reg_origin_X,bottom_left_y - REG_LINE_MM)]
		regmark_layer.append(PathElement.new(path="M"+str(bottom_left_path), id=REGMARK_BOTTOM_LEFT_ID, style=f"fill:none; stroke:black; stroke-width:{REG_MARK_LINE_WIDTH_MM};"))

		# Safe Area Marker #
		# This draws the safe drawing area
		safearea_left_x = reg_origin_X+REG_LINE_MM
		safearea_top_y = reg_origin_Y+REG_LINE_MM
		safearea_right_x = reg_origin_X+reg_width-REG_LINE_MM
		safearea_bottom_y = reg_origin_Y+reg_length-REG_LINE_MM
		safe_area_points = [
			(safearea_left_x-REG_SAFE_AREA_MM,safearea_top_y),
			(safearea_left_x,safearea_top_y),
			(safearea_left_x,safearea_top_y-REG_SAFE_AREA_MM),
			(safearea_right_x,safearea_top_y-REG_SAFE_AREA_MM),
			(safearea_right_x,safearea_top_y),
			(safearea_right_x+REG_SAFE_AREA_MM,safearea_top_y),
			(safearea_right_x+REG_SAFE_AREA_MM,safearea_bottom_y+REG_SAFE_AREA_MM),
			(safearea_left_x,safearea_bottom_y+REG_SAFE_AREA_MM),
			(safearea_left_x,safearea_bottom_y),
			(safearea_left_x-REG_SAFE_AREA_MM,safearea_bottom_y),
		]
		regmark_layer.append(PathElement.new(path="M"+str(safe_area_points)+"Z", id=REGMARK_SAFE_AREA_ID, style='fill:white;stroke:none;'))

		# Add some settings reminders to the print layer as a reminder
		safe_area_note = f"mark distance from document: Left={reg_origin_X}mm, Top={reg_origin_Y}mm; mark to mark distance: X={reg_width}mm, Y={reg_length}mm; "
		regmark_layer.append(TextElement(safe_area_note, x=f"{(safearea_left_x+3)}", y=f"{(safearea_bottom_y+(REG_SAFE_AREA_MM+reg_origin_Y/2))}", id = REGMARK_NOTES_ID, style=f"font-size:{REG_MARK_INFO_FONT_SIZE_PX}px;"))

		# Lock Layer
		regmark_layer.set_sensitive(False)

		# Insert regmark layer to the bottom of the svg layer stack to avoid covering any existing artwork
		self.svg.insert(0, regmark_layer)

		# Set Page Setting to enable checkerboard (This is required so that safe area is easier to see)
		self.svg.namedview.set('inkscape:pagecheckerboard', str(ENABLE_CHECKERBOARD).lower())

if __name__ == '__main__':
	InsertRegmark().run()