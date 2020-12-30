#! /usr/bin/python
#
# simple demo program to feed paper in the silhouette cameo.
# (C) 2015 juewei@fabmail.org
#
# Requires: python-usb  # from Factory

from __future__ import print_function

import time,sys,string

sys.path.extend(['..','.'])	# make it callable from top or misc directory.
from silhouette.Graphtec import SilhouetteCameo

dev = SilhouetteCameo()		# no dev.setup() needed here.

feed_mm = 10
if len(sys.argv) > 1:
  feed_mm = string.atof(sys.argv[1])

if not feed_mm:
  print("Usage: %s [PAPER_FORWARD_MM]" % sys.argv[0])

dev.move_origin(feed_mm)
