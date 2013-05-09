#! /usr/bin/python
#
# simple demo program to drive the silhouette cameo.
# (C) 2013 jw@suse.de
#
# Requires: python-usb  # from Factory

from Graphtec import SilhouetteCameo

# coordinates in mm, origin int top lefthand corner
arrow1 = [ (1,6), (21,6), (18,1), (31,11), (18,21), (21,16), (1,16), (4,11), (1,6) ]
arrow2 = map(lambda x: (x[0]+50, x[1]+5), arrow1)
arrow3 = map(lambda x: (x[0]+100,x[1]+10), arrow1)

dev = SilhouetteCameo()
state = dev.initialize()
print state
print "device version: '%s'" % dev.get_version()

dev.setup(media=132)
dev.page(cut=[arrow1,arrow2,arrow3], margintop=10.0)
