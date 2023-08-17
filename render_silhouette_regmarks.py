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
from inkex import Boolean, Rectangle, Line
from inkex import Layer, Group
from gettext import gettext

LAYERNAME = 'Regmarks'
REG_SQUARE_MM = 5
REG_LINE_MM = 20
REG_KEEPOUT_MM = 2

# https://www.reddit.com/r/silhouettecutters/comments/wcdnzy/the_key_to_print_and_cut_success_an_extensive/
# > The registration mark thickness is actually very important. For some reason, 0.3 mm marks work perfectly. 
# > The thicker you get, the less accurate registration will be. ~~~ galaxyman47
REG_MARK_LINE_WIDTH_MM = 0.3

class InsertRegmark(inkex.Effect):
	def __init__(self):
		inkex.Effect.__init__(self)

	def add_arguments(self, pars):
		# Parse arguments
		pars.add_argument("-X", "--reg-x", "--regwidth",  type = float, dest = "regwidth",   default = 180.0, help="X mark distance [mm]")
		pars.add_argument("-Y", "--reg-y", "--reglength", type = float, dest = "reglength",  default = 230.0, help="Y mark distance [mm]")
		pars.add_argument("--rego-x",  "--regoriginx",    type = float, dest = "regoriginx", default = 15.0,  help="X mark origin from left [mm]")
		pars.add_argument("--rego-y", "--regoriginy",     type = float, dest = "regoriginy", default = 20.0,  help="X mark origin from top [mm]")
		pars.add_argument("--verbose", dest = "verbose",  type = Boolean, default = False, help="enable log messages")

	#SVG rect element generation routine
	def drawRect(self, size, pos, name):
		mm_to_user_unit = self.svg.unittouu('1mm')
		x, y = [pos * mm_to_user_unit for pos in pos  ]
		w, h = [pos * mm_to_user_unit for pos in size ]
		return Rectangle.new(x, y, w, h, id=name, style='fill: black;')
		
	#SVG line element generation routine
	def drawLine(self, posStart, posEnd, name):
		mm_to_user_unit = self.svg.unittouu('1mm')
		x1, y1, = [pos * mm_to_user_unit for pos in posStart]
		x2, y2, = [pos * mm_to_user_unit for pos in posEnd  ]
		line_style = 'stroke: black; stroke-width: '+str(REG_MARK_LINE_WIDTH_MM * mm_to_user_unit)+';'
		return Line.new((x1, y1), (x2, y2), id=name, style=line_style)
	
	def effect(self):
		reg_origin_X = self.options.regoriginx
		reg_origin_Y = self.options.regoriginy
		reg_width = self.options.regwidth if self.options.regwidth else int(self.svg.get("width").rstrip("mm")) - reg_origin_X*2
		reg_length = self.options.reglength if self.options.reglength else int(self.svg.get("height").rstrip("mm")) - reg_origin_Y*2

		if self.options.verbose == True:
			inkex.base.InkscapeExtension.msg(gettext("[INFO]: page width ")+str(self.svg.get("width").rstrip("mm")))
			inkex.base.InkscapeExtension.msg(gettext("[INFO]: page height ")+str(self.svg.get("height").rstrip("mm")))
			inkex.base.InkscapeExtension.msg(gettext("[INFO]: regmark from document left ")+str(reg_origin_X))
			inkex.base.InkscapeExtension.msg(gettext("[INFO]: regmark from document top ")+str(reg_origin_Y))
			inkex.base.InkscapeExtension.msg(gettext("[INFO]: regmark to regmark spacing X ")+str(reg_width))
			inkex.base.InkscapeExtension.msg(gettext("[INFO]: regmark to regmark spacing Y ")+str(reg_length))

		# Create a new layer
		layer = self.svg.add(Layer.new(LAYERNAME))
	
		# Create square in top left corner
		layer.append(self.drawRect((REG_SQUARE_MM,REG_SQUARE_MM), (reg_origin_X,reg_origin_Y), 'TopLeft'))
		
		# Create group for top right corner
		topRight = Group(id = 'TopRight')
		# Create horizontal and vertical lines in group
		top_right_reg_origin_x = reg_origin_X+reg_width
		topRight.append(self.drawLine((top_right_reg_origin_x-REG_LINE_MM,reg_origin_Y), (top_right_reg_origin_x,reg_origin_Y), 'Horizontal'))
		topRight.append(self.drawLine((top_right_reg_origin_x,reg_origin_Y), (top_right_reg_origin_x,reg_origin_Y + REG_LINE_MM), 'Vertical'))
		layer.append(topRight)
		
		# Create group for top right corner
		bottomLeft = Group(id = 'BottomLeft')
		# Create horizontal and vertical lines in group
		top_right_reg_origin_y = reg_origin_Y+reg_length
		bottomLeft.append(self.drawLine((reg_origin_X,top_right_reg_origin_y), (reg_origin_X+REG_LINE_MM,top_right_reg_origin_y), 'Horizontal'))
		bottomLeft.append(self.drawLine((reg_origin_X,top_right_reg_origin_y), (reg_origin_X,top_right_reg_origin_y - REG_LINE_MM), 'Vertical'))
		layer.append(bottomLeft)
		
		# Keepout Marker #
		# Not directly part of Silhouette registration marker
		# Instead it's a visual indicator to the user to avoid putting any design within this area

		# Create group for top left corner keepout
		topLeftKeepout = Group(id = 'TopLeftKeepout')
		# Create horizontal and vertical lines in group
		top_left_keepout_origin_x = reg_origin_X+REG_LINE_MM
		top_left_keepout_origin_y = reg_origin_Y+REG_LINE_MM
		topLeftKeepout.append(self.drawLine((top_left_keepout_origin_x,top_left_keepout_origin_y), (top_left_keepout_origin_x-REG_KEEPOUT_MM,top_left_keepout_origin_y),'Horizontal'))
		topLeftKeepout.append(self.drawLine((top_left_keepout_origin_x,top_left_keepout_origin_y), (top_left_keepout_origin_x,top_left_keepout_origin_y-REG_KEEPOUT_MM), 'Vertical'))
		layer.append(topLeftKeepout)

		# Create group for top right corner keepout
		topRightKeepout = Group(id = 'TopRightKeepout')
		# Create horizontal and vertical lines in group
		top_left_keepout_origin_x = reg_origin_X+reg_width-REG_LINE_MM
		top_left_keepout_origin_y = reg_origin_Y+REG_LINE_MM
		topRightKeepout.append(self.drawLine((top_left_keepout_origin_x,top_left_keepout_origin_y), (top_left_keepout_origin_x+REG_KEEPOUT_MM,top_left_keepout_origin_y),'Horizontal'))
		topRightKeepout.append(self.drawLine((top_left_keepout_origin_x,top_left_keepout_origin_y), (top_left_keepout_origin_x,top_left_keepout_origin_y-REG_KEEPOUT_MM), 'Vertical'))
		layer.append(topRightKeepout)

		# Create group for bottom right corner keepout
		bottomRightKeepout = Group(id = 'BottomRightKeepout')
		# Create horizontal and vertical lines in group
		bottom_right_keepout_origin_x = reg_origin_X+REG_LINE_MM
		bottom_right_keepout_origin_y = reg_origin_Y+reg_length-REG_LINE_MM
		bottomRightKeepout.append(self.drawLine((bottom_right_keepout_origin_x,bottom_right_keepout_origin_y), (bottom_right_keepout_origin_x-REG_KEEPOUT_MM,bottom_right_keepout_origin_y),'Horizontal'))
		bottomRightKeepout.append(self.drawLine((bottom_right_keepout_origin_x,bottom_right_keepout_origin_y), (bottom_right_keepout_origin_x,bottom_right_keepout_origin_y+REG_KEEPOUT_MM), 'Vertical'))
		layer.append(bottomRightKeepout)

		# Lock layer
		layer.set_sensitive(False)
		
if __name__ == '__main__':
	InsertRegmark().run()