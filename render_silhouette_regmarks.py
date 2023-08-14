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
from lxml import etree
from gettext import gettext

SVG_URI = u'http://www.w3.org/2000/svg'

class InsertRegmark(inkex.Effect):
	def __init__(self):
		inkex.Effect.__init__(self)
		
		# Layer name static, since self.document.getroot() not available on initialization
		self.layername = 'silhouette-regmark'
		
		# Parse arguments
		self.arg_parser.add_argument("-X", "--reg-x", "--regwidth", 
				type = float, dest = "regwidth", default = 180.0, help="X mark distance [mm]")
		self.arg_parser.add_argument("-Y", "--reg-y", "--reglength", 
				type = float, dest = "reglength", default = 230.0, help="Y mark distance [mm]")
		self.arg_parser.add_argument("--rego-x",  "--regoriginx", 
				type = float, dest = "regoriginx", default = 15.0, help="X mark origin from left [mm]")
		self.arg_parser.add_argument("--rego-y", "--regoriginy", 
				type = float, dest = "regoriginy", default = 20.0, help="X mark origin from top [mm]")
	
	#SVG rect element generation routine
	def drawRect(self, size, pos, name):
		x, y = pos
		w, h = size
		rect = etree.Element('{%s}rect' % SVG_URI)
		rect.set('x', str(x))
		rect.set('y', str(y))
		rect.set('id', name)
		rect.set('width', str(w))
		rect.set('height', str(h))
		rect.set('style', 'fill: black;')
		return rect
		
	#SVG line element generation routine
	def drawLine(self, posStart, posEnd, name):
		x1, y1 = posStart
		x2, y2, = posEnd
		line = etree.Element('{%s}line' % SVG_URI)
		line.set('x1', str(x1))
		line.set('y1', str(y1))
		line.set('x2', str(x2))
		line.set('y2', str(y2))
		line.set('id', name)
		# https://www.reddit.com/r/silhouettecutters/comments/wcdnzy/the_key_to_print_and_cut_success_an_extensive/
		# > The registration mark thickness is actually very important. For some reason, 0.3 mm marks work perfectly. 
		# > The thicker you get, the less accurate registration will be. ~~~ galaxyman47
		line.set('style', 'stroke: black; stroke-width: 0.3;')
		return line
	
	def effect(self):
		REG_SQUARE_MM = 5
		REG_LINE_MM = 20

		svg = self.document.getroot()

		regwidth = self.options.regwidth if self.options.regwidth else int(svg.get("width").rstrip("mm")) - self.options.regoriginx*2
		reglength = self.options.reglength if self.options.reglength else int(svg.get("height").rstrip("mm")) - self.options.regoriginy*2

		#inkex.errormsg(gettext("[INFO]: width ")+str(svg.get("width").rstrip("mm")))
		#inkex.errormsg(gettext("[INFO]: height ")+str(svg.get("height").rstrip("mm")))
		#inkex.errormsg(gettext("[INFO]: gap width ")+str(regwidth))
		#inkex.errormsg(gettext("[INFO]: gap height ")+str(reglength))

		# Create a new layer.
		layer = etree.SubElement(svg, 'g')
		layer.set(inkex.addNS('label', 'inkscape'), self.layername)
		layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
	
		# Create square in top left corner
		layer.append(self.drawRect((REG_SQUARE_MM,REG_SQUARE_MM), (self.options.regoriginx,self.options.regoriginy), 'TopLeft'))
		
		# Create group for top right corner
		topRight = etree.Element('{%s}g' % SVG_URI)
		topRight.set('id', 'TopRight')
		topRight.set('style', 'fill: black;')
		
		# Create horizontal and vertical lines in group
		top_right_reg_origin_x = self.options.regoriginx+regwidth
		topRight.append(self.drawLine((top_right_reg_origin_x-REG_LINE_MM,self.options.regoriginy), (top_right_reg_origin_x,self.options.regoriginy), 'Horizontal'))
		topRight.append(self.drawLine((top_right_reg_origin_x,self.options.regoriginy), (top_right_reg_origin_x,self.options.regoriginy + REG_LINE_MM), 'Vertical'))
		layer.append(topRight)
		
		# Create group for top right corner
		bottomLeft = etree.Element('{%s}g' % SVG_URI)
		bottomLeft.set('id', 'BottomLeft')
		bottomLeft.set('style', 'fill: black;')
		
		# Create horizontal and vertical lines in group
		top_right_reg_origin_y = self.options.regoriginy+reglength
		bottomLeft.append(self.drawLine((self.options.regoriginx,top_right_reg_origin_y), (self.options.regoriginx+REG_LINE_MM,top_right_reg_origin_y), 'Horizontal'))
		bottomLeft.append(self.drawLine((self.options.regoriginx,top_right_reg_origin_y), (self.options.regoriginx,top_right_reg_origin_y - REG_LINE_MM), 'Vertical'))
		layer.append(bottomLeft)
		
		#Lock layer
		layer.set(inkex.addNS('insensitive', 'sodipodi'), 'true') 
		
if __name__ == '__main__':
	InsertRegmark().run()