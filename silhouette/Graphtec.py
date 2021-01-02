# (c) 2013,2014 jw@suse.de
# (c) 2016 juewei@fabmail.org
# (c) 2016 Alexander Wenger
# (c) 2017 Johann Gail
#
# Distribute under GPLv2 or ask.
#
# Driver for a Graphtec Silhouette Cameo plotter.
# modeled after https://github.com/nosliwneb/robocut.git
# https://github.com/pmonta/gerber2graphtec/blob/master/file2graphtec
#
# Native resolution of the plotter is 0.05mm -- All movements are integer multiples of this.
#
# 2015-06-04, juewei@fabmail.org using print_function. added wait_for_ready().
#             plot(bboxonly=None) is now the special case for not doing anything. False is normal plot.
# 2015-06-05  Renamed cut_bbox() to find_bbox(). It does not cut anything.
# 2015-06-06  refactored plot_cmds() from plot().
# 2016-05-16  no reset per default, this helps usbip.
# 2016-05-21  detect python-usb < 1.0 and give instructions.
# 2017-04-20  Adding Cameo3 USB IDs
# 2020-06-    Adding Cameo4 and refactor code

from __future__ import print_function

import os
import re
import sys
import time

usb_reset_needed = False  # https://github.com/fablabnbg/inkscape-silhouette/issues/10

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/pyusb-1.0.2')      # have a pyusb fallback

sys_platform = sys.platform.lower()
if sys_platform.startswith('win'):
  import usb.core
elif sys_platform.startswith('darwin'):
  import usb1, usb.core
  usb1ctx = usb1.USBContext()
else:   # if sys_platform.startswith('linux'):
  try:
    import usb.core  # where???
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
          raise e2

try:
    try:
      usb_vi = usb.version_info[0]
      usb_vi_str = str(usb.version_info)
    except AttributeError:
      usb_vi = 0
      if sys_platform.startswith('win'):
        usb_vi = 1
        pass # windows does not seem to detect the usb.version , gives attribute error. Other tests of pyusb work, pyusb is installed.
      usb_vi_str = 'unknown'


    if usb_vi < 1:
      print("Your python usb module appears to be "+usb_vi_str+" -- We need version 1.x", file=sys.stderr)
      print("For Debian 8 try:\n  echo > /etc/apt/sources.list.d/backports.list 'deb http://ftp.debian.org debian jessie-backports main\n  apt-get update\n  apt-get -t jessie-backports install python-usb", file=sys.stderr)
      print("\n\n\n", file=sys.stderr)
      print("For Ubuntu 14.04try:\n  pip install pyusb --upgrade", file=sys.stderr)
      print("\n\n\n", file=sys.stderr)
      sys.exit(0)
except NameError:
    pass # on OS X usb.version_info[0] will always fail as libusb1 is being used


# taken from
#  robocut/CutDialog.ui
#  robocut/CutDialog.cpp

MEDIA = [
# CAUTION: keep in sync with sendto_silhouette.inx
# media, pressure, speed, depth, cap-color, name
  ( 100,   27,     10,   1,  "yellow", "Card without Craft Paper Backing"),
  ( 101,   27,     10,   1,  "yellow", "Card with Craft Paper Backing"),
  ( 102,   10,      5,   1,  "blue",   "Vinyl Sticker"),
  ( 106,   14,     10,   1,  "blue",   "Film Labels"),
  ( 111,   27,     10,   1,  "yellow", "Thick Media"),
  ( 112,    2,     10,   1,  "blue",   "Thin Media"),
  ( 113,   18,     10,None,  "pen",    "Pen"),
  ( 120,   30,     10,   1,  "blue",   "Bond Paper 13-28 lbs (105g)"),
  ( 121,   30,     10,   1,  "yellow", "Bristol Paper 57-67 lbs (145g)"),
  ( 122,   30,     10,   1,  "yellow", "Cardstock 40-60 lbs (90g)"),
  ( 123,   30,     10,   1,  "yellow", "Cover 40-60 lbs (170g)"),
  ( 124,    1,     10,   1,  "blue",   "Film, Double Matte Translucent"),
  ( 125,    1,     10,   1,  "blue",   "Film, Vinyl With Adhesive Back"),
  ( 126,    1,     10,   1,  "blue",   "Film, Window With Kling Adhesive"),
  ( 127,   30,     10,   1,  "red",    "Index 90 lbs (165g)"),
  ( 128,   20,     10,   1,  "yellow", "Inkjet Photo Paper 28-44 lbs (70g)"),
  ( 129,   27,     10,   1,  "red",    "Inkjet Photo Paper 45-75 lbs (110g)"),
  ( 130,   30,      3,   1,  "red",    "Magnetic Sheet"),
  ( 131,   30,     10,   1,  "blue",   "Offset 24-60 lbs (90g)"),
  ( 132,    5,     10,   1,  "blue",   "Print Paper Light Weight"),
  ( 133,   25,     10,   1,  "yellow", "Print Paper Medium Weight"),
  ( 134,   20,     10,   1,  "blue",   "Sticker Sheet"),
  ( 135,   20,     10,   1,  "red",    "Tag 100 lbs (275g)"),
  ( 136,   30,     10,   1,  "blue",   "Text Paper 24-70 lbs (105g)"),
  ( 137,   30,     10,   1,  "yellow", "Vellum Bristol 57-67 lbs (145g)"),
  ( 138,   30,     10,   1,  "blue",   "Writing Paper 24-70 lbs (105g)"),
  ( 300, None,   None,None,  "custom", "Custom"),
]

#  robocut/Plotter.h:53 ff
VENDOR_ID_GRAPHTEC = 0x0b4d
PRODUCT_ID_CC200_20 = 0x110a
PRODUCT_ID_CC300_20 = 0x111a
PRODUCT_ID_SILHOUETTE_SD_1 = 0x111c
PRODUCT_ID_SILHOUETTE_SD_2 = 0x111d
PRODUCT_ID_SILHOUETTE_CAMEO =  0x1121
PRODUCT_ID_SILHOUETTE_CAMEO2 =  0x112b
PRODUCT_ID_SILHOUETTE_CAMEO3 =  0x112f
PRODUCT_ID_SILHOUETTE_CAMEO4 =  0x1137
PRODUCT_ID_SILHOUETTE_PORTRAIT = 0x1123
PRODUCT_ID_SILHOUETTE_PORTRAIT2 = 0x1132

# End Of Text - marks the end of a command
CMD_ETX = '\x03'
# Escape - send escape command
CMD_ESC = '\x1b'

### Escape Commands
# End Of Transmission - will initialize the device,
CMD_EOT = '\x04'
# Enquiry - Returns device status
CMD_ENQ = '\x05'
# Negative Acnoledge - Returns device tool setup
CMD_NAK = '\x15'

SILHOUETTE_CAMEO4_TOOL_EMPTY = 0
SILHOUETTE_CAMEO4_TOOL_RATCHETBLADE = 1
SILHOUETTE_CAMEO4_TOOL_AUTOBLADE = 2
SILHOUETTE_CAMEO4_TOOL_DEEPCUTBLADE = 3
SILHOUETTE_CAMEO4_TOOL_KRAFTBLADE = 4
SILHOUETTE_CAMEO4_TOOL_ROTARYBLADE = 5
SILHOUETTE_CAMEO4_TOOL_PEN = 7
SILHOUETTE_CAMEO4_TOOL_ERROR = 255

DEVICE = [
 { 'vendor_id': VENDOR_ID_GRAPHTEC, 'product_id': PRODUCT_ID_SILHOUETTE_PORTRAIT, 'name': 'Silhouette Portrait',
   'width_mm':  206, 'length_mm': 3000, 'regmark': True },
 { 'vendor_id': VENDOR_ID_GRAPHTEC, 'product_id': PRODUCT_ID_SILHOUETTE_PORTRAIT2, 'name': 'Silhouette Portrait2',
   'width_mm':  203, 'length_mm': 3000, 'regmark': True },
 { 'vendor_id': VENDOR_ID_GRAPHTEC, 'product_id': PRODUCT_ID_SILHOUETTE_CAMEO, 'name': 'Silhouette Cameo',
   # margin_top_mm is just for safety when moving backwards with thin media
   # margin_left_mm is a physical limit, but is relative to width_mm!
   'width_mm':  304, 'length_mm': 3000, 'margin_left_mm':9.0, 'margin_top_mm':1.0, 'regmark': True },
 { 'vendor_id': VENDOR_ID_GRAPHTEC, 'product_id': PRODUCT_ID_SILHOUETTE_CAMEO2, 'name': 'Silhouette Cameo2',
   # margin_top_mm is just for safety when moving backwards with thin media
   # margin_left_mm is a physical limit, but is relative to width_mm!
   'width_mm':  304, 'length_mm': 3000, 'margin_left_mm':9.0, 'margin_top_mm':1.0, 'regmark': True },
 { 'vendor_id': VENDOR_ID_GRAPHTEC, 'product_id': PRODUCT_ID_SILHOUETTE_CAMEO3, 'name': 'Silhouette Cameo3',
   # margin_top_mm is just for safety when moving backwards with thin media
   # margin_left_mm is a physical limit, but is relative to width_mm!
   'width_mm':  304.8, 'length_mm': 3000, 'margin_left_mm':0.0, 'margin_top_mm':0.0, 'regmark': True },
 { 'vendor_id': VENDOR_ID_GRAPHTEC, 'product_id': PRODUCT_ID_SILHOUETTE_CAMEO4, 'name': 'Silhouette Cameo4',
   # margin_top_mm is just for safety when moving backwards with thin media
   # margin_left_mm is a physical limit, but is relative to width_mm!
   'width_mm':  304.8, 'length_mm': 3000, 'margin_left_mm':0.0, 'margin_top_mm':0.0, 'regmark': True },
 { 'vendor_id': VENDOR_ID_GRAPHTEC, 'product_id': PRODUCT_ID_CC200_20, 'name': 'Craft Robo CC200-20',
   'width_mm':  200, 'length_mm': 1000, 'regmark': True },
 { 'vendor_id': VENDOR_ID_GRAPHTEC, 'product_id': PRODUCT_ID_CC300_20, 'name': 'Craft Robo CC300-20' },
 { 'vendor_id': VENDOR_ID_GRAPHTEC, 'product_id': PRODUCT_ID_SILHOUETTE_SD_1, 'name': 'Silhouette SD 1' },
 { 'vendor_id': VENDOR_ID_GRAPHTEC, 'product_id': PRODUCT_ID_SILHOUETTE_SD_2, 'name': 'Silhouette SD 2' },
]


def _bbox_extend(bb, x, y):
    # The coordinate system origin is in the top lefthand corner.
    # Downwards and rightwards we count positive. Just like SVG or HPGL.
    # Thus lly is a higher number than ury
    if not 'llx' in bb or x < bb['llx']: bb['llx'] = x
    if not 'urx' in bb or x > bb['urx']: bb['urx'] = x
    if not 'lly' in bb or y > bb['lly']: bb['lly'] = y
    if not 'ury' in bb or y < bb['ury']: bb['ury'] = y


#   1   mm =   20 SU
#   1   in =  508 SU
#   8.5 in = 4318 SU
#  11   in = 5588 SU

def _mm_2_SU(mm):
  """Convert mm to SU (SilhuetteUnit) using round

  Parameters
  ----------
      mm : int, float
          input millimetre

  Returns
  -------
      int
          output SU
  """
  return int(round(mm * 20.0))

def _inch_2_SU(inch):
  """Convert inch to SU (SilhuetteUnit) using round

  Parameters
  ----------
      inch : int, float
          input inch

  Returns
  -------
      int
          output SU
  """
  return int(round(inch * 508.0))


class SilhouetteCameoTool:
  def __init__(self, toolholder=1):
    if toolholder is None:
      toolholder = 1
    self.toolholder = toolholder

  def select(self):
    """ select tool command """
    return "J%d" % self.toolholder

  def pressure(self, pressure):
    """ set pressure command """
    return "FX%d,%d" % (pressure, self.toolholder)

  def speed(self, speed):
    """ set speed command """
    return "!%d,%d" % (speed, self.toolholder)

  def depth(self, depth):
    """ set depth command """
    return "TF%d,%d" % (depth, self.toolholder)

  def cutter_offset(self, xmm, ymm):
    """ set cutter offset command using mm """
    return "FC%d,%d,%d" % (_mm_2_SU(xmm), _mm_2_SU(ymm), self.toolholder)

  def lift(self, lift):
    """ set lift command """
    if lift:
      return "FE1,%d" % self.toolholder
    else:
      return "FE0,%d" % self.toolholder

  def sharpen_corners(self, start, end):
    return [
      "FF%d,0,%d" % (start, self.toolholder),
      "FF%d,%d,%d" % (start, end, self.toolholder)]

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
        try:
            for dev in usb.core.find(find_all=True):
              msg += "(%04x,%04x) " % (dev.idVendor, dev.idProduct)
        except NameError:
            msg += "unable to list devices on OS X"
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

        if usb_reset_needed:
          for i in range(5):
            try:
              dev.reset()
              break
            except usb.core.USBError as e:
              print("reset failed: ", e, file=self.log)
              print("retrying reset in 5 sec", file=self.log)
              time.sleep(5)

        try:
          dev.set_configuration()
          dev.set_interface_altsetting()      # Probably not really necessary.
        except usb.core.USBError:
          pass

    self.dev = dev
    self.need_interface = False         # probably never needed, but harmful on some versions of usb.core
    self.regmark = False                # not yet implemented. See robocut/Plotter.cpp:446
    if self.dev is None or 'width_mm' in self.hardware:
      self.leftaligned = True
    self.enable_sw_clipping = True

  def product_id(self):
    return self.hardware['product_id'] if 'product_id' in self.hardware else None

  def write(self, data, timeout=10000):
    """Send a command to the device. Long commands are sent in chunks of 4096 bytes.
       A nonblocking read() is attempted before write(), to find spurious diagnostics."""

    if self.dev is None: return None

    # convert string to bytes if required
    if isinstance(data, str):
      data = data.encode()

    # robocut/Plotter.cpp:73 says: Send in 4096 byte chunks. Not sure where I got this from, I'm not sure it is actually necessary.
    try:
      resp = self.read(timeout=10) # poll the inbound buffer
      if resp:
        print("response before write('%s'): '%s'" % (data, resp), file=self.log)
    except:
      pass
    endpoint = 0x01
    chunksz = 4096
    r = 0
    o = 0
    msg=''
    retry = 0
    while o < len(data):
      if o:
        if self.progress_cb:
          self.progress_cb(o,len(data),msg)
        elif self.log:
          self.log.write(" %d%% %s\r" % (100.*o/len(data),msg))
          self.log.flush()
      chunk = data[o:o+chunksz]
      try:
        if self.need_interface:
          try:
            r = self.dev.write(endpoint, chunk, interface=0, timeout=timeout)
          except AttributeError:
            r = self.dev.bulkWrite(endpoint, chunk, interface=0, timeout=timeout)
        else:
          try:
            r = self.dev.write(endpoint, chunk, timeout=timeout)
          except AttributeError:
            r = self.dev.bulkWrite(endpoint, chunk, timeout=timeout)
      except TypeError as te:
        # write() got an unexpected keyword argument 'interface'
        raise TypeError("Write Exception: %s, %s dev=%s" % (type(te), te, type(self.dev)))
      except AttributeError as ae:
        # write() got an unexpected keyword argument 'interface'
        raise TypeError("Write Exception: %s, %s dev=%s" % (type(ae), ae, type(self.dev)))

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
          msg += "s.dev.write Error:  {}".format(ee)
      else:
        if len(msg):
          msg = ''
          self.log.write("\n")

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

    if o != len(data):
      raise ValueError('write all %d bytes failed: o=%d' % (len(data), o))

  def safe_write(self, data):
    """wrapper for write with special emphasis on not to over-load the cutter with long commands."""
    if self.dev is None: return None

    # convert string to bytes if required
    if isinstance(data, str):
      data = data.encode()

    # Silhouette Studio uses packet size of maximal 3k, 1k is default
    safemaxchunksz = 1024
    so = 0
    delimiter = CMD_ETX.encode()
    while so < len(data):
      safechunksz = min(safemaxchunksz, len(data)-so)
      candidate = data[so:so+safechunksz]
      # strip string candidate of unfinished command at its end
      safechunk = candidate[0:(candidate.rfind(delimiter) + 1)]
      self.write(data = safechunk)
      # wait for cutter to finish current chunk, otherwise blocking might occur
      while not self.status() == "ready":
        time.sleep(0.05)
      so += len(safechunk)

  def send_command(self, cmd, timeout=10000):
    """ Sends a command or a list of commands of type string """
    if isinstance(cmd, str):
      data = cmd
    elif isinstance(cmd, list) and isinstance(cmd[0], str):
      data = CMD_ETX.join(cmd)
    else:
      raise TypeError("Send Command Exception: %s " % type(cmd))
    self.write(data + CMD_ETX, timeout)

  def safe_send_command(self, cmd):
    """ Sends a command or a list of commands of type string """
    if isinstance(cmd, str):
      data = cmd
    elif isinstance(cmd, list):
      if not cmd:
        # if list of commands is empty this function shall do nothing
        return
      else:
        # list must not contain anything but strings
        for c in cmd:
          if not isinstance(c, str):
            raise TypeError("Send Command Exception: %s " % type(cmd))
        data = CMD_ETX.join(cmd)
    else:
      raise TypeError("Send Command Exception: %s " % type(cmd))
    self.safe_write(data + CMD_ETX)

  def send_escape(self, esc):
    """ Sends a Escape Command """
    if isinstance(esc, str):
      self.write(CMD_ESC + esc)
    else:
      raise TypeError("Send Escape Exception: %s " % type(esc))

  def read(self, size=64, timeout=5000):
    """Low level read method"""
    if self.dev is None: return None
    endpoint = 0x82
    if self.need_interface:
        try:
            data = self.dev.read(endpoint, size, timeout=timeout, interface=0)
        except AttributeError:
            data = self.dev.bulkRead(endpoint, size, timeout=timeout, interface=0)
    else:
        try:
            data = self.dev.read(endpoint, size, timeout=timeout)
        except AttributeError:
            data = self.dev.bulkRead(endpoint, size, timeout=timeout)
    if data is None:
      raise ValueError('read failed: none')
    if isinstance(data, (str, bytes, bytearray)):
        return data.decode()
    else:
        try:
            return data.tobytes().decode() # with py3
        except:
            return data.tostring().decode() # with py2/3 - dropped in py39

  def try_read(self, size=64, timeout=1000):
    ret=None
    try:
      ret = self.read(size=size,timeout=timeout)
      print("try_read got: '%s'" % ret)
    except:
      pass
    return ret

  def send_receive_command(self, cmd, tx_timeout=10000, rx_timeout=1000):
      self.send_command(cmd, tx_timeout)
      try:
        resp = self.read(timeout=rx_timeout)
        if len(resp) > 1:
          return resp[:-1]
      except:
        pass
      return None

  def status(self):
    """Query the device status. This can return one of the three strings
       'ready', 'moving', 'unloaded' or a raw (unknown) byte sequence."""

    if self.dev is None: return 'none'

    # Status request.
    self.send_escape(CMD_ENQ)
    resp = b"None\x03"
    try:
      resp = self.read(timeout=5000)
    except usb.core.USBError as e:
      print("usb.core.USBError:", e, file=self.log)
      pass
    if resp[-1] != CMD_ETX: raise ValueError('status response not terminated with 0x03: %s' % (resp[-1]))
    if resp[:-1] == '0': return "ready"
    if resp[:-1] == '1': return "moving"
    if resp[:-1] == '2': return "unloaded"
    return resp[:-1]

  def get_tool_setup(self):
    """ gets the type of the tools installed in Cameo 4 """
    if self.dev is None:
      return 'none'

    if self.product_id() != PRODUCT_ID_SILHOUETTE_CAMEO4:
      return 'none'

    # tool setup request.
    self.send_escape(CMD_NAK)
    try:
      resp = self.read(timeout=1000)
      if len(resp) > 1:
        return resp[:-1]
    except:
      pass
    return 'none'

  def wait_for_ready(self, timeout=30, verbose=True):
    # get_version() is likely to timeout here...
    # if verbose: print("device version: '%s'" % s.get_version(), file=sys.stderr)
    state = self.status()
    for i in range(1, int(timeout*.5)):
      if (state == 'ready'): break
      if verbose: print(" %d/%d: status=%s\r" % (i, int(timeout*.5), state), end='', file=sys.stderr)
      if verbose == False:
        if state == 'unloaded':
          print(" %d/%d: please load media ...\r" % (i, int(timeout*.5)), end='', file=sys.stderr)
        elif i > 5:
          print(" %d/%d: status=%s\r" % (i, int(timeout*.5), state), end='', file=sys.stderr)
      time.sleep(2.0)
      state = self.status()
    if verbose: print("",file=sys.stderr)
    return state

  def initialize(self):
    """Send the init command. Called by setup()."""
    # taken from robocut/Plotter.cpp:331 ff
    # Initialize plotter.
    try:
      self.send_escape(CMD_EOT)
    except Exception as e:
      raise ValueError("Write Exception: %s, %s errno=%s\n\nFailed to write the first 3 bytes. Permissions? inf-wizard?" % (type(e), e, e.errno))

    # Initial palaver
    print("Device Version: '%s'" % self.get_version(), file=self.log)

    # Additional commands seen in init by Silhouette Studio
    """
    # Get Upper Left Coords: 2 six digit numbers.
    resp = self.send_receive_command("[")
    if resp:
      # response '0,0'
      print("[: '%s'" % resp, file=self.log)

    # Get Lower Right Coordinates: 2 six digit numbers
    resp = self.send_receive_command("U")
    if resp:
      # response '20320,4120' max. usable print range?
      # response ' 20320,   3840' on Portrait
      print("U: '%s'" % resp, file=self.log)

    # Unknown: 1 five digit number. Maybe last speed set?
    resp = self.send_receive_command("FQ0")
    if resp:
      # response '10'
      # response '    5' on portrait
      print("FQ0: '%s'" % resp, file=self.log)

    # Unknown: 1 five digit number. Maybe last blade offset or last pressure?
    resp = self.send_receive_command("FQ2")
    if resp:
      # response '18'
      # response '   17' on portrait
      print("FQ2: '%s'" % resp, file=self.log)
    """

    if self.product_id() in [PRODUCT_ID_SILHOUETTE_CAMEO3, PRODUCT_ID_SILHOUETTE_CAMEO4]:

      # Unknown: 2 five digit numbers. Probably machine stored calibration offset of the regmark sensor optics
      resp = self.send_receive_command("TB71")
      if resp:
        # response '    0,    0' on portrait
        print("TB71: '%s'" % resp, file=self.log)
      # Unknown: 2 five digit numbers. Probably machine stored calibration factors of carriage and roller (carriage, roller / unit 1/100% i.e. 0.0001)
      resp = self.send_receive_command("FA")
      if resp:
        # response '    0,    0' on portrait
        print("FA: '%s'" % resp, file=self.log)

    # Silhouette Studio does not appear to issue this command when using a cameo 4
    if self.product_id() == PRODUCT_ID_SILHOUETTE_CAMEO3:
      resp = self.send_receive_command("TC")
      if resp:
        # response '0,0'
        print("TC: '%s'" % resp, file=self.log)

  def get_version(self):
    """Retrieve the firmware version string from the device."""

    if self.dev is None: return None

    return self.send_receive_command("FG", rx_timeout = 10000)

  def set_boundary(self, top, left, bottom, right):
    """ Sets boundary box """
    self.send_command(["\\%d,%d" % (top, left), "Z%d,%d" % (bottom, right)])

  def set_cutting_mat(self, cuttingmat, mediawidth, mediaheight):
    """Setting Cutting mat only for Cameo 3 and 4

    Parameters
    ----------
        cuttingmat : {'cameo_12x12', 'cameo_12x24'. None}
            type of the cutting mat
        mediawidth : float
            width of the media
        mediaheight : float
            height of the media
    """
    if self.product_id() not in [PRODUCT_ID_SILHOUETTE_CAMEO3, PRODUCT_ID_SILHOUETTE_CAMEO4]:
      return
    if cuttingmat == 'cameo_12x12':
      self.send_command("TG1")
    elif cuttingmat == 'cameo_12x24':
      self.send_command("TG2")
    else:
      self.send_command("TG0")

    #FNx, x = 0 seem to be some kind of reset, x = 1: plotter head moves to other
    # side of media (boundary check?), but next cut run will stall
    #TB50,x: x = 1 landscape mode, x = 0 portrait mode
    self.send_command(["FN0", "TB50,0"])

    if cuttingmat == 'cameo_12x12':
      self.set_boundary(0, 0, _inch_2_SU(12), _inch_2_SU(12))
    elif cuttingmat == 'cameo_12x24':
      self.set_boundary(0, 0, _inch_2_SU(24), _inch_2_SU(12))
    else:
      bottom = _mm_2_SU(self.hardware['length_mm'] if 'length_mm' in self.hardware else mediaheight)
      right = _mm_2_SU(self.hardware['width_mm'] if 'width_mm' in self.hardware else mediawidth)
      self.set_boundary(0, 0, bottom, right)

  def setup(self, media=132, speed=None, pressure=None, toolholder=None, pen=None, cuttingmat=None, sharpencorners=False, sharpencorners_start=0.1, sharpencorners_end=0.1, autoblade=False, depth=None, sw_clipping=True, trackenhancing=False, bladediameter=0.9, landscape=False, leftaligned=None, mediawidth=210.0, mediaheight=297.0):
    """Setup the Silhouette Device

    Parameters
    ----------
        media : int, optional
            range is [100..300], "Print Paper Light Weight". Defaults to 132.
        speed : int, optional
            range is [1..10]. Defaults to None, from paper (132 -> 10).
        pressure : int, optional
            range is [1..33], Notice: Cameo runs trackenhancing if you select a pressure of 19 or more. Defaults to None, from paper (132 -> 5).
        toolholder : int, optional
            range is [1..2]. Defaults to 1.
        pen : bool, optional
            media dependent. Defaults to None.
        cuttingmat : {'cameo_12x12', 'cameo_12x24'}, optional
            setting the cutting mat. Defaults to None.
        sharpencorners : bool, optional
            Defaults to False.
        sharpencorners_start : float, optional
            Defaults to 0.1.
        sharpencorners_end : float, optional
            Defaults to 0.1.
        autoblade : bool, optional
            Defaults to False.
        depth : int, optional
            range is [0..10] Defaults to None.
        sw_clipping : bool, optional
            Defaults to True.
        trackenhancing : bool, optional
            Defaults to False.
        bladediameter : float, optional
            Defaults to 0.9.
        landscape : bool, optional
            Defaults to False.
        leftaligned : bool, optional
            Loaded media is aligned left(=True) or right(=False). Defaults to device dependant.
        mediawidth : float, optional
            Defaults to 210.0.
        mediaheight : float, optional
            Defaults to 297.0.
    """


    if leftaligned is not None:
      self.leftaligned = leftaligned

    if self.dev is None: return None

    self.initialize()

    self.set_cutting_mat(cuttingmat, mediawidth, mediaheight)

    if media is not None:
      if media < 100 or media > 300: media = 300

      # Silhouette Studio does not appear to issue this command
      if self.product_id() not in [PRODUCT_ID_SILHOUETTE_CAMEO3, PRODUCT_ID_SILHOUETTE_CAMEO4]:
        self.send_command("FW%d" % media)

      if pen is None:
        if media == 113:
          pen = True
        else:
          pen = False
      for i in MEDIA:
        if i[0] == media:
          print("Media=%d, cap='%s', name='%s'" % (media, i[4], i[5]), file=self.log)
          if pressure is None: pressure = i[1]
          if speed is None:    speed = i[2]
          if depth is None:    depth = i[3]
          break

    tool = SilhouetteCameoTool(toolholder)

    if toolholder is None:
      toolholder = 1

    if self.product_id() in [PRODUCT_ID_SILHOUETTE_CAMEO3, PRODUCT_ID_SILHOUETTE_CAMEO4]:
      self.send_command(tool.select())

    print("toolholder: %d" % toolholder, file=self.log)

    # cameo 4 sets some parameters two times (force, acceleration, Cutter offset)
    if self.product_id() == PRODUCT_ID_SILHOUETTE_CAMEO4:
      if pressure is not None:
        if pressure <  1: pressure = 1
        if pressure > 33: pressure = 33
        self.send_command(tool.pressure(pressure))
        print("pressure: %d" % pressure, file=self.log)

        # on first connection acceleration is always set to 0
        self.send_command(self.acceleration_cmd(0))

      if speed is not None:
        if speed < 1: speed = 1
        if speed > 10: speed = 10
        self.send_command(tool.speed(speed))
        print("speed: %d" % speed, file=self.log)

      # set cutter offset a first time (seems to always be 0mm x 0.05mm)
      self.send_command(tool.cutter_offset(0, 0.05))

      # lift tool between paths
      self.send_command(tool.lift(sharpencorners))

      if pen:
        self.send_command(tool.sharpen_corners(0, 0))
      else:
        # start and end for sharpen corners is transmitted in tenth of a millimeter NOT in SUs
        sharpencorners_start = int((sharpencorners_start + 0.05) * 10.0)
        sharpencorners_end = int((sharpencorners_end + 0.05) * 10.0)
        self.send_command(tool.sharpen_corners(sharpencorners_start, sharpencorners_end))

      # set pressure a second time (don't know why, just reproducing)
      if pressure is not None:
        if pressure <  1: pressure = 1
        if pressure > 33: pressure = 33
        self.send_command(tool.pressure(pressure))
        print("pressure: %d" % pressure, file=self.log)
        self.send_command(self.acceleration_cmd(3))

      # set cutter offset a second time (this time with blade specific parameters)
      if pen:
        self.send_command(tool.cutter_offset(0, 0.05))
      else:
        self.send_command(tool.cutter_offset(bladediameter, 0.05))
    else:
      if speed is not None:
        if speed < 1: speed = 1
        if speed > 10: speed = 10
        if self.product_id() == PRODUCT_ID_SILHOUETTE_CAMEO3:
          self.send_command(tool.speed(speed))
        else:
          self.send_command("!%d" % speed)
        print("speed: %d" % speed, file=self.log)

      if pressure is not None:
        if pressure <  1: pressure = 1
        if pressure > 33: pressure = 33
        if self.product_id() == PRODUCT_ID_SILHOUETTE_CAMEO3:
          self.send_command(tool.pressure(pressure))
        else:
          self.send_command("FX%d" % pressure)
          # s.write(b"FX%d,0\x03" % pressure);       # oops, graphtecprint does it like this
        print("pressure: %d" % pressure, file=self.log)

      if self.product_id() == PRODUCT_ID_SILHOUETTE_CAMEO3:
        if pen:
          self.send_command(tool.cutter_offset(0, 0.05))

      if self.leftaligned:
        print("Loaded media is expected left-aligned.", file=self.log)
      else:
        print("Loaded media is expected right-aligned.", file=self.log)

      # Lift plotter head at sharp corners
      if self.product_id() == PRODUCT_ID_SILHOUETTE_CAMEO3:
        self.send_command(tool.lift(sharpencorners))

        if pen:
          self.send_command(tool.sharpen_corners(0, 0))
        else:
          # TODO: shouldn't be this also SU? why * 10 ?
          sharpencorners_start = int((sharpencorners_start + 0.05) * 10.0)
          sharpencorners_end = int((sharpencorners_end + 0.05) * 10.0)
          self.send_command(tool.sharpen_corners(sharpencorners_start, sharpencorners_end))

      # robocut/Plotter.cpp:393 says:
      # It is 0 for the pen, 18 for cutting. Default diameter of a blade is 0.9mm
      # C possible stands for curvature. Not that any of the other letters make sense...
      # C possible stands for circle.
      # This value is the circle diameter which is executed on direction changes on corners to adjust the blade.
      # Seems to be limited to 46 or 47. Values above does keep the last setting on the device.
      if self.product_id() == PRODUCT_ID_SILHOUETTE_CAMEO3:
        if not pen:
          self.send_command([
            tool.cutter_offset(0, 0.05),
            tool.cutter_offset(bladediameter, 0.05)])
      else:
        if pen:
          self.send_command("FC0")
        else:
          self.send_command("FC%d" % _mm_2_SU(bladediameter))

    if self.product_id() in [PRODUCT_ID_SILHOUETTE_CAMEO3, PRODUCT_ID_SILHOUETTE_CAMEO4]:
      if autoblade and depth is not None:
        if toolholder == 1:
          if depth < 0: depth = 0
          if depth > 10: depth = 10
          self.send_command(tool.depth(depth))
          print("depth: %d" % depth, file=self.log)

    self.enable_sw_clipping = sw_clipping

    # if enabled, rollers three times forward and back.
    # needs a pressure of 19 or more, else nothing will happen
    if trackenhancing is not None:
      if trackenhancing:
        self.send_command("FY0")
      else:
        if self.product_id() in [PRODUCT_ID_SILHOUETTE_CAMEO3, PRODUCT_ID_SILHOUETTE_CAMEO4]:
          pass
        else:
          self.send_command("FY1")

    #FNx, x = 0 seem to be some kind of reset, x = 1: plotter head moves to other
    # side of media (boundary check?), but next cut run will stall
    #TB50,x: x = 1 landscape mode, x = 0 portrait mode
    if self.product_id() in [PRODUCT_ID_SILHOUETTE_CAMEO3, PRODUCT_ID_SILHOUETTE_CAMEO4]:
      pass
    else:
      if landscape is not None:
        if landscape:
          self.send_command(["FN0", "TB50,1"])
        else:
          self.send_command(["FN0", "TB50,0"])

      # Don't lift plotter head between paths
      self.send_command("FE0,0")

  def find_bbox(self, cut):
    """Find the bounding box of the cut, returns (xmin,ymin,xmax,ymax)"""
    bb = {}
    for path in cut:
      for pt in path:
        _bbox_extend(bb,pt[0],pt[1])
    return bb

  def flip_cut(self, cut):
    """this returns a flipped copy of the cut about the y-axis,
       keeping min and max values as they are."""
    bb = self.find_bbox(cut)
    new_cut = []
    for path in cut:
      new_path = []
      for pt in path:
        new_path.append((pt[0], bb['lly']+bb['ury']-pt[1]))
      new_cut.append(new_path)
    return new_cut

  def mirror_cut(self, cut):
    """this returns a mirrored copy of the cut about the x-axis,
       keeping min and max values as they are."""
    bb = self.find_bbox(cut)
    new_cut = []
    for path in cut:
      new_path = []
      for pt in path:
        new_path.append((bb['llx']+bb['urx']-pt[0], pt[1]))
      new_cut.append(new_path)
    return new_cut

  def acceleration_cmd(self, acceleration):
    """ TJa """
    return "TJ%d" % acceleration

  def move_mm_cmd(self, mmy, mmx):
    """ My,x """
    return "M%d,%d" % (_mm_2_SU(mmy), _mm_2_SU(mmx))

  def draw_mm_cmd(self, mmy, mmx):
    """ Dy,x """
    return "D%d,%d" % (_mm_2_SU(mmy), _mm_2_SU(mmx))

  def upper_left_mm_cmd(self, mmy, mmx):
    r""" \y,x """
    return "\\%d,%d" % (_mm_2_SU(mmy), _mm_2_SU(mmx))

  def lower_right_mm_cmd(self, mmy, mmx):
    """ Zy,x """
    return "Z%d,%d" % (_mm_2_SU(mmy), _mm_2_SU(mmx))

  def automatic_regmark_test_mm_cmd(self, height, width, top, left):
    """ TB123,h,w,t,l """
    return "TB123,%d,%d,%d,%d" % (_mm_2_SU(height), _mm_2_SU(width), _mm_2_SU(top), _mm_2_SU(left))

  def manual_regmark_mm_cmd(self, height, width):
    """ TB23,h,w """
    return "TB23,%d,%d" % (_mm_2_SU(height), _mm_2_SU(width))


  def plot_cmds(self, plist, bbox, x_off, y_off):
    """
        bbox coordinates are in mm
        bbox *should* contain a proper { 'clip': {'llx': , 'lly': , 'urx': , 'ury': } }
        otherwise a hardcoded flip width is used to make the coordinate system left aligned.
        x_off, y_off are in mm, relative to the clip urx, ury.
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

    # Change by Sven Fabricius:
    # Update the code to use millimeters in all places to prevent mixing with device units.
    # The conversion to SU (SilhouetteUnits) will be done in command create function.
    # Removing all kinds of multiplying, dividing and rounding.

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
      x = path[0][0] + x_off
      y = path[0][1] + y_off
      _bbox_extend(bbox, x, y)
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
        plotcmds.append(self.move_mm_cmd(y, x))

      for j in range(1,len(path)):
        x = path[j][0] + x_off
        y = path[j][1] + y_off
        _bbox_extend(bbox, x, y)
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
          if not self.enable_sw_clipping or (inside and last_inside):
            plotcmds.append(self.draw_mm_cmd(y, x))
          else:
            # // if outside the range just move
            plotcmds.append(self.move_mm_cmd(y, x))
        last_inside = inside
    return plotcmds


  def plot(self, mediawidth=210.0, mediaheight=297.0, margintop=None,
           marginleft=None, pathlist=None, offset=None, bboxonly=False,
           end_paper_offset=0, endposition='below', regmark=False, regsearch=False,
           regwidth=180, reglength=230, regoriginx=15.0, regoriginy=20.0):
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
                (reverse movements are clipped at the home position)
                It reverse over the last home position.
       endposition: Default 'below': The media is moved to a position below the actual cut (so another
                can be started without additional steps, also good for using the cross-cutter).
                'start': The media is returned to the position where the cut started.
       Example: The letter Y (20mm tall, 9mm wide) can be generated with
                pathlist=[[(0,0),(4.5,10),(4.5,20)],[(9,0),(4.5,10)]]
    """
    bbox = { }
    if margintop  is None and 'margin_top_mm'  in self.hardware: margintop  = self.hardware['margin_top_mm']
    if marginleft is None and 'margin_left_mm' in self.hardware: marginleft = self.hardware['margin_left_mm']
    if margintop  is None: margintop = 0
    if marginleft is None: marginleft = 0

    # if 'margin_top_mm' in s.hardware:
    #   print("hardware margin_top_mm = %s" % (s.hardware['margin_top_mm']), file=s.log)
    # if 'margin_left_mm' in s.hardware:
    #   print("hardware margin_left_mm = %s" % (s.hardware['margin_left_mm']), file=s.log)

    if self.leftaligned and 'width_mm' in self.hardware:
      # marginleft += s.hardware['width_mm'] - mediawidth  ## FIXME: does not work.
      mediawidth = self.hardware['width_mm']

    print("mediabox: (%g,%g)-(%g,%g)" % (marginleft,margintop, mediawidth,mediaheight), file=self.log)

    width  = mediawidth
    height = mediaheight
    top    = margintop
    left   = marginleft
    if width < left: width  = left
    if height < top: height = top

    x_off = left
    y_off = top
    if offset is None:
      offset = (0,0)
    else:
      if type(offset) != type([]) and type(offset) != type(()):
        offset = (offset, 0)

    if regmark:
      # after registration logically (0,0) is at regmark position
      # compensate the offset of the regmark to the svg document origin.
      #bb = s.find_bbox(pathlist)
      #print("bb llx=%g ury=%g" % (bb['llx'], bb['ury']), file=s.log)
      #regoriginx = bb['llx']
      #regoriginy = bb['ury']
      print("bb regoriginx=%g regoriginy=%g" % (regoriginx, regoriginy), file=self.log)
      offset = (offset[0] - regoriginx, offset[1] - regoriginy)

      # Limit the cutting area inside cutting marks
      height = reglength
      width = regwidth

      self.send_command("TB50,0") #only with registration (it was TB50,1), landscape mode
      self.send_command("TB99")
      self.send_command("TB52,2")     #type of regmarks: 0='Original,SD', 2='Cameo,Portrait'
      self.send_command("TB51,400")   # length of regmarks
      self.send_command("TB53,10")    # width of regmarks
      self.send_command("TB55,1")

      if regsearch:
        # automatic regmark test
        # add a search range of 10mm
        self.send_command(self.automatic_regmark_test_mm_cmd(reglength, regwidth, regoriginy - 10, regoriginx - 10))
      else:
        # manual regmark
        self.send_command(self.manual_regmark_mm_cmd(reglength, regwidth))

      #while True:
      #  s.write("\1b\05") #request status
      #  resp = s.read(timeout=1000)
      #  if resp != "    1\x03":
      #    break;

      resp = self.read(timeout=40000) ## Allow 20s for reply...
      if resp != "    0\x03":
        raise ValueError("Couldn't find registration marks. %s" % str(resp))

      ## Looks like if the reg marks work it gets 3 messages back (if it fails it times out because it only gets the first message)
      #resp = s.read(timeout=40000) ## Allow 20s for reply...
      #if resp != "    0\x03":
        #raise ValueError("Couldn't find registration marks. (2)(%s)" % str(resp))

      #resp = s.read(timeout=40000) ## Allow 20s for reply...
      #if resp != "    1\x03":
        #raise ValueError("Couldn't find registration marks. (3)")


    # // I think this is the feed command. Sometimes it is 5588 - maybe a maximum?
    #s.write(b"FO%d\x03" % (height-top))


    #FMx, x = 0/1: 1 leads to additional horizontal offset of 5 mm, why? Has other profound
    # impact (will not cut in certain configuration if x=0). Seems dangerous. Not used
    # in communication of Sil Studio with Cameo2.
    #FEx,0 , x = 0 cutting of distinct paths in one go, x = 1 head is lifted at sharp angles
    #\xmin, ymin Zxmax,ymax, designate cutting area

    # needed only for the trackenhancing feature, defines the usable length, rollers three times forward and back.
    # needs a pressure of 19 or more, else nothing will happen
    #p = b"FU%d\x03" % (height)
    #p = b"FU%d,%d\x03" % (height,width) # optional
    #s.write(p)

    if self.product_id() not in [PRODUCT_ID_SILHOUETTE_CAMEO3, PRODUCT_ID_SILHOUETTE_CAMEO4]:
      self.send_command([
        self.upper_left_mm_cmd(0, 0),
        self.lower_right_mm_cmd(height, width),
        "L0",
        "FE0,0",
        "FF0,0,0"])

    bbox['clip'] = {'urx':width, 'ury':top, 'llx':left, 'lly':height}
    bbox['only'] = bboxonly
    cmd_list = self.plot_cmds(pathlist,bbox,offset[0],offset[1])

    if bboxonly == True:
      # move the bounding box
      cmd_list = [
        self.move_mm_cmd(bbox['ury'], bbox['llx']),
        self.draw_mm_cmd(bbox['ury'], bbox['urx']),
        self.draw_mm_cmd(bbox['lly'], bbox['urx']),
        self.draw_mm_cmd(bbox['lly'], bbox['llx']),
        self.draw_mm_cmd(bbox['ury'], bbox['llx'])]

    # potentially long command string needs extra care
    self.safe_send_command(cmd_list)

    # Silhouette Cameo2 does not start new job if not properly parked on left side
    # Attention: This needs the media to not extend beyond the left stop
    if not 'llx' in bbox: bbox['llx'] = 0  # survive empty pathlist
    if not 'lly' in bbox: bbox['lly'] = 0
    if not 'urx' in bbox: bbox['urx'] = 0
    if not 'ury' in bbox: bbox['ury'] = 0
    if endposition == 'start':
      if self.product_id() in [PRODUCT_ID_SILHOUETTE_CAMEO3, PRODUCT_ID_SILHOUETTE_CAMEO4]:
        new_home = [
          "L0",
          self.upper_left_mm_cmd(0, 0),
          self.move_mm_cmd(0, 0),
          "J0",
          "FN0",
          "TB50,0"]
      else:
        new_home = "H"
    else: #includes 'below'
      new_home = [
        self.move_mm_cmd(bbox['lly'] + end_paper_offset, 0),
        "SO0"]
    #new_home += b"FN0\x03TB50,0\x03"
    self.send_command(new_home)

    return {
        'bbox': bbox,
        'unit' : 1,
        'trailer': new_home
      }


  def move_origin(self, feed_mm):
    self.wait_for_ready(verbose=False)
    self.send_command([
      self.move_mm_cmd(feed_mm, 0),
      "SO0",
      "FN0"])
    self.wait_for_ready(verbose=False)

  def load_dumpfile(self,file):
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
