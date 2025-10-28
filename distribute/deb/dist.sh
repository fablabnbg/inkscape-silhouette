#! /bin/bash
# Make a debian/ubuntu distribution

name=$1
vers=$2
url=http://github.com/fablabnbg/$name
# versioned dependencies need \ escapes to survive checkinstall mangling.
# requires="python3-usb\ \(\>=1.0.0\), bash"

## not even ubuntu 16.04 has python-usb 1.0,  we requre any python-usb
## and check at runtime again.
requires="python3-usb, bash"

tmp=../out

[ -d $tmp ] && rm -rf $tmp/*.deb
mkdir -p $tmp
cp *-pak files/
cd files
fakeroot checkinstall --fstrans --reset-uid --type debian \
  --install=no -y --pkgname $name --pkgversion $vers --arch all \
  --pkglicense GPL-2 --pkggroup other --pakdir ../$tmp --pkgsource $url \
  --pkgaltsource "https://fablab-nuernberg.de" \
  --maintainer "'Juergen Weigert (juewei@fabmail.org)'" \
  --requires "$requires" make install \
  -e PREFIX=/usr || { echo "fakeroot checkinstall error "; exit 1; }

