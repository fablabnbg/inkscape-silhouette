#! /usr/bin/python
#
# expose a bug in font metrics handling.
# (c) 2013, jw@suse.de
#
# Requires: zypper in python-goocanvas
# https://bugzilla.novell.com/show_bug.cgi?id=820593
# https://bugzilla.gnome.org/show_bug.cgi?id=700664

from __future__ import print_function

import gtk
from goocanvas import *
import cairo


def scale_up(win, ev):
  s = canvas.get_scale()
  if chr(ev.keyval) == '+':  canvas.set_scale(s*1.2)
  elif chr(ev.keyval) == '-':  canvas.set_scale(s*.8)
  else: gtk.main_quit()
  print(canvas.get_scale())


def button_press(win, ev):
  win.click_x = ev.x
  win.click_y = ev.y
  print(win.click_x, win.click_y)


def button_release(win, ev):
  win.click_x = None
  win.click_y = None


def motion_notify(win, ev):
  try:
    # 3.79 is the right factor for units='mm'
    dx = (ev.x-win.click_x) / canvas.get_scale() / 3.79
    dy = (ev.y-win.click_y) / canvas.get_scale() / 3.79
    win.click_x = ev.x
    win.click_y = ev.y
    (x1,y1,x2,y2) = canvas.get_bounds()
    canvas.set_bounds(x1-dx,y1-dy,x2-dx,y2-dy)
  except:
    pass


win = gtk.Window()
win.connect("destroy", gtk.main_quit)
win.connect("key-press-event", scale_up)
win.connect("motion-notify-event", motion_notify)
win.connect("button-press-event", button_press)
win.connect("button-release-event", button_release)

canvas = Canvas(units='mm', scale=2)
canvas.set_size_request(1000, 400)
root = canvas.get_root_item()

Text(parent=root, x=0, y=0,  text="TooT, Hifi VA World", font="6")
Text(parent=root, x=0, y=8,  text="TooT, Hifi VA World", font="sans 9")
Text(parent=root, x=0, y=20, text="TooT, Hifi VA World", font="Arial 12")
Text(parent=root, x=0, y=30, text="TooT, Hifi VA World", font="24")

win.add(canvas)
win.show_all()

gtk.main()
