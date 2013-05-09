# (c) 2013 jw@suse.de
# driver for a Graphtec Silhouette Cameo plotter.
# modelled after https://github.com/nosliwneb/robocut.git 
#
import usb.core
import time
    
# taken from robocut/Plotter.h:53 ff

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
    r = s.dev.write(endpoint, string, interface=0) 
    if r != len(string):
      raise ValueError('write %d bytes failed: r=%d' % (len(string), r))
      
  def read(s, size=64, timeout=5000):
    endpoint = 0x82
    data = s.dev.read(endpoint, size, timeout=timeout, interface=0) 
    if data is None:
      raise ValueError('read failed: none')
    return data 

  def status(s):
    # Status request.
    s.write("\x1b\x05")
    resp = s.read(timeout=5000).tostring()
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
    
