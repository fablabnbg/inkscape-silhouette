#!/bin/bash
test -e /usr/bin/xpath || sudo apt-get install libxml-xpath-perl
test -e /usr/bin/checkinstall || sudo apt-get install checkinstall
#
VERSION=$( python3 ../sendto_silhouette.py --version )
INX_VERSION=$( xpath -q -e '//*[@name="about_version"]/text()' ../sendto_silhouette.inx | sed -e 's/^version //i' ) # grep Version ../*.inx
echo "Source version is: \"$VERSION\""
echo "INX version is: \"$INX_VERSION\""
test "$VERSION" = "$INX_VERSION" || ( echo "Error: python source and .inx version differ" && exit 1 )



name=inkscape-silhouette
if [ -d $name ]
then
	echo "Removing leftover files"
	rm -rf $name
fi
echo "Copying contents ..."
mkdir $name
cp ../README.md $name/README
cp ../LICENSE* $name/
cp -a ../silhouette $name/
cp ../*silhouette*.py ../*.inx $name/


echo "****************************************************************"
echo "Build Windows Version (Y/n)?"
read answer
if [ "$answer" != "n" ]
then
  mkdir -p out
  zip -r out/$name-winpackage_$VERSION.zip $name --exclude \*.pyc \*__pycache__\*
  zip -j out/$name-winpackage_$VERSION.zip win/*
fi


# add linux-specific content
cp ../*.sh ../*.rules ../*.png ../Makefile $name/


echo "****************************************************************"
echo "Ubuntu Version: For Building you must have checkinstall and dpkg"
echo "Build Ubuntu Version (Y/n)?"
read answer
if [ "$answer" != "n" ]
then
  mkdir -p deb/files
  cp -a $name/* deb/files
  (cd deb && sh ./dist.sh $name $VERSION)
fi


echo "Built packages are in distribute/out :"
ls -la out
echo "Cleaning up..."
rm -rf $name
echo "done."
