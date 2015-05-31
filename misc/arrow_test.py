#! /usr/bin/python
#
# simple demo program to drive the silhouette cameo.
# (C) 2013 jw@suse.de
# (C) 2015 juewei@fabfolk.com
#
# Requires: python-usb  # from Factory

import time,sys
sys.path.extend(['..','.'])	# make it callable from top or misc directory.
from silhouette.Graphtec import SilhouetteCameo

# coordinates in mm, origin int top lefthand corner
arrow1 = [ (0,5), (21,5), (18,0), (31,10), (18,20), (21,15), (0,15), (3,10), (0,5) ]
arrow2 = map(lambda x: (x[0]+263, x[1]+0), arrow1)
arrow3 = map(lambda x: (x[0]+2, x[1]+0), arrow1)

dev = SilhouetteCameo()

state = dev.status()    # hint at loading paper, if not ready.
for i in range(1,10):
  if (state == 'ready'): break
  print "status=%s" % (state)
  time.sleep(5.0)
  state = dev.status()
print "status=%s" % (state)
    
print "device version: '%s'" % dev.get_version()

dev.setup(media=113, pressure=0, trackenhancing=True, return_home=False)
bbox = dev.plot(pathlist=[arrow1,arrow1], mediaheight=180, offset=(0,0),bboxonly=True)
print bbox
