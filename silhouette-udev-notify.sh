#! /bin/sh
# silhouette-udev-notify.sh -- a helper triggered by silhouette.rules RUN= 
#
# (c) 2013, jw@suse.de - All rights reserved. Distribute under GPL-2.0
# (c) 2016, juewei@fabmail.org - using Ubuntu paths.
#
# Popup a notification and instruct users how to access the device.
#

# udev RUN= fires 3 times when plugging in, but only once we have an ID_SERIAL
# udev PROGRAM= also fires 3 times, but without any uniq parameter. 
#
# Use this script with RUN=only, or you end up with multiple notifications!
#
# TODO: 
# * Prevent systemd, udev-add-printer, udev-configure-printer 
#   from trolling the device too.  # Blacklist somewhere?
# * Find out how we can find and notify a KDE user.
# * Confirm, we always have an $ID_SERIAL once, and exactly once.
# * Check if a user has permission to access the device.
#   Tell him if this is not the case.

# logger "$0 [$$]: Hello Syslog xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

test -z "$ID_SERIAL" && exit 0

title="Silhouette CAMEO ($ACTION)"
text="use via inkscape -> Extensions -> Export"
test "$ACTION" = 'add' || text=
timeout=10000		# Milliseconds
icon=printer
icon=/lib/udev/silhouette-icon.png	# Ubuntu path
test -f "$icon" || icon=/usr/$icon	# SUSE path
test -f "$icon" || icon=printer 	# any other stock values allowed?

## FIXME: how is this triggered for KDE?
pids=$(pgrep 'gnome-panel|xfce4-panel')
# logger "$0 [$$]: pids=$pids"
for pid in $pids; do
 # find DBUS session bus for this session
 CRED=$(egrep -z 'USER|DBUS_SESSION_BUS_ADDRESS' /proc/$pid/environ | tr \\0 ' ') 
 if [ "$CRED" != "" ]; then
   eval export $CRED
   su $USER -c "notify-send -i '$icon' '$title' '$text'"
   logger "$0 [$$]: notify-send via USER=$USER SESS=$DBUS_SESSION_BUS_ADDRESS"
 fi
done

exit 0
