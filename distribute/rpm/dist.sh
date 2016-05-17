# silhouette-udev.rules uses Ubuntu paths.
# patch them up for SUSE.
#
sed -i -e 's@"/lib/udev/@"/usr/lib/udev/@' files/silhouette-udev.rules

# override UDEV to match SUSE:
make install UDEV=/usr/lib/udev

