#!/usr/bin/env python
# coding=utf-8
#
# Extracted from inkscape extension; original comments below:
#
# Copyright (C) 2005,2007 Aaron Spike, aaron@ekips.org
# Copyright (C) 2009 Alvin Penner, penner@vaxxine.com
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
"""
This extension converts a path into a dashed line using 'stroke-dasharray'
It is a modification of the file addnodes.py
"""
from inkex import bezier, CubicSuperPath


def convert2dash(node):
        dashes = []
        offset = 0
        style = node.style
        if 'stroke-dasharray' in style:
            if style['stroke-dasharray'].find(',') > 0:
                dashes = [float(dash) for dash in style['stroke-dasharray'].split(',')]
        if 'stroke-dashoffset' in style:
            offset = style['stroke-dashoffset']
        if not dashes:
            return
        new = []
        for sub in node.path.to_superpath():
            idash = 0
            dash = dashes[0]
            length = float(offset)
            while dash < length:
                length = length - dash
                idash = (idash + 1) % len(dashes)
                dash = dashes[idash]
            new.append([sub[0][:]])
            i = 1
            while i < len(sub):
                dash = dash - length
                length = bezier.cspseglength(new[-1][-1], sub[i])
                while dash < length:
                    new[-1][-1], nxt, sub[i] = \
                        bezier.cspbezsplitatlength(new[-1][-1], sub[i], dash/length)
                    if idash % 2:           # create a gap
                        new.append([nxt[:]])
                    else:                   # splice the curve
                        new[-1].append(nxt[:])
                    length = length - dash
                    idash = (idash + 1) % len(dashes)
                    dash = dashes[idash]
                if idash % 2:
                    new.append([sub[i]])
                else:
                    new[-1].append(sub[i])
                i += 1
        style.pop('stroke-dasharray')
        node.pop('sodipodi:type')
        node.path = CubicSuperPath(new)
        node.style = style
