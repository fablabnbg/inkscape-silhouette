#! /usr/bin/python
#
# simple demo program to cut with the silhouette cameo.
# (C) 2015 juewei@fabmail.org
#
# Requires: python-usb  # from Factory

from __future__ import print_function

import re,time,sys,string,argparse

sys.path.extend(['..','.'])	# make it callable from top or misc directory.
from silhouette.Graphtec import SilhouetteCameo

ArgParser = argparse.ArgumentParser(description='Cut a dumpfile from sendto_silhouette without using inkscape.')
ArgParser.add_argument('-P', '--pen', action='store_true', help="switch to pen mode. Default: knive mode")
ArgParser.add_argument('-b', '--bbox', action='store_true', help="Bounding box only. Default: entire design")
ArgParser.add_argument('-x', '--xoff', type=float, default=0.0, help="Horizontal offset [mm]. Positive values point rightward")
ArgParser.add_argument('-y', '--yoff', type=float, default=0.0, help="Vertical offset [mm]. Positive values point downward")
#ArgParser.add_argument('-S', '--scale',type=float, default=1.0, help="Scale the design.")
ArgParser.add_argument('-p', '--pressure', type=int, default=3, help="Pressure value [1..18]")
ArgParser.add_argument('-s', '--speed', type=int, default=10, help="Speed value [1..10]")
ArgParser.add_argument('-a', '--advance-origin', action='store_true', help="Set the origin below the design. Default: return home.")
ArgParser.add_argument('-W', '--width', type=float, default=210.0, help="Media width [mm].")
ArgParser.add_argument('-H', '--height', type=float, default=297.0, help="Media height [mm].")
ArgParser.add_argument('dumpfile')
args = ArgParser.parse_args()

dev = SilhouetteCameo()
dev.setup(speed=args.speed, pressure=args.pressure, pen=args.pen, return_home=(not args.advance_origin))

# print args

dumpdata=dev.load_dumpfile(args.dumpfile)

dev.wait_for_ready()
meta = dev.plot(pathlist=[], bboxonly=args.bbox, no_trailer=True,
                mediawidth=args.width, mediaheight=args.height, offset=(args.xoff,args.yoff))
print(meta)

dev.wait_for_ready()
cmd_list = dev.plot_cmds(dumpdata, meta['bbox'], args.xoff, args.yoff)
dev.send_command(cmd_list)
dev.send_command(meta['trailer'])
dev.wait_for_ready()
