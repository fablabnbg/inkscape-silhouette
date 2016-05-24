#! /bin/bash
# Make a debian/ubuntu distribution

name=$1
vers=$2
url=http://github.com/fablabnbg/$name
# versioned dependencies need \ escapes to survive checkinstall mangling.
requires="python-usb\ \(\>=1.0.0\), bash"

tmp=../out

[ -d $tmp ] && rm -rf $tmp/*.deb
mkdir -p $tmp
cp *-pak files/
cd files
fakeroot checkinstall --fstrans --reset-uid --type debian \
  --install=no -y --pkgname $name --pkgversion $vers --arch all \
  --pkglicense LGPL --pkggroup other --pakdir ../$tmp --pkgsource $url \
  --pkgaltsource "http://fablab-nuernberg.de" \
  --maintainer "'Juergen Weigert (juewei@fabmail.org)'" \
  --requires "$requires" make install \
  -e PREFIX=/usr || { echo "fakeroot checkinstall error "; exit 1; }

