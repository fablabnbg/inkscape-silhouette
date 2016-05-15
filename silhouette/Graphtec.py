# (c) 2013,2014 jw@suse.de
# (c) 2015 juewei@fabmail.org
#
# Distribute under GPLv2 or ask.
#
# Driver for a Graphtec Silhouette Cameo plotter.
# modelled after https://github.com/nosliwneb/robocut.git
# https://github.com/pmonta/gerber2graphtec/blob/master/file2graphtec
#
# Native resolution of the plotter is 0.05mm -- All movements are integer multiples of this.
#
# 2015-06-04, juewei@fabmail.org using print_function. added wait_for_ready().
#             plot(bboxonly=None) is now the special case for not doing anything. False is normal plot.
# 2015-06-05  Renamed cut_bbox() to find_bbox(). It does not cut anything.
# 2015-06-06  refactored plot_cmds() from plot().

from __future__ import print_function
import sys, time, re

sys_platform = sys.platform.lower()
if sys_platform.startswith('win'):
  import usb.core
elif sys_platform.startswith('darwin'):
  import usb1
  usb1ctx = usb1.USBContext()
else:   # if sys_platform.startswith('linux'):
  try:
    import usb.core		# where???
  except Exception as e:
      try:
          import libusb1 as usb
      except Exception as e1:
	    try:
	      import usb
	    except Exception as e2:
	      print("The python usb module could not be found. Try", file=sys.stderr)
	      print("\t sudo zypper in python-usb \t\t# if you run SUSE", file=sys.stderr)
	      print("\t sudo apt-get install python-usb   \t\t# if you run Ubuntu", file=sys.stderr)
	      print("\n\n\n", file=sys.stderr)
	      raise e2;
	    print("Your python usb module appears to be 0.4.x or older -- We need version 1.x", file=sys.stderr)
	    print("\n\n\n", file=sys.stderr)
	    raise e;
	    # try my own wrapper instead.
	    # import UsbCoreMini as usb
	    # forget this. old 0.4 PyUSB segfaults easily.

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
   'width_mm':  304, 'length_mm': 3000, 'margin_left_mm':9.0, 'margin_top_mm':1.0, 'regmark': True },
 { 'vendor_id': 0x0b4d, 'product_id': 0x112b, 'name': 'Silhouette Cameo2',
   # margin_top_mm is just for safety when moving backwards with thin media
   # margin_left_mm is a physical limit, but is relative to width_mm!
   'width_mm':  304, 'length_mm': 3000, 'margin_left_mm':9.0, 'margin_top_mm':1.0, 'regmark': True },
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
  def __init__(self, log=sys.stderr, no_device=False, progress_cb=None):
    """ This initializer simply finds the first known device.
        The default paper alignment is left hand side for devices with known width
        (currently Cameo and Portrait). Otherwise it is right hand side.
        Use setup() to specify your needs.

        If no_device is True, the usb device is not actually opened, and all
        generated data is discarded.

        The progress_cb is called with the following parameters:
        int(strokes_done), int(strikes_total), str(status_flags)
        The status_flags contain 't' when there was a (non-fatal) write timeout
        on the device.
    """
    self.leftaligned = False            # True: only works for DEVICE with known hardware.width_mm
    self.log = log
    self.progress_cb = progress_cb
    dev = None
    self.margins_printed = None

    if no_device is True:
      self.hardware = { 'name': 'Crashtest Dummy Device' }
    else:
      for hardware in DEVICE:
        if sys_platform.startswith('win'):
          print("device lookup under windows not tested. Help adding code!", file=self.log)
          dev = usb.core.find(idVendor=hardware['vendor_id'], idProduct=hardware['product_id'])

        elif sys_platform.startswith('darwin'):
          dev = usb1ctx.openByVendorIDAndProductID(hardware['vendor_id'], hardware['product_id'])

        else:   # linux
          dev = usb.core.find(idVendor=hardware['vendor_id'], idProduct=hardware['product_id'])
        if dev:
          self.hardware = hardware
          break

      if dev is None:
        if sys_platform.startswith('win'):
          print("device fallback under windows not tested. Help adding code!", file=self.log)
          dev = usb.core.find(idVendor=VENDOR_ID_GRAPHTEC)
          self.hardware = { 'name': 'Unknown Graphtec device' }
          if dev:
            self.hardware['name'] += " 0x%04x" % dev.idProduct
            self.hardware['product_id'] = dev.idProduct
            self.hardware['vendor_id'] = dev.idVendor


        elif sys_platform.startswith('darwin'):
          print("device fallback under macosx not implemented. Help adding code!", file=self.log)

        else:   # linux
          dev = usb.core.find(idVendor=VENDOR_ID_GRAPHTEC)
          self.hardware = { 'name': 'Unknown Graphtec device ' }
          if dev:
            self.hardware['name'] += " 0x%04x" % dev.idProduct
            self.hardware['product_id'] = dev.idProduct
            self.hardware['vendor_id'] = dev.idVendor

      if dev is None:
        msg = ''
        for dev in usb.core.find(find_all=True):
          msg += "(%04x,%04x) " % (dev.idVendor, dev.idProduct)
        raise ValueError('No Graphtec Silhouette devices found.\nCheck USB and Power.\nDevices: '+msg)

      try:
        dev_bus = dev.bus
      except:
        dev_bus = -1

      try:
        dev_addr = dev.address
      except:
        dev_addr = -1

      print("%s found on usb bus=%d addr=%d" % (self.hardware['name'], dev_bus, dev_addr), file=self.log)

      if sys_platform.startswith('win'):
        print("device init under windows not implemented. Help adding code!", file=self.log)

      elif sys_platform.startswith('darwin'):
        dev.claimInterface(0)
        print("device write under macosx not implemented? Check the code!", file=self.log)
        # usb_enpoint = 1
        # dev.bulkWrite(usb_endpoint, data)

      else:     # linux
        try:
          if dev.is_kernel_driver_active(0):
            print("is_kernel_driver_active(0) returned nonzero", file=self.log)
            if dev.detach_kernel_driver(0):
              print("detach_kernel_driver(0) returned nonzero", file=self.log)
        except usb.core.USBError as e:
          print("usb.core.USBError:", e, file=self.log)
          if e.errno == 13:
            msg = """
If you are not running as root, this might be a udev issue.
Try a file /etc/udev/rules.d/99-graphtec-silhouette.rules
with the following example syntax:
SUBSYSTEM=="usb", ATTR{idVendor}=="%04x", ATTR{idProduct}=="%04x", MODE="666"

Then run 'sudo udevadm trigger' to load this file.

Alternatively, you can add yourself to group 'lp' and logout/login.""" % (self.hardware['vendor_id'], self.hardware['product_id'])
            print(msg, file=self.log)
            print(msg, file=sys.stderr)
          sys.exit(0)

        for i in range(5):
          try:
            dev.reset();
            break
          except usb.core.USBError as e:
            print("reset failed: ", e, file=self.log)
            print("retrying reset in 5 sec", file=self.log)
            time.sleep(5)

        dev.set_configuration()
        try:
          dev.set_interface_altsetting()      # Probably not really necessary.
        except usb.core.USBError:
          pass

    self.dev = dev
    self.need_interface = False		# probably never needed, but harmful on some versions of usb.core
    self.regmark = False                # not yet implemented. See robocut/Plotter.cpp:446
    if self.dev is None or 'width_mm' in self.hardware:
      self.leftaligned = True

  def write(s, string, timeout=3000):
    """Send a command to the device. Long commands are sent in chunks of 4096 bytes.
       A nonblocking read() is attempted before write(), to find spurious diagnostics."""

    if s.dev is None: return None

    # robocut/Plotter.cpp:73 says: Send in 4096 byte chunks. Not sure where I got this from, I'm not sure it is actually necessary.
    try:
      resp = s.read(timeout=10) # poll the inbound buffer
      if resp:
        print("response before write('%s'): '%s'" % (string, resp), file=s.log)
    except:
      pass
    endpoint = 0x01
    chunksz = 4096
    r = 0
    o = 0
    msg=''
    retry = 0
    while o < len(string):
      if o:
        if s.progress_cb:
          s.progress_cb(o,len(string),msg)
        elif s.log:
          s.log.write(" %d%% %s\r" % (100.*o/len(string),msg))
          s.log.flush()
      chunk = string[o:o+chunksz]
      try:
        if s.need_interface:
          r = s.dev.write(endpoint, chunk, interface=0, timeout=timeout)
        else:
          r = s.dev.write(endpoint, chunk, timeout=timeout)
      except TypeError as te:
        # write() got an unexpected keyword argument 'interface'
        raise TypeError("Write Exception: %s, %s dev=%s" % (type(te), te, type(s.dev)))
      except AttributeError as ae:
        # write() got an unexpected keyword argument 'interface'
        raise TypeError("Write Exception: %s, %s dev=%s" % (type(ae), ae, type(s.dev)))

      except Exception as e:
        # raise USBError(_str_error[ret], ret, _libusb_errno[ret])
        # usb.core.USBError: [Errno 110] Operation timed
        #print("Write Exception: %s, %s errno=%s" % (type(e), e, e.errno), file=s.log)
        import errno
        try:
          if e.errno == errno.ETIMEDOUT:
            time.sleep(1)
            msg += 't'
            continue
        except Exception as ee:
          msg += "s.dev.write Error: " + ee
      else:
        if len(msg):
          msg = ''
          s.log.write("\n")

      # print("write([%d:%d], len=%d) = %d" % (o,o+chunksz, len(chunk), r), file=s.log)
      if r == 0 and retry < 5:
        time.sleep(1)
        retry += 1
        msg += 'r'
      elif r <= 0:
        raise ValueError('write %d bytes failed: r=%d' % (len(chunk), r))
      else:
        retry = 0
      o += r

    if o != len(string):
      raise ValueError('write all %d bytes failed: o=%d' % (len(string), o))

  def safe_write(s, string):
    """wrapper for write with special emphasis on not to over-load the cutter with long commands."""
    if s.dev is None: return None
    # Silhouette Studio uses packet size of maximal 3k, 1k is default
    safemaxchunksz = 1024
    so = 0
    delimiter = "\x03"
    while so < len(string):
      safechunksz = min(safemaxchunksz, len(string)-so)
      candidate = string[so:so+safechunksz]
      # strip string candidate of unfinished command at its end
      safechunk = candidate[0:(candidate.rfind(delimiter) + 1)]
      s.write(string = safechunk)
      # wait for cutter to finish current chunk, otherwise blocking might occur
      while not s.status() == "ready":
        time.sleep(0.05)
      so += len(safechunk)
      
  def read(s, size=64, timeout=5000):
    """Low level read method"""
    if s.dev is None: return None
    endpoint = 0x82
    if s.need_interface:
      data = s.dev.read(endpoint, size, timeout=timeout, interface=0)
    else:
      data = s.dev.read(endpoint, size, timeout=timeout)
    if data is None:
      raise ValueError('read failed: none')
    return data.tostring()

  def try_read(s, size=64, timeout=1000):
    ret=None
    try:
      ret = s.read(size=size,timeout=timeout)
      print("try_read got: '%s'" % ret)
    except:
      pass
    return ret

  def status(s):
    """Query the device status. This can return one of the three strings
       'ready', 'moving', 'unloaded' or a raw (unknown) byte sequence."""

    if s.dev is None: return 'none'

    # Status request.
    s.write("\x1b\x05")
    resp = "None\x03"
    try:
      resp = s.read(timeout=5000)
    except usb.core.USBError as e:
      print("usb.core.USBError:", e, file=self.log)
      pass
    if resp[-1] != '\x03': raise ValueError('status response not terminated with 0x03: %s' % (resp[-1]))
    if resp[:-1] == '0': return "ready"
    if resp[:-1] == '1': return "moving"
    if resp[:-1] == '2': return "unloaded"
    return resp[:-1]

  def wait_for_ready(s, timeout=30, verbose=True):
    # get_version() is likely to timeout here...
    # if verbose: print("device version: '%s'" % s.get_version(), file=sys.stderr)
    state = s.status()
    for i in range(1, int(timeout*.5)):
      if (state == 'ready'): break
      if verbose: print(" %d/%d: status=%s\r" % (i, int(timeout*.5), state), end='', file=sys.stderr)
      if verbose == False:
        if state == 'unloaded':
          print(" %d/%d: please load media ...\r" % (i, int(timeout*.5)), end='', file=sys.stderr)
        elif i > 5:
          print(" %d/%d: status=%s\r" % (i, int(timeout*.5), state), end='', file=sys.stderr)
      time.sleep(2.0)
      state = s.status()
    if verbose: print("",file=sys.stderr)
    return state

  def initialize(s):
    """Send the init command. Called by setup()."""
    # taken from robocut/Plotter.cpp:331 ff
    # Initialise plotter.
    s.write("\x1b\x04")
    
    # Initial palaver
    try:
      s.write("FG\x03")   # query device name
    except Exception as e:
      raise ValueError("Write Exception: %s, %s errno=%s\n\nFailed to write the first 3 bytes. Permissions? inf-wizard?" % (type(e), e, e.errno))

    try:
      resp = s.read(timeout=1000)
      if len(resp) > 1:
        print("FG: '%s'" % (resp[:-1]), file=s.log)
    except:
      pass
    
    # Additional commands seen in init by Silhouette Studio
    #s.write("FQ0\x03") # asks for something, no idea, just repeating sniffed communication
    #try:
    #  resp = s.read(timeout=1000)
    #  if len(resp) > 1:
    #  print("FQ0: '%s'" % (resp[:-1]), file=s.log)
    #except:
    #  pass
    
    #s.write("FQ2\x03") # asks for something, no idea, just repeating sniffed communication
    #try:
    #  resp = s.read(timeout=1000)
    #  if len(resp) > 1:
    #  print("FQ2: '%s'" % (resp[:-1]), file=s.log)
    #except:
    #  pass
    
    #s.write("TB71\x03") # asks for something, no idea, just repeating sniffed communication
    #try:
    #  resp = s.read(timeout=1000)
    #  if len(resp) > 1:
    #  print("TB71: '%s'" % (resp[:-1]), file=s.log)
    #except:
    #  pass
    
    #s.write("FA\x03") # asks for something, not sure, current position?
    #try:
    #  resp = s.read(timeout=1000)
    #  if len(resp) > 1:
    #  print("FA: '%s'" % (resp[:-1]), file=s.log)
    #except:
    #  pass

  def get_version(s):
    """Retrieve the firmware version string from the device."""

    if s.dev is None: return None

    s.write("FG\x03")
    try:
      resp = s.read(timeout=10000) # Large timeout because the plotter moves.
    except usb.core.USBError as e:
      print("usb.core.USBError:", e, file=s.log)
      resp = "None  "
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
       return_home: True, default, go back to start, after plotting. False: set new page origin below plotted graphics.
    """

    if leftaligned is not None:
      s.leftaligned = leftaligned

    if s.dev is None: return None

    s.initialize()

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
          print("Media=%d, cap='%s', name='%s'" % (media, i[3], i[4]), file=s.log)
          if pressure is None: pressure = i[1]
          if    speed is None:    speed = i[2]

    if speed is not None:
      if speed < 1: speed = 1
      if speed > 10: speed = 10
      s.write("!%d\x03" % speed);
      print("speed: %d" % speed, file=s.log)

    if pressure is not None:
      if pressure <  1: pressure = 1
      if pressure > 33: pressure = 33
      s.write("FX%d\x03" % pressure);
      # s.write("FX%d,0\x03" % pressure);       # oops, graphtecprint does it like this
      print("pressure: %d" % pressure, file=s.log)

    if s.leftaligned:
      print("Loaded media is expected left-aligned.", file=s.log)
    else:
      print("Loaded media is expected right-aligned.", file=s.log)

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

    #FNx, x = 0 seem to be some kind of reset, x = 1: plotter head moves to other
    # side of media (boundary check?), but next cut run will stall
    #TB50,x: x = 1 landscape mode, x = 0 portrait mode
    if landscape is not None:
      if landscape:
        s.write("FN0\x03TB50,1\x03")
      else:
        s.write("FN0\x03TB50,0\x03")
    
    # Don't lift plotter head between paths
    s.write("FE0,0\x03")

  def find_bbox(s, cut):
    """Find the bouding box of the cut, returns (xmin,ymin,xmax,ymax)"""
    bb = {}
    for path in cut:
      for pt in path:
        _bbox_extend(bb,pt[0],pt[1])
    return bb

  def flip_cut(s, cut):
    """this returns a flipped copy of the cut about the x-axis,
       keeping min and max values as they are."""
    bb = s.find_bbox(cut)
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
    bb = s.find_bbox(cut)
    new_cut = []
    for path in cut:
      new_path = []
      for pt in path:
        new_path.append((bb['llx']+bb['urx']-pt[0], pt[1]))
      new_cut.append(new_path)
    return new_cut

  def plot_cmds(s, plist, bbox, x_off_mm, y_off_mm, step_per_mm_along_height = 20.0, step_per_mm_along_width = 19.83):
    """ s is unused.
        bbox coordinates are in device units.
        bbox *should* contain a proper { 'clip': {'llx': , 'lly': , 'urx': , 'ury': } }
        otherwise a hardcoded flipwidth is used to make the coordinate system left aligned.
        x_off_mm, y_off_mm are in mm, relative to the clip urx, ury.
    """

    # Change by Alexander Senger:
    # Well, there seems to be a clash of different coordinate systems here:
    # Cameo uses a system with the origin in the top-left corner, x-axis 
    # running from top to bottom and y-axis from left to right.
    # Inkscape uses a system where the origin is also in the top-left corner
    # but x-axis is running from left to right and y-axis from top to 
    # bottom.
    # The transform between these two systems used so far was to set Cameo in
    # landscape-mode ("FN0.TB50,1" in Cameo-speak) and flip the x-coordinates
    # around the mean x-value (rotate by 90 degrees, mirror and shift x).
    # My proposed change: just swap x and y in the data (mirror about main diagonal)
    # This is easier and avoids utilizing landscape-mode.
    # Why should we bother? Pure technical reason: At the beginning of each cutting run,
    # Cameo makes a small "tick" in the margin of the media to align the blade.
    # This gives a small offset which is automatically compensated for in 
    # portrait mode but not (correctly) in landscape mode.
    # As a result we get varying offsets which can be really annoying if doing precision
    # work.

    x_off = x_off_mm * step_per_mm_along_width
    y_off = y_off_mm * step_per_mm_along_height

    if bbox is None: bbox = {}
    bbox['count'] = 0
    if not 'only' in bbox: bbox['only'] = False
    if 'clip' in bbox and 'urx' in bbox['clip']:
      flipwidth=bbox['clip']['urx']
    if 'clip' in bbox and 'llx' in bbox['clip']:
      x_off += bbox['clip']['llx']
    if 'clip' in bbox and 'ury' in bbox['clip']:
      y_off += bbox['clip']['ury']

    last_inside = True
    plotcmds=[]
    for path in plist:
      if len(path) < 2: continue
      x = path[0][0]*step_per_mm_along_width + x_off
      y = path[0][1]*step_per_mm_along_height + y_off
      _bbox_extend(bbox, x,y)
      bbox['count'] += 1

      if 'clip' in bbox:
        last_inside = True
        if x < bbox['clip']['llx']:
          x = bbox['clip']['llx']
          last_inside = False
        if x > bbox['clip']['urx']:
          x = bbox['clip']['urx']
          last_inside = False
        if y < bbox['clip']['ury']:
          y = bbox['clip']['ury']
          last_inside = False
        if y > bbox['clip']['lly']:
          y = bbox['clip']['lly']
          last_inside = False
        if not last_inside:
          if 'count' in bbox['clip']:
            bbox['clip']['count'] += 1
          else:
            bbox['clip']['count'] = 1

      if bbox['only'] is False:
        plotcmds.append("M%d,%d" % (int(0.5+y), int(0.5+x)))

      for j in range(1,len(path)):
        x = path[j][0]*step_per_mm_along_width + x_off
        y = path[j][1]*step_per_mm_along_height + y_off
        _bbox_extend(bbox, x,y)
        bbox['count'] += 1

        inside = True
        if 'clip' in bbox:
          if x < bbox['clip']['llx']:
            x = bbox['clip']['llx']
            inside = False
          if x > bbox['clip']['urx']:
            x = bbox['clip']['urx']
            inside = False
          if y < bbox['clip']['ury']:
            y = bbox['clip']['ury']
            inside = False
          if y > bbox['clip']['lly']:
            y = bbox['clip']['lly']
            inside = False
          if not inside:
            if 'count' in bbox['clip']:
              bbox['clip']['count'] += 1
            else:
              bbox['clip']['count'] = 1

        if bbox['only'] is False:
          if inside and last_inside:
            plotcmds.append("D%d,%d" % (int(0.5+y), int(0.5+x)))
          else:
            # // if outside the range just move
            plotcmds.append("M%d,%d" % (int(0.5+y), int(0.5+x)))
        last_inside = inside
    return plotcmds


  def plot(s, mediawidth=210.0, mediaheight=297.0, margintop=None, marginleft=None, pathlist=None, offset=None, bboxonly=False, end_paper_offset=10, endposition='below',step_per_mm_along_height = 20.0, step_per_mm_along_width = 20.11):
    """plot sends the pathlist to the device (real or dummy) and computes the
       bounding box of the pathlist, which is returned.

       Each path in pathlist is rendered as a connected stroke (aka "pen_down"
       mode). Movements between paths are not rendered (aka "pen_up" mode).

       A path is a sequence of 2-tupel, all measured in mm.
           The tool is lowered at the beginning and raised at the end of each path.
       offset = (X_MM, Y_MM) can be specified, to easily move the design to the
           desired position.  The top and left media margin is always added to the
           origin. Default: margin only.
       bboxonly:  True for drawing the bounding instead of the actual cut design;
                  None for not moving at all (just return the bounding box).
                  Default: False for normal cutting or drawing.
       end_paper_offset: [mm] adds to the final move, if endposition is 'below'.
                If the end_paper_offset is negative, the end position is within the drawing
                (reverse movmeents are clipped at the home position)
                It reverse over the last home position.
       endpostiton: Default 'below': The media is moved to a position below the actual cut (so another
                can be started without additional steps, also good for using the cross-cutter).
                'start': The media is returned to the positon where the cut started.
       step_per_mm_along_: count of steps made by cutter per mm
                (gives resolution, scales cuts on media). along_height
                designates direction of feeding in cutter (y-axis in
                inkscape), along_width designates direction of movement of
                cutting head (inkscape x-axis).
                Having this setting here allows for easy adaption of new
                machines. Not (yet) exposed to UI.
       Example: The letter Y (20mm tall, 9mm wide) can be generated with
                pathlist=[[(0,0),(4.5,10),(4.5,20)],[(9,0),(4.5,10)]]
    """
    bbox = { }
    if margintop  is None and 'margin_top_mm'  in s.hardware: margintop  = s.hardware['margin_top_mm']
    if marginleft is None and 'margin_left_mm' in s.hardware: marginleft = s.hardware['margin_left_mm']
    if margintop  is None: margintop = 0
    if marginleft is None: marginleft = 0

    # if 'margin_top_mm' in s.hardware:
    #   print("hardware margin_top_mm = %s" % (s.hardware['margin_top_mm']), file=s.log)
    # if 'margin_left_mm' in s.hardware:
    #   print("hardware margin_left_mm = %s" % (s.hardware['margin_left_mm']), file=s.log)

    if s.leftaligned and 'width_mm' in s.hardware:
      # marginleft += s.hardware['width_mm'] - mediawidth  ## FIXME: does not work.
      mediawidth =   s.hardware['width_mm']

    print("mediabox: (%g,%g)-(%g,%g)" % (marginleft,margintop, mediawidth,mediaheight), file=s.log)

    width  = int(0.5+step_per_mm_along_width*mediawidth)
    height = int(0.5+step_per_mm_along_height*mediaheight)
    top    = int(0.5+step_per_mm_along_height*margintop)
    left   = int(0.5+step_per_mm_along_width*marginleft)
    if width < left: width  = left
    if height < top: height = top

    x_off = left
    y_off = top
    if offset is None:
      offset = (0,0)
    else:
      if type(offset) != type([]) and type(offset) != type(()):
        offset = (offset, 0)

    if s.regmark:
      raise ValueError("regmark code not impl. see robocut/Plotter.cpp:446")

    #FMx, x = 0/1: 1 leads to additional horizontal offset of 5 mm, why? Has other profound
    # impact (will not cut in certain configuration if x=0). Seems dangerous. Not used
    # in communtication of Sil Studio with Cameo2.
    #FEx,0 , x = 0 cutting of distinct paths in one go, x = 1 head is lifted at sharp angles
    #\xmin, ymin Zxmax,ymax, designate cutting area
    
    p = "\\0,0\x03Z%d,%d\x03L0\x03FE0,0\x03FF0,0,0\x03" % (height, width) #FIXME Is coordinate swap necessary here?
    s.write(p)

    bbox['clip'] = {'urx':width, 'ury':top, 'llx':left, 'lly':height}
    bbox['only'] = bboxonly
    cmd_list = s.plot_cmds(pathlist,bbox,offset[0],offset[1],step_per_mm_along_height, step_per_mm_along_width)
    p = '\x03'.join(cmd_list)

    if bboxonly == True:
      # move the bouding box
      p = "M%d,%d" % (int(0.5+bbox['ury']), int(0.5+bbox['llx']))
      p += "\x03D%d,%d" % (int(0.5+bbox['ury']), int(0.5+bbox['urx']))
      p += "\x03D%d,%d" % (int(0.5+bbox['lly']), int(0.5+bbox['urx']))
      p += "\x03D%d,%d" % (int(0.5+bbox['lly']), int(0.5+bbox['llx']))
      p += "\x03D%d,%d" % (int(0.5+bbox['ury']), int(0.5+bbox['llx']))
    p += "\x03"   # Properly terminate string of plot commands.
    # potentially long command string needs extra care
    s.safe_write(p)
    
    # Silhouette Cameo2 does not start new job if not properly parked on left side
    # Attention: This needs the media to not extend beyond the left stop
    if not 'llx' in bbox: bbox['llx'] = 0	# survive empty pathlist
    if not 'lly' in bbox: bbox['lly'] = 0
    if not 'urx' in bbox: bbox['urx'] = 0
    if not 'ury' in bbox: bbox['ury'] = 0
    if endposition == 'start':
      new_home = "H\x03"
    else: #includes 'below'
      new_home = "M%d,%d\x03SO0\x03" % (int(0.5+bbox['lly']+end_paper_offset*step_per_mm_along_height), 0) #! axis swapped when using Cameo-system
    #new_home += "FN0\x03TB50,0\x03"
    s.write(new_home)

    return {
        'bbox': bbox,
        'unit' : 1/step_per_mm_along_width, #FIXME small deviations depending on axis not honoured here
        'trailer': new_home
      }


  def move_origin(s, feed_mm):
    new_home = "M%d,%d\x03SO0\x03FN0" % (int(0.5+feed_mm*step_per_mm_along_height),0)
    s.wait_for_ready(verbose=False)
    s.write(new_home)
    s.wait_for_ready(verbose=False)

  def load_dumpfile(s,file):
    """ s is unused
    """
    data1234=None
    for line in open(file,'r').readlines():
      if re.match(r'\s*\[', line):
        exec('data1234='+line)
        break 
      elif re.match(r'\s*<\s*svg', line):
        print(line)
        print("Error: xml/svg file. Please load into inkscape. Use extensions -> export -> sendto silhouette, [x] dump to file")
        return None
      else:
        print(line,end='')
    return data1234
