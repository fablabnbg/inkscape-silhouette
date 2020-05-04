#!/bin/bash
#umockdev-record /dev/bus/usb/003/017
umockdev-record --ioctl=/dev/bus/usb/003/017=/tmp/test.io python sendto_silhouette.py
