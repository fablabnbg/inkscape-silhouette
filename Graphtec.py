# (c) 2013 jw@suse.de
# driver for a Graphtec Silhouette Cameo plotter.
# modelled after https://github.com/nosliwneb/robocut.git 
#
import usb.core
import time
    
# taken from 
#  robocut/CutDialog.ui
#  robocut/CutDialog.cpp

MEDIA = [
# media, pressure, speed, name
  ( 100,   27,     10,  "Card without Craft Paper Backing"),
  ( 101,   27,     10,  "Card with Craft Paper Backing"),
  ( 102,   10,     10,  "Vinyl Sticker"),
  ( 106,   14,     10,  "Film Labels"),
  ( 111,   27,     10,  "Thick Media"),
  ( 112,    2,     10,  "Thin Media"),
  ( 113,   10,     10,  "Pen"),
  ( 120,   30,     10,  "Bond Paper 13-28 lbs (105g)"),
  ( 121,   30,     10,  "Bristol Paper 57-67 lbs (145g)"),
  ( 122,   30,     10,  "Cardstock 40-60 lbs (90g)"),
  ( 123,   30,     10,  "Cover 40-60 lbs (170g)"),
  ( 124,    1,     10,  "Film, Double Matte Translucent"),
  ( 125,    1,     10,  "Film, Vinyl With Adhesive Back"),
  ( 126,    1,     10,  "Film, Window With Kling Adhesive"),
  ( 127,   30,     10,  "Index 90 lbs (165g)"),
  ( 128,   20,     10,  "Inkjet Photo Paper 28-44 lbs (70g)"),
  ( 129,   27,     10,  "Inkjet Photo Paper 45-75 lbs (110g)"),
  ( 130,   30,      3,  "Magnetic Sheet"),
  ( 131,   30,     10,  "Offset 24-60 lbs (90g)"),
  ( 132,    5,     10,  "Print Paper Light Weight"),
  ( 133,   25,     10,  "Print Paper Medium Weight"),
  ( 134,   20,     10,  "Sticker Sheet"),
  ( 135,   20,     10,  "Tag 100 lbs (275g)"),
  ( 136,   30,     10,  "Text Paper 24-70 lbs (105g)"),
  ( 137,   30,     10,  "Vellum Bristol 57-67 lbs (145g)"),
  ( 138,   30,     10,  "Writing Paper 24-70 lbs (105g)"),
  ( 300, None,   None,  "Custom"),
]

#  robocut/Plotter.h:53 ff
VENDOR_ID_GRAPHTEC = 0x0b4d 
PRODUCT_ID_CC200_20 = 0x110a
PRODUCT_ID_CC300_20 = 0x111a
PRODUCT_ID_SILHOUETTE_SD_1 = 0x111c
PRODUCT_ID_SILHOUETTE_SD_2 = 0x111d
PRODUCT_ID_SILHOUETTE_CAMEO =  0x1121
PRODUCT_ID_SILHOUETTE_PORTRAIT = 0x1123

class SilhouetteCameo:
  def __init__(self):
    dev = usb.core.find(idVendor=VENDOR_ID_GRAPHTEC, idProduct=PRODUCT_ID_SILHOUETTE_CAMEO)
    if dev is None:
      raise ValueError('Silhouette Cameo not found. Check USB and Power')
    print "Silhouette Cameo found on usb bus=%d addr=%d" % (dev.bus, dev.address)

    if dev.is_kernel_driver_active(0):
      print "is_kernel_driver_active(0) returned nonzero"
      if dev.detach_kernel_driver(0):
        print "detach_kernel_driver(0) returned nonzero"
    dev.reset();

    dev.set_configuration()
    try:
      dev.set_interface_altsetting()      # Probably not really necessary.
    except usb.core.USBError:
      pass
    self.dev = dev

  def write(s, string):
    # robocut/Plotter.cpp:73 says: Send in 4096 byte chunks. Not sure where I got this from, I'm not sure it is actually necessary.
    endpoint = 0x01
    chunksz = 4096
    r = 0
    o = 0
    while o < len(string):
      r += s.dev.write(endpoint, string[o:o+chunksz], interface=0) 
      o += chunksz
    if r != len(string):
      raise ValueError('write %d bytes failed: r=%d' % (len(string), r))
      
  def read(s, size=64, timeout=5000):
    endpoint = 0x82
    data = s.dev.read(endpoint, size, timeout=timeout, interface=0) 
    if data is None:
      raise ValueError('read failed: none')
    return data.tostring()

  def status(s):
    # Status request.
    s.write("\x1b\x05")
    resp = s.read(timeout=5000)
    if len(resp) != 2:    raise ValueError('status response not 2 bytes: %s' % (resp))
    if resp[1] != '\x03': raise ValueError('status response not terminated with 0x03: %s' % (resp[1]))
    if resp[0] == '0': return "ready"
    if resp[0] == '1': return "moving"
    if resp[0] == '2': return "unloaded"
    return resp[0]
  
  def initialize(s):
    # taken from robocut/Plotter.cpp:331 ff
    # Initialise plotter.
    s.write("\x1b\x04")

    for i in range(1,10):
      st = s.status()
      if (st == 'ready'): 
        return st
      print "status=%s" % (st)
      time.sleep(5.0)
    return st
    
  def home(s):
    s.write("TT\x03")

  def get_version(s):
    s.write("FG\x03")
    resp = s.read(timeout=10000) # Large timeout because the plotter moves.
    return resp[0:-2]   # chop of 0x03

  def setup(s, media=132, speed=None, pressure=None, pen=None, trackenhancing=False, landscape=False):
    """media range is [100..300], default 132, "Print Paper Light Weight"
       speed range is [1..10], default None, from paper (132 -> 10)
       pressure range is [1..33], default None, from paper (132 -> 5)
       pen: True or False, default None (media dependant)
       trackenhancing: True or False, default False
       landscape: True or False, default False
    """

    if media is not None: 
      if media < 100 or media > 300: media = 300
      s.write("FW%d\x03" % media);
      if pen is None: 
        if media == 113:
          pen = True
        else:
          pen = False
      for i in MEDIA:
        if i[0] == media: print "Media=%d, name='%s'" % (media, i[3])
    if speed is not None: 
      if speed < 1: speed = 1
      if speed > 10: speed = 10
      s.write("!%d\x03" % speed);
    if pressure is not None: 
      s.write("FX%d\x03" % pressure);

    # robocut/Plotter.cpp:393 says:
    # // I think this sets the distance from the position of the plotter
    # // head to the actual cutting point, maybe in 0.1 mms (todo: Measure blade).
    # // It is 0 for the pen, 18 for cutting.
    # // C possible stands for curvature. Not that any of the other letters make sense...
    cutter = 18
    if pen: cutter = 0
    s.write("FC%d\x03" % cutter)

    if trackenhancing is not None: 
      if trackenhancing: 
        s.write("FY1\x03")
      else:
        s.write("FY0\x03")

    if landscape is not None: 
      if landscape: 
        s.write("FN1\x03")
      else:
        s.write("FN0\x03")

    # // No idea what this does.
    s.write("FE0\x03")

    # // Again, no idea. Maybe something to do with registration marks?
    s.write("TB71\x03")
    resp = s.read(timeout=10000)        # // Allow 10s. Seems reasonable.
    if resp != "    0,    0\x03":
      raise ValueError("setup: Invalid response from plotter.")

  def page(s, mediawidth=210.0, mediaheight=297.0, margintop=5.0, marginright=0, cut=None):
    """cut is a list of paths. A path is a sequence of 2-tupel, all measured in mm.
       The tool is lowered at the beginning and raised at the end of each path.
       Example: The letter Y can be represented with 
                cut=[[(0,0),(4.5,10),(4.5,20)],[(9,0),(4.5,10)]]
    """
    # // Begin page definition.
    regmark = False
    s.write("FA\x03")
    width  = int(0.5+20.*mediawidth)
    height = int(0.5+20.*mediaheight)
    top    = int(0.5+20.*margintop)
    right  = int(0.5+20.*marginright)
    if width < right: width=right
    if height < top:  height=top

    s.write("FU%d,%d\x03" % (height-top, width-right))
    s.write("FM1\x03")          # // ?
    if regmark:
      raise ValueError("regmark code not impl. see robocut/Plotter.cpp:446")
    else:
      s.write("TB50,1\x03")     #; // ???

    # // I think this is the feed command. Sometimes it is 5588 - maybe a maximum?
    s.write("FO%d\x03" % (height-top))

    p = "&100,100,100,\\0,0,Z%d,%d,L0" % (width,height)

    for cuts_i in cut:
      if len(cuts_i) < 2: continue
      x = cuts_i[0][0]*20. 
      y = cuts_i[0][1]*20.
    
      if x < right: x = right
      if x > width: x = width
      if y < top:    y = top
      if y > height: y = height

      p += ",M%d,%d" % (int(0.5+width-x), int(0.5+y))
      for j in range(1,len(cuts_i)):
        x = cuts_i[j][0]*20.
        y = cuts_i[j][1]*20.

        draw = True
        if x < right:
          x = right
          draw = False
        if x > width:
          x = width
          draw = False
        if y < top:
          y = top
          draw = False
        if y > height:
          y = height
          draw = False

        if draw:
          p += ",D%d,%d" % (int(0.5+width-x), int(0.5+y))
        else:
          # // if outside the range just move
          p += ",M%d,%d" % (int(0.5+width-x), int(0.5+y))

    p += "&1,1,1,TB50,0\x03"   #; // TB maybe .. ah I dunno. Need to experiment. No idea what &1,1,1 does either.
    s.write(p)
    s.write("FO0\x03")          # // Feed the page out.
    s.write("H,")               # // Halt?

