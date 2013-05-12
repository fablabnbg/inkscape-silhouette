# (c) 2013 jw@suse.de
# driver for a Graphtec Silhouette Cameo plotter.
# modelled after https://github.com/nosliwneb/robocut.git 
#
import sys, time, usb.core
    
# taken from 
#  robocut/CutDialog.ui
#  robocut/CutDialog.cpp

MEDIA = [
# media, pressure, speed, cap-color, name
  ( 100,   27,     10,  "yellow", "Card without Craft Paper Backing"),
  ( 101,   27,     10,  "yellow", "Card with Craft Paper Backing"),
  ( 102,   10,     10,  "blue",   "Vinyl Sticker"),
  ( 106,   14,     10,  "blue",   "Film Labels"),
  ( 111,   27,     10,  "yellow", "Thick Media"),
  ( 112,    2,     10,  "blue",   "Thin Media"),
  ( 113,   10,     10,  "pen",    "Pen"),
  ( 120,   30,     10,  "blue",   "Bond Paper 13-28 lbs (105g)"),
  ( 121,   30,     10,  "yellow", "Bristol Paper 57-67 lbs (145g)"),
  ( 122,   30,     10,  "yellow", "Cardstock 40-60 lbs (90g)"),
  ( 123,   30,     10,  "yellow", "Cover 40-60 lbs (170g)"),
  ( 124,    1,     10,  "blue",   "Film, Double Matte Translucent"),
  ( 125,    1,     10,  "blue",   "Film, Vinyl With Adhesive Back"),
  ( 126,    1,     10,  "blue",   "Film, Window With Kling Adhesive"),
  ( 127,   30,     10,  "red",    "Index 90 lbs (165g)"),
  ( 128,   20,     10,  "yellow", "Inkjet Photo Paper 28-44 lbs (70g)"),
  ( 129,   27,     10,  "red",    "Inkjet Photo Paper 45-75 lbs (110g)"),
  ( 130,   30,      3,  "red",    "Magnetic Sheet"),
  ( 131,   30,     10,  "blue",   "Offset 24-60 lbs (90g)"),
  ( 132,    5,     10,  "blue",   "Print Paper Light Weight"),
  ( 133,   25,     10,  "yellow", "Print Paper Medium Weight"),
  ( 134,   20,     10,  "blue",   "Sticker Sheet"),
  ( 135,   20,     10,  "red",    "Tag 100 lbs (275g)"),
  ( 136,   30,     10,  "blue",   "Text Paper 24-70 lbs (105g)"),
  ( 137,   30,     10,  "yellow", "Vellum Bristol 57-67 lbs (145g)"),
  ( 138,   30,     10,  "blue",   "Writing Paper 24-70 lbs (105g)"),
  ( 300, None,   None,  "custom", "Custom"),
]

#  robocut/Plotter.h:53 ff
VENDOR_ID_GRAPHTEC = 0x0b4d 
PRODUCT_ID_CC200_20 = 0x110a
PRODUCT_ID_CC300_20 = 0x111a
PRODUCT_ID_SILHOUETTE_SD_1 = 0x111c
PRODUCT_ID_SILHOUETTE_SD_2 = 0x111d
PRODUCT_ID_SILHOUETTE_CAMEO =  0x1121
PRODUCT_ID_SILHOUETTE_PORTRAIT = 0x1123

DEVICE = [
 { 'vendor_id': 0x0b4d, 'product_id': 0x1123, 'name': 'Silhouette Portrait', 
   'width_mm':  203, 'length_mm': 3000, 'regmark': True },
 { 'vendor_id': 0x0b4d, 'product_id': 0x1121, 'name': 'Silhouette Cameo',    
   # margin_top_mm is just for safety when moving backwards with thin media
   # margin_left_mm is a physical limit, but is relative to width_mm!
   'width_mm':  304, 'length_mm': 3000, 'margin_left_mm':9.0, 'margin_top_mm':5.0, 'regmark': True },
 { 'vendor_id': 0x0b4d, 'product_id': 0x110a, 'name': 'Craft Robo CC200-20', 
   'width_mm':  200, 'length_mm': 1000, 'regmark': True },
 { 'vendor_id': 0x0b4d, 'product_id': 0x111a, 'name': 'Craft Robo CC300-20' },
 { 'vendor_id': 0x0b4d, 'product_id': 0x111c, 'name': 'Silhouette SD 1' },
 { 'vendor_id': 0x0b4d, 'product_id': 0x111d, 'name': 'Silhouette SD 2' },
]

def _bbox_extend(bb, x, y):
    # The coordinate system origin is in the top lefthand corner.
    # Downwards and rightwards we count positive. Just like SVG or HPGL.
    # Thus lly is a higher number than ury
    if not 'llx' in bb or x < bb['llx']: bb['llx'] = x
    if not 'urx' in bb or x > bb['urx']: bb['urx'] = x
    if not 'lly' in bb or y > bb['lly']: bb['lly'] = y
    if not 'ury' in bb or y < bb['ury']: bb['ury'] = y

class SilhouetteCameo:
  def __init__(self, log=sys.stderr):
    """ This initializer simply finds the first known device.
        The default paper alignment is left hand side for devices with known width 
        (currently Cameo and Portrait). Otherwise it is right hand side. 
        Use setup() to specify your needs.
    """
    self.leftaligned = False            # True: only works for DEVICE with known hardware.width_mm
    self.log = log
    dev = None
    for hardware in DEVICE:
      dev = usb.core.find(idVendor=hardware['vendor_id'], idProduct=hardware['product_id'])
      if dev:
        dev.hardware = hardware
        break

    if dev is None:
      dev = usb.core.find(idVendor=VENDOR_ID_GRAPHTEC)
      # dev.hardware = { 'name': 'Unknown Graphtec device' }

    if dev is None:
      raise ValueError('No Graphtec Silhouette devices found. Check USB and Power')
    print >>self.log, "%s found on usb bus=%d addr=%d" % (dev.hardware['name'], dev.bus, dev.address)

    if dev.is_kernel_driver_active(0):
      print >>self.log, "is_kernel_driver_active(0) returned nonzero"
      if dev.detach_kernel_driver(0):
        print >>self.log, "detach_kernel_driver(0) returned nonzero"
    dev.reset();

    dev.set_configuration()
    try:
      dev.set_interface_altsetting()      # Probably not really necessary.
    except usb.core.USBError:
      pass
    self.dev = dev
    self.regmark = False                # not yet implemented. See robocut/Plotter.cpp:446
    if 'width_mm' in self.dev.hardware: self.leftaligned = True 

  def write(s, string, timeout=1000):
    """Send a command to the device. Long commands are sent in chunks of 4096 bytes.
       A nonblocking read() is attempted before write(), to find spurious diagnostics."""

    # robocut/Plotter.cpp:73 says: Send in 4096 byte chunks. Not sure where I got this from, I'm not sure it is actually necessary.
    try:
      resp = s.read(timeout=10) # poll the inbound buffer
      if resp:
        print >>s.log, "response before write('%s'): '%s'" % (string, resp)
    except:
      pass
    endpoint = 0x01
    chunksz = 4096
    r = 0
    o = 0
    msg=''
    while o < len(string):
      if o and s.log:
        s.log.write(" %d%% %s\r" % (100.*o/len(string),msg))
        s.log.flush()
      chunk = string[o:o+chunksz]
      try:
        r = s.dev.write(endpoint, string[o:o+chunksz], interface=0, timeout=timeout) 
      except Exception as e:
        # raise USBError(_str_error[ret], ret, _libusb_errno[ret])
        # usb.core.USBError: [Errno 110] Operation timed 
        # print >>s.log, "Write Exception: %s, %s errno=%s" % (type(e), e, e.errno)
        import errno
        if e.errno == errno.ETIMEDOUT:
          time.sleep(1)
          msg += 't'
          continue
      else:
        if len(msg):
          msg = ''
          s.log.write("\n")

      # print >>s.log, "write([%d:%d], len=%d) = %d" % (o,o+chunksz, len(chunk), r)
      if r <= 0:
        raise ValueError('write %d bytes failed: r=%d' % (len(chunk), r))
      o += r
    if o != len(string):
      raise ValueError('write all %d bytes failed: o=%d' % (len(string), o))
      
  def read(s, size=64, timeout=5000):
    """Low level read method"""
    endpoint = 0x82
    data = s.dev.read(endpoint, size, timeout=timeout, interface=0) 
    if data is None:
      raise ValueError('read failed: none')
    return data.tostring()

  def status(s):
    """Query the device status. This can return one of the three strings
       'ready', 'moving', 'unloaded' or a raw (unknown) byte sequence."""
    # Status request.
    s.write("\x1b\x05")
    resp = s.read(timeout=5000)
    if resp[-1] != '\x03': raise ValueError('status response not terminated with 0x03: %s' % (resp[-1]))
    if resp[:-1] == '0': return "ready"
    if resp[:-1] == '1': return "moving"
    if resp[:-1] == '2': return "unloaded"
    return resp[:-1]
  
  def initialize(s):
    """Send the init command. Called by setup()."""
    # taken from robocut/Plotter.cpp:331 ff
    # Initialise plotter.
    s.write("\x1b\x04")

  def home(s):
    """Send the home command. Untested. Called by setup()."""
    s.write("TT\x03")

  def get_version(s):
    """Retrieve the firmware version string from the device."""
    s.write("FG\x03")
    resp = s.read(timeout=10000) # Large timeout because the plotter moves.
    return resp[0:-2]   # chop of 0x03

  def setup(s, media=132, speed=None, pressure=None, pen=None, trackenhancing=False, landscape=False, leftaligned=None):
    """media range is [100..300], default 132, "Print Paper Light Weight"
       speed range is [1..10], default None, from paper (132 -> 10)
       pressure range is [1..33], default None, from paper (132 -> 5)
          Notice: Cameo runs trackenhancing if you select a pressure of 19 or more.
       pen: True or False, default None (media dependant)
       trackenhancing: True or False, default False (setting ignored??)
       landscape: True or False, default False
       leftaligned: Loaded media is aligned left(=True) or right(=False), default: device dependant
    """

    s.initialize()
    s.home()

    if leftaligned is not None:
      s.leftaligned = leftaligned
    if media is not None: 
      if media < 100 or media > 300: media = 300
      s.write("FW%d\x03" % media);
      if pen is None: 
        if media == 113:
          pen = True
        else:
          pen = False
      for i in MEDIA:
        if i[0] == media: 
          print >>s.log, "Media=%d, cap='%s', name='%s'" % (media, i[3], i[4])
          if pressure is None: pressure = i[1]
          if    speed is None:    speed = i[2]

    if speed is not None: 
      if speed < 1: speed = 1
      if speed > 10: speed = 10
      s.write("!%d\x03" % speed);
      print >>s.log, "speed: %d" % speed

    if pressure is not None: 
      if pressure <  1: pressure = 1
      if pressure > 33: pressure = 33
      s.write("FX%d\x03" % pressure);
      # s.write("FX%d,0\x03" % pressure);       # oops, graphtecprint does it like this
      print >>s.log, "pressure: %d" % pressure

    if s.leftaligned:
      print >>s.log, "Loaded media is expected left-aligned."
    else:
      print >>s.log, "Loaded media is expected right-aligned."

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

  def cut_bbox(s, cut):
    """Find the bouding box of the cut, returns (xmin,ymin,xmax,ymax)"""
    bb = {}
    for path in cut:
      for pt in path:
        _bbox_extend(bb,pt[0],pt[1])
    return bb

  def flip_cut(s, cut):
    """this returns a flipped copy of the cut about the x-axis, 
       keeping min and max values as they are."""
    bb = s.cut_bbox(cut)
    new_cut = []
    for path in cut:
      new_path = []
      for pt in path:
        new_path.append((pt[0], bb['lly']+bb['ury']-pt[1]))
      new_cut.append(new_path)
    return new_cut

  def mirror_cut(s, cut):
    """this returns a mirrored copy of the cut about the x-axis, 
       keeping min and max values as they are."""
    bb = s.cut_bbox(cut)
    new_cut = []
    for path in cut:
      new_path = []
      for pt in path:
        new_path.append((bb['llx']+bb['urx']-pt[0], pt[1]))
      new_cut.append(new_path)
    return new_cut

  def page(s, mediawidth=210.0, mediaheight=297.0, margintop=None, marginleft=None, cut=None, offset=None, bboxonly=None):
    """cut is a list of paths. A path is a sequence of 2-tupel, all measured in mm.
           The tool is lowered at the beginning and raised at the end of each path.
       offset = (X_MM, Y_MM) can be specified, to easily move the design to the 
           desired position.  The top and left media margin is always added to the 
           origin. Default: margin only.
       bboxonly:  True for drawing the bounding instead of the actual cut design; 
                  False for not moving at all (just return the bounding box). 
                  Default: None for normal cutting.
       Example: The letter Y can be represented with 
                cut=[[(0,0),(4.5,10),(4.5,20)],[(9,0),(4.5,10)]]
    """
    bbox = { }
    clipcount = 0
    total = 0
    if margintop  is None and 'margin_top_mm'  in s.dev.hardware: margintop  = s.dev.hardware['margin_top_mm']
    if marginleft is None and 'margin_left_mm' in s.dev.hardware: marginleft = s.dev.hardware['margin_left_mm']
    if margintop  is None: margintop = 0
    if marginleft is None: marginleft = 0

    if s.leftaligned and 'width_mm' in s.dev.hardware:
      # marginleft += s.dev.hardware['width_mm'] - mediawidth  ## FIXME: does not work.
      mediawidth =   s.dev.hardware['width_mm']

    print >>s.log, "mediabox: (%g,%g)-(%g,%g)" % (marginleft,margintop, mediawidth,mediaheight)

    # // Begin page definition.
    s.write("FA\x03")   # query someting?
    try:
      resp = s.read(timeout=100)
      if len(resp) > 1:
        print >>s.log, "FA: '%s'" % (resp[:-1])
    except:
      pass

    width  = int(0.5+20.*mediawidth)
    height = int(0.5+20.*mediaheight)
    top    = int(0.5+20.*margintop)
    left  = int(0.5+20.*marginleft)
    if width < left: width=left
    if height < top:  height=top

    x_off = left
    y_off = top
    if offset is not None:
      if type(offset) != type([]) and type(offset) != type(()):
        offset = (offset, 0)
      x_off += int(.5+offset[0]*20.)
      y_off += int(.5+offset[1]*20.)
    # print >>s.log, "x_off=%d, y_off=%d" % (x_off,y_off)

    s.write("FU%d,%d\x03" % (height-top, width-left))
    s.write("FM1\x03")          # // ?
    if s.regmark:
      raise ValueError("regmark code not impl. see robocut/Plotter.cpp:446")
    else:
      s.write("TB50,1\x03")     #; // ???

    # // I think this is the feed command. Sometimes it is 5588 - maybe a maximum?
    s.write("FO%d\x03" % (height-top))

    p = "&100,100,100,\\0,0,Z%d,%d,L0" % (width,height)

    for path in cut:
      if len(path) < 2: continue
      # x = path[len(path)-1][0]*20. + x_off
      # y = path[len(path)-1][1]*20. + y_off
      x = path[0][0]*20. + x_off
      y = path[0][1]*20. + y_off
      _bbox_extend(bbox, x,y)
      total += 1
    
      last_inside = True
      if x < left:  
        x = left
        last_inside = False
      if x > width: 
        x = width
        last_inside = False
      if y < top:    
        y = top
        last_inside = False
      if y > height: 
        y = height
        last_inside = False
      if not last_inside: clipcount += 1

      if bboxonly is None:
        p += ",M%d,%d" % (int(0.5+width-x), int(0.5+y))
      # for j in reversed(range(0,len(path)-1)):
      for j in range(1,len(path)):
        x = path[j][0]*20. + x_off
        y = path[j][1]*20. + y_off
        _bbox_extend(bbox, x,y)
        total += 1

        inside = True
        if x < left:
          x = left
          inside = False
        if x > width:
          x = width
          inside = False
        if y < top:
          y = top
          inside = False
        if y > height:
          y = height
          inside = False
        if not inside: clipcount += 1

        if bboxonly is None:
          if inside and last_inside:
            p += ",D%d,%d" % (int(0.5+width-x), int(0.5+y))
          else:
            # // if outside the range just move
            p += ",M%d,%d" % (int(0.5+width-x), int(0.5+y))
        last_inside = inside

    if bboxonly == True:
      # move the bouding box
      p += ",M%d,%d" % (int(0.5+width-bbox['llx']), int(0.5+bbox['ury']))
      p += ",D%d,%d" % (int(0.5+width-bbox['urx']), int(0.5+bbox['ury']))
      p += ",D%d,%d" % (int(0.5+width-bbox['urx']), int(0.5+bbox['lly']))
      p += ",D%d,%d" % (int(0.5+width-bbox['llx']), int(0.5+bbox['lly']))
      p += ",D%d,%d" % (int(0.5+width-bbox['llx']), int(0.5+bbox['ury']))

    p += "&1,1,1,TB50,0\x03"   #; // TB maybe .. ah I dunno. Need to experiment. No idea what &1,1,1 does either.
    s.write(p)
    s.write("FO0\x03")          # // Feed the page out.
    s.write("H,")               # // Halt?

    return { 
        'bbox': bbox, 
        'clipcount': clipcount,
        'total': total,
        'unit' : 1/20.,
        'mbox': { 'urx':width, 'ury':top, 'llx':left, 'lly':height }
      }

