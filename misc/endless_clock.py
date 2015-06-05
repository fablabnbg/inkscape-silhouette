#! /usr/bin/python
#
# endless-clock.py - plot a the time on a silhouette-cameo, repeating...
# (c) 2015, juewei@fabfolk.com
#
# Requires: sudo zypper in python-goocanvas
# Requires: sudo easy_install freetype-py
#
# Modelled after https://github.com/rougier/freetype-py/blob/master/examples/glyph-vector.py

import gtk,time
from goocanvas import *
import cairo,random
import freetype
import matplotlib.path as MP
import matplotlib.transforms as MT

#fontfile= './motorhead.ttf'
#fontfile= './WC Wunderbach Wimpern.ttf'
fontfile= './RIKY2vamp.ttf'
#fontfile= './LeckerliOne-Regular.ttf'
fontfile= '/usr/share/fonts/truetype/FreeSans.ttf'

def show_path(canvas, path = [(0,0),(20,0),(10,20),(0,0)], xoff=0, yoff=0 ):
  """ default path is a downward pointing triangle 
      Both, a list of lists, and a list of tuples is accepted.
  """

  tuplepath=[]
  for i in path: tuplepath.append( tuple([i[0]+xoff, i[1]+yoff]) )
  p = Points(tuplepath)		# cannot handle 2-element lists, need 2-element tuples.
  poly = Polyline(parent=canvas, points=p, line_width=0.5, stroke_color="black")

  idx = 1
  for C in path:
    text = Text(parent=canvas, text=idx, font="4", fill_color="blue")
    idx += 1
    # text.translate(C.x+random.uniform(-.1,0), C.y+random.uniform(-.1,0))
    text.translate(C[0]+xoff+random.uniform(-.5,0), C[1]+yoff+random.uniform(-.5,0))
    text.scale(.25,.25)


def polygons_from_glyph(glyph,x=0,y=0,scale=1.0):
  """ converts a freetype Face glyph outline to a set of polygons.
      Interpolation of splines is implicitly defined by scale.
      And also returns the advance metrics. (More reliable than all 
     the other techniques tested in show_char())
  """
  fix_adv_scale=scale*0.001		# this is horrible. But works for all fonts.
  xadv = glyph.linearHoriAdvance*fix_adv_scale
  yadv = glyph.linearVertAdvance*fix_adv_scale

  o = glyph.outline

  affine=MT.Affine2D()
  trans = affine.translate(x,y).scale(sx=scale,sy=-scale)
  start, end = 0, 0
  VERTS, CODES = [], []
  for i in range(len(o.contours)):
        end    = o.contours[i]
        points = o.points[start:end+1]
        points.append(points[0])
        tags   = o.tags[start:end+1]
        tags.append(tags[0])

        segments = [ [points[0],], ]
        for j in range(1, len(points) ):
            segments[-1].append(points[j])
            if tags[j] & (1 << 0) and j < (len(points)-1):
                segments.append( [points[j],] )
        verts = [points[0], ]
        codes = [MP.Path.MOVETO,]
        for segment in segments:
            if len(segment) == 2:
                verts.extend(segment[1:])
                codes.extend([MP.Path.LINETO])
            elif len(segment) == 3:
                verts.extend(segment[1:])
                codes.extend([MP.Path.CURVE3, MP.Path.CURVE3])
            else:
                verts.append(segment[1])
                codes.append(MP.Path.CURVE3)
                for i in range(1,len(segment)-2):
                    A,B = segment[i], segment[i+1]
                    C = ((A[0]+B[0])/2.0, (A[1]+B[1])/2.0)
                    verts.extend([ C, B ])
                    codes.extend([ MP.Path.CURVE3, MP.Path.CURVE3])
                verts.append(segment[-1])
                codes.append(MP.Path.CURVE3)
        VERTS.extend(verts)
        CODES.extend(codes)
        start = end+1
  return MP.Path(VERTS, CODES).to_polygons(transform=trans),xadv,yadv


def show_char(canvas, face, char, x, y, scale, flags=None):
  if not flags: flags=freetype.FT_LOAD_IGNORE_GLOBAL_ADVANCE_WIDTH|freetype.FT_LOAD_RENDER|freetype.FT_LOAD_FORCE_AUTOHINT

  idx = face.get_char_index(char)
  face.load_char(char)		# Do not use load_glyph(), it scales all chars to equal height.
  adv = face.get_advance(idx, flags|freetype.FT_LOAD_NO_SCALE)	# need NO_SCALE,  or its broken.
  
  # bbox = face.glyph.outline.get_bbox()
  polys,xadv,yadv = polygons_from_glyph(face.glyph, x=x,y=y,scale=scale)
  for poly in polys: show_path(canvas,poly)

  if False:
    fix_adv_scale=scale*1.2		# not really good.
    #adv = (bbox.xMax-bbox.xMin)		# not really good.
    x += adv * fix_adv_scale
    print("advance "+char+" ",adv*fix_adv_scale)

  if False:
    fix_adv_scale=scale*0.03		# 0.06 for FreeSans. 0.03 for motorhead. this is horrible.
    x += adv * fix_adv_scale
    print("advance "+char+" ",adv*fix_adv_scale)

  if True:
    print("advance "+char+" ", xadv)
    x += xadv
    y += yadv
  return x,y


def scale_up(win, ev):
  s = canvas.get_scale()  
  if   chr(ev.keyval) == '+':  canvas.set_scale(s*1.2)
  elif chr(ev.keyval) == '-':  canvas.set_scale(s*.8)
  else: gtk.main_quit()
  print canvas.get_scale()

def button_press(win, ev):
  win.click_x = ev.x
  win.click_y = ev.y
  print win.click_x, win.click_y

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
        
canvas = Canvas(units='mm', scale=1)
canvas.set_size_request(1000, 400)
root = canvas.get_root_item()

# Text(parent=root, x=0, y=0,  text="Hello", font="3")
face = freetype.Face(fontfile)
face.set_char_size(12)

x,y = 0,-100
scale=1

clock_chars = {}

for char in "0123456789:":
  face.load_char(char)
  p,xa,ya = polygons_from_glyph(face.glyph, 0, 0, scale)
  clock_chars[char] = [ p, xa, ya ]

print(clock_chars['1'])

while (y < 100):
  txt = time.strftime('%H:%M:%S')
  x = 0
  for ch in txt:
    for poly in clock_chars[ch][0]: show_path(root,poly, x,y)
    x += clock_chars[ch][1]
  y += clock_chars[txt[0]][2]
  print(txt)
  time.sleep(2)

# for char in "0123456789:,m1To":
#  x,_ = show_char(root,face, char, x, y, scale)
                
win.add(canvas)
win.show_all()

gtk.main()
