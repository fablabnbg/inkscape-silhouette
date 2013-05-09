#! /usr/bin/python
#
# simple demo program to drive the silhouette cameo.
# (C) 2013 jw@suse.de
#
# Requires: python-usb  # from Factory

from Graphtec import SilhouetteCameo

# coordinates in mm, origin int top lefthand corner
arrow1 = [ (1,6), (21,6), (18,1), (31,11), (18,21), (21,16), (1,16), (4,11), (1,6) ]
dev = SilhouetteCameo()
state = dev.initialize()
print state

# 
# if (resp != "0\x03") // 0 = Ready. 1 = Moving. 2 = Nothing loaded. "  " = ??
# {
# if (resp == "1\x03")
#   e = Error("Moving, please try again.");
# else if (resp == "2\x03")
#   e = Error("Empty tray, please load media.");	// Silhouette Cameo
# else
#   e = Error("Invalid response from plotter: " + resp);
# goto error;
# }
# 
# // Home the cutter.
# e = UsbSend(handle, "TT\x03");
# if (!e) goto error;
# 
# // Query version.
# e = UsbSend(handle, "FG\x03");
# if (!e) goto error;
# 
# // Receive the firmware version.
# e = UsbReceive(handle, resp, 10000); // Large timeout because the plotter moves.
# if (!e) goto error;
# 
# 
# e = UsbSend(handle, "FW" + ItoS(media) + "\x03");
# if (!e) goto error;
# 
# e = UsbSend(handle, "!" + ItoS(speed) + "\x03");
# if (!e) goto error;
# 
# e = UsbSend(handle, "FX" + ItoS(pressure) + "\x03");
# if (!e) goto error;
# 
# 
# e = UsbSend(handle, "FW" + ItoS(media) + "\x03");
# if (!e) goto error;
# 
# e = UsbSend(handle, "!" + ItoS(speed) + "\x03");
# if (!e) goto error;
# 
# e = UsbSend(handle, "FX" + ItoS(pressure) + "\x03");
# if (!e) goto error;
# 
