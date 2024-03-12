#!/bin/bash

# VERBOSE=-s
VERBOSE=

umockdev-run --device=cameo3.umockdev --ioctl=/dev/bus/usb/003/017=test_io.io -- python3 -m pytest $VERBOSE test_io.py --hardware 

