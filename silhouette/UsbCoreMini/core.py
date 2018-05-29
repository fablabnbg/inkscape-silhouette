# coding=utf-8
# (c) 2014 jw@suse.de
#
# UsbCoreMini.py - A minimal usb.core implementation, to make poor 
# ubuntu users happy, who still need to use a 5 (or more) years old python-usb 0.4.2 
#

# This implements usb.core.find() and usb.core.USBError
# compatible with 1.x versions of python-usb when loaded as
# import UsbCoreMini as usb
#
from __future__ import print_function

import sys

try:
    import usb
except:
    print("The python usb module could not be found. Try", file=sys.stderr)
    print("\t sudo zypper in python-usb \t\t# if you run SUSE", file=sys.stderr)
    print("\t sudo apt-get python-usb   \t\t# if you run Ubuntu", file=sys.stderr)
    sys.exit(0)


def find(find_all=False, idVendor=None, idProduct=None):
    all = []
    for bus in usb.busses():
        for dev in bus.devices:
            d = UsbDeviceMini(dev, bus)
            # print "seen idVendor=%04x idProduct=%04x" % (d.idVendor, d.idProduct)
            if idVendor is None and idProduct is None:
                all.append(d)
            elif idVendor is None:
                if idProduct == d.idProduct:
                    all.append(d)
            elif idProduct is None:
                if idVendor == d.idVendor:
                    all.append(d)
            else:
                if idVendor == d.idVendor and idProduct == d.idProduct:
                    all.append(d)
    if find_all:
        return all
    if not len(all):
        return None
    return all[0]


class USBError(IOError):
    def __init__(self, strerror, error_code=None, errno=None):
        IOError.__init__(self, errno, strerror)
        self.backend_error_code = error_code
        self.errno = errno


class UsbDeviceMini(object):
    def __init__(self, olddev, bus):
        self.bus = bus.location
        self.idVendor = olddev.idVendor
        self.idProduct = olddev.idProduct
        self.address = olddev.devnum
        self.olddev = olddev
        self.handle = None

    def write(self, data, *args, **kwargs):
        if self.handle is None:
            print("opening")
            # here we get a segv. --> forget compatibility with the 0.4.x code.
            self.handle = self.olddev.open()
            print("opened")
        return self.handle.write(data)

    def is_kernel_driver_active(self, dummy):
        return False

    def reset(self):
        return False

    def set_configuration(self):
        return False

    def set_interface_altsetting(self):
        return False
