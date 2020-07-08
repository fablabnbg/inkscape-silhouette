#! /usr/bin/python
#
# simple demo program to drive the silhouette cameo.
# (C) 2013 jw@suse.de
# (C) 2015 juewei@fabmail.org
#
# Requires: python-usb  # from Factory

from __future__ import print_function

import time, sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')      # make it callable from anywhere
from silhouette.Graphtec import SilhouetteCameo

# coordinates in mm, origin int top lefthand corner
arrow1 = [ (0,5), (21,5), (18,0), (31,10), (18,20), (21,15), (0,15), (3,10), (0,5) ]
arrow2 = [(x[0]+263, x[1]+0) for x in arrow1]
arrow3 = [(x[0]+30, x[1]+0) for x in arrow1]

dev = SilhouetteCameo()
print("status=%s" % dev.wait_for_ready(20))

tmp_fwd=85	# enough to show 20mm of the latest drawing on the far side of the device.

dev.setup(media=113, pressure=0, trackenhancing=True, return_home=False)

for i in range(8):
  bbox = dev.plot(pathlist=[ arrow1,[(0,tmp_fwd),(0,tmp_fwd)] ], mediaheight=180, offset=(60,0), bboxonly=False, end_paper_offset=-tmp_fwd+1, no_trailer=True)
  dev.wait_for_ready()
  print(i, "path done.")
  time.sleep(5)
  dev.send_command(bbox['trailer'])
  # something is still wrong after we finish a job. The next job does not draw anything.
  # we can workaround by sending a dummy job.
  bbox = dev.plot(pathlist=[ [(0,0),(0,0)] ], offset=(0,0))
  dev.wait_for_ready()
print(bbox)
