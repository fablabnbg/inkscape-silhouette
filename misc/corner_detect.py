#! /usr/bin/python
#
# detect sharp corners in a path.

import gtk
from goocanvas import *
import cairo

cut = [[(6.447013888888888, 1.7197916666666666), (2.7447450608333335, 1.8781719273333333), (1.7712151617013887, 1.9675756834166662), (1.4375694444444445, 2.0637499999999998), (1.7712129392013884, 2.15725412703125), (2.7447391341666667, 2.240002452083333), (6.447013888888888, 2.38125)]]

## From http://www.bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
def ccw(A,B,C):
  return (C.y-A.y)*(B.x-A.x) > (B.y-A.y)*(C.x-A.x)

def ccw_t(A,B,C):
  """same as ccw, but expecting tuples"""
  return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])

def intersect(A,B,C,D):
  return ccw_t(A,C,D) != ccw_t(B,C,D) and ccw_t(A,B,C) != ccw_t(A,B,D)

def sharp_turn(A,B,C):
  """Given the path from A to B to C as two line segments.
     Return true, if the corner at B is more than +/- 90 degree.

     Algorithm:
     For the segment A-B, we construct the normal B-D. 
     The we test, if points A and C lie on the same side of the line(!) B-D.
     If so, it is a sharp turn.
  """
  dx = B[0]-A[0]
  dy = B[1]-A[1]
  D = (B[0]-dy, B[1]+dx)        # BD is now the normal to AB
  return ccw_t(A,B,D) == ccw_t(C,B,D)



def scale_up(win, ev, c):
  s = c.get_scale()  
  if   chr(ev.keyval) == '+':  c.set_scale(s*1.2)
  elif chr(ev.keyval) == '-':  c.set_scale(s*.8)
  else: gtk.main_quit()
  print c.get_scale()

def button_press(win, ev):
  win.click_x = ev.x
  win.click_y = ev.y

def button_release(win, ev):
  win.click_x = None
  win.click_y = None

def motion_notify(win, ev, c):
  try:
    # 3.79 is the right factor for units='mm'
    dx = (ev.x-win.click_x) / c.get_scale() / 3.79
    dy = (ev.y-win.click_y) / c.get_scale() / 3.79
    win.click_x = ev.x
    win.click_y = ev.y
    (x1,y1,x2,y2) = c.get_bounds()
    c.set_bounds(x1-dx,y1-dy,x2-dx,y2-dy)
  except:
    pass


def main ():
    win = gtk.Window()

    canvas = Canvas(units='mm', scale=10)
    canvas.set_size_request(600, 450)
    # canvas.set_bounds(0, 0, 120., 90.)
    root = canvas.get_root_item()

    win.connect("destroy", gtk.main_quit)
    win.connect("key-press-event", scale_up, canvas)
    win.connect("motion-notify-event", motion_notify, canvas)
    win.connect("button-press-event", button_press)
    win.connect("button-release-event", button_release)
    
    rect = Rect(parent=root, x=1, y=1, width=3,  height=2,
                        fill_color = '#77ff77', stroke_color = 'black', line_width = .01)
    
    # text = Text(parent=root, text="Hello World", font="12")
    # text.rotate(30,0,10)
    # text.scale(.05,.05)

    p = Points(cut[0])
    poly = Polyline(parent=root, points=p, line_width=0.01)
    A = None
    B = None 
    for path in cut:
      for C in path:
        Ellipse(parent=root, center_x=C[0], center_y=C[1], radius_x=.1, radius_y=.1, line_width = 0.01)
        if A is not None and sharp_turn(A,B,C):
          Ellipse(parent=root, center_x=B[0], center_y=B[1], radius_x=.1, radius_y=.1, fill_color = '#FF7777', line_width = 0)

        A = B
        B = C
      
                    
    win.add(canvas)
    win.show_all()
                                
    gtk.main()

if __name__ == "__main__":
    main ()
