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
from inkex import EffectExtension, Boolean, Rectangle, PathElement, Layer, Group, TextElement, Transform
from gettext import gettext
from inkex.units import convert_unit

# Temporary Monkey Backport Patches to support functions that exist only after v1.2
# TODO: If support for Inkscape v1.1 is dropped then this backport can be removed
if not hasattr(inkex, "__version__") or inkex.__version__[0:3] < "1.2":
	from inkex import BaseElement, SvgDocumentElement, paths
	import re
	SvgDocumentElement.viewport_width = property(lambda self: convert_unit(self.get("width"), "px") or self.get_viewbox()[2])
	SvgDocumentElement.viewport_height = property(lambda self: convert_unit(self.get("height"), "px") or self.get_viewbox()[3])
	SvgDocumentElement._base_scale = lambda self, unit="px": (convert_unit(1, unit) or 1.0) if not all(self.get_viewbox()[2:]) else max([convert_unit(self.viewport_width, unit) / self.get_viewbox()[2], convert_unit(self.viewport_height, unit) / self.get_viewbox()[3]]) or convert_unit(1, unit) or 1.0
	BaseElement.to_dimensional = staticmethod(lambda value, to_unit="px": convert_unit(value, to_unit))
	BaseElement.to_dimensionless = staticmethod(lambda value: convert_unit(value, "px"))
	BaseElement.viewport_to_unit = lambda self, value, unit="px": self.to_dimensional(self.to_dimensionless(value) / self.root._base_scale(), unit)
	BaseElement.unit_to_viewport = lambda self, value, unit="px": self.to_dimensional(self.to_dimensionless(value) * self.root._base_scale(), unit)
	BaseElement.set_sensitive = lambda self, sensitive="true": self.set("sodipodi:insensitive", ["true", None][sensitive])
	paths.strargs = lambda string, kind=float: [kind(val) for val in re.compile(r"(?:[+-]?(?:(?:(?:[0-9]+)?\.(?:[0-9]+)|(?:[0-9]+)\.)(?:[eE][+-]?(?:[0-9]+))?|(?:[0-9]+)(?:[eE][+-]?(?:[0-9]+)))|[+-]?(?:[0-9]+))").findall(string)]

REGMARK_LAYERNAME = 'Regmarks'
REGMARK_LAYER_ID = 'regmark'
REGMARK_TOP_LEFT_ID = 'regmark-tl'
REGMARK_TOP_RIGHT_ID = 'regmark-tr'
REGMARK_BOTTOM_LEFT_ID = 'regmark-bl'
REGMARK_BOTTOM_RIGHT_ID = 'regmark-br'
REGMARK_SAFE_AREA_ID = 'regmark-safe-area'
REGMARK_NOTES_ID = 'regmark-notes'

# Registration mark styles
REGSTYLE_STANDARD = 'standard'
REGSTYLE_FOUR_CORNER = 'four_corner'

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
		pars.add_argument("--regstyle", dest = "regstyle", type = str, default = REGSTYLE_STANDARD, help="registration mark style (standard or four_corner)")
		pars.add_argument("--verbose", dest = "verbose",  type = Boolean, default = False, help="enable log messages")

	def l_mark(self, corner_x, corner_y, h_dir, v_dir, mark_id, line_width):
		# Build an L-shaped corner mark: a horizontal and a vertical arm meeting
		# at (corner_x, corner_y). h_dir/v_dir (+1 or -1) point the arms inward.
		path = [
			(corner_x + h_dir * REG_LINE_MM, corner_y),
			(corner_x, corner_y),
			(corner_x, corner_y + v_dir * REG_LINE_MM),
		]
		return PathElement.new(path="M"+str(path), id=mark_id, style=f"fill:none; stroke:black; stroke-width:{line_width};")

	def get_document_pages(self):
		"""Return Inkscape page rectangles in document viewport coordinates."""
		namedview = getattr(self.svg, "namedview", None)
		if namedview is not None and hasattr(namedview, "get_pages"):
			page_elements = namedview.get_pages()
		elif namedview is not None:
			page_elements = [
				node for node in namedview
				if isinstance(node.tag, str) and node.tag.endswith("}page")
			]
		else:
			page_elements = []

		pages = [
			{
				"x": float(getattr(page, "x", page.get("x", 0))),
				"y": float(getattr(page, "y", page.get("y", 0))),
				"width": float(getattr(page, "width", page.get("width", 0))),
				"height": float(getattr(page, "height", page.get("height", 0))),
			}
			for page in page_elements
		]
		if pages:
			return pages

		viewbox = self.svg.get_viewbox()
		return [{
			"x": viewbox[0],
			"y": viewbox[1],
			"width": viewbox[2],
			"height": viewbox[3],
		}]

	def remove_existing_regmark_layers(self):
		"""Remove renderer-owned layers from prior single- or multi-page runs."""
		page_prefix = REGMARK_LAYER_ID + "-page-"
		for element in list(self.svg.iter()):
			element_id = element.get("id", "")
			if (element_id == REGMARK_LAYER_ID or
					(element_id.startswith(page_prefix) and
					 element_id[len(page_prefix):].isdigit())):
				element.delete()

	def regmark_ids(self, page_index, page_count):
		"""Keep single-page IDs stable and make multi-page IDs unique."""
		if page_count == 1:
			return {
				"layer": REGMARK_LAYER_ID,
				"top_left": REGMARK_TOP_LEFT_ID,
				"top_right": REGMARK_TOP_RIGHT_ID,
				"bottom_left": REGMARK_BOTTOM_LEFT_ID,
				"bottom_right": REGMARK_BOTTOM_RIGHT_ID,
				"safe_area": REGMARK_SAFE_AREA_ID,
				"notes": REGMARK_NOTES_ID,
			}
		suffix = "-page-" + str(page_index + 1)
		return {
			"layer": REGMARK_LAYER_ID + suffix,
			"top_left": REGMARK_TOP_LEFT_ID + suffix,
			"top_right": REGMARK_TOP_RIGHT_ID + suffix,
			"bottom_left": REGMARK_BOTTOM_LEFT_ID + suffix,
			"bottom_right": REGMARK_BOTTOM_RIGHT_ID + suffix,
			"safe_area": REGMARK_SAFE_AREA_ID + suffix,
			"notes": REGMARK_NOTES_ID + suffix,
		}

	def render_page_regmarks(self, page, page_index, page_count):
		"""Render one page's registration marks in its local coordinates."""
		reg_origin_X = self.options.regoriginx
		reg_origin_Y = self.options.regoriginy
		page_width = self.svg.unit_to_viewport(page["width"], "mm")
		page_height = self.svg.unit_to_viewport(page["height"], "mm")
		reg_width = self.options.regwidth or page_width - reg_origin_X * 2
		reg_length = self.options.reglength or page_height - reg_origin_Y * 2
		reg_style = self.options.regstyle
		ids = self.regmark_ids(page_index, page_count)

		if self.options.verbose == True:
			self.msg(gettext("[INFO]: page width ")+str(page_width))
			self.msg(gettext("[INFO]: page height ")+str(page_height))
			self.msg(gettext("[INFO]: regmark from document left ")+str(reg_origin_X))
			self.msg(gettext("[INFO]: regmark from document top ")+str(reg_origin_Y))
			self.msg(gettext("[INFO]: regmark to regmark spacing X ")+str(reg_width))
			self.msg(gettext("[INFO]: regmark to regmark spacing Y ")+str(reg_length))

		mm_to_user_unit = self.svg.viewport_to_unit('1mm')
		layer_name = REGMARK_LAYERNAME
		if page_count > 1:
			layer_name += " (page " + str(page_index + 1) + ")"
		regmark_layer = Layer.new(layer_name, id=ids["layer"])
		regmark_layer.transform = (
			Transform(translate=(page["x"], page["y"])) @
			Transform(scale=mm_to_user_unit)
		)

		top_right_x = reg_origin_X + reg_width
		bottom_left_y = reg_origin_Y + reg_length

		if reg_style == REGSTYLE_FOUR_CORNER:
			regmark_layer.append(self.l_mark(reg_origin_X, reg_origin_Y, +1, +1, ids["top_left"], REG_MARK_LINE_WIDTH_MM))
		else:
			regmark_layer.append(Rectangle.new(left=reg_origin_X, top=reg_origin_Y, width=REG_SQUARE_MM, height=REG_SQUARE_MM, id=ids["top_left"], style='fill:black;'))

		regmark_layer.append(self.l_mark(top_right_x, reg_origin_Y, -1, +1, ids["top_right"], REG_MARK_LINE_WIDTH_MM))
		regmark_layer.append(self.l_mark(reg_origin_X, bottom_left_y, +1, -1, ids["bottom_left"], REG_MARK_LINE_WIDTH_MM))
		if reg_style == REGSTYLE_FOUR_CORNER:
			regmark_layer.append(self.l_mark(top_right_x, bottom_left_y, -1, -1, ids["bottom_right"], REG_MARK_LINE_WIDTH_MM))

		safearea_left_x = reg_origin_X + REG_LINE_MM
		safearea_top_y = reg_origin_Y + REG_LINE_MM
		safearea_right_x = reg_origin_X + reg_width - REG_LINE_MM
		safearea_bottom_y = reg_origin_Y + reg_length - REG_LINE_MM
		if reg_style == REGSTYLE_FOUR_CORNER:
			bottom_right_corner = [
				(safearea_right_x + REG_SAFE_AREA_MM, safearea_bottom_y),
				(safearea_right_x, safearea_bottom_y),
				(safearea_right_x, safearea_bottom_y + REG_SAFE_AREA_MM),
			]
		else:
			bottom_right_corner = [
				(safearea_right_x + REG_SAFE_AREA_MM, safearea_bottom_y + REG_SAFE_AREA_MM),
			]
		safe_area_points = [
			(safearea_left_x - REG_SAFE_AREA_MM, safearea_top_y),
			(safearea_left_x, safearea_top_y),
			(safearea_left_x, safearea_top_y - REG_SAFE_AREA_MM),
			(safearea_right_x, safearea_top_y - REG_SAFE_AREA_MM),
			(safearea_right_x, safearea_top_y),
			(safearea_right_x + REG_SAFE_AREA_MM, safearea_top_y),
		] + bottom_right_corner + [
			(safearea_left_x, safearea_bottom_y + REG_SAFE_AREA_MM),
			(safearea_left_x, safearea_bottom_y),
			(safearea_left_x - REG_SAFE_AREA_MM, safearea_bottom_y),
		]
		regmark_layer.append(PathElement.new(path="M" + str(safe_area_points) + "Z", id=ids["safe_area"], style='fill:white;stroke:none;'))

		safe_area_note = f"mark distance from document: Left={reg_origin_X}mm, Top={reg_origin_Y}mm; mark to mark distance: X={reg_width}mm, Y={reg_length}mm; "
		regmark_layer.append(TextElement(safe_area_note, x=f"{(safearea_left_x + 3)}", y=f"{(safearea_bottom_y + (REG_SAFE_AREA_MM + reg_origin_Y / 2))}", id=ids["notes"], style=f"font-size:{REG_MARK_INFO_FONT_SIZE_PX}px;"))

		regmark_layer.set_sensitive(False)
		self.svg.insert(0, regmark_layer)

	def effect(self):
		pages = self.get_document_pages()
		self.remove_existing_regmark_layers()
		for page_index, page in enumerate(pages):
			self.render_page_regmarks(page, page_index, len(pages))

		# Set Page Setting to enable checkerboard (This is required so that safe area is easier to see)
		self.svg.namedview.set('inkscape:pagecheckerboard', str(ENABLE_CHECKERBOARD).lower())

if __name__ == '__main__':
	InsertRegmark().run()
