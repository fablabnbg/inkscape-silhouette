#!/bin/bash
echo "Determining Version:"
VERSION=$(python ../sendto_silhouette.py --version)

test -e /usr/bin/xpath || sudo apt-get install libxml-xpath-perl
test -e /usr/bin/checkinstall || sudo apt-get install checkinstall
#
# grep Version ../*.inx
xpath -q -e '//param[@name="about_version"]/text()' ../sendto_silhouette.inx
echo "Version should be: \"$VERSION\""



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
cp ../*.py ../*.inx ../Makefile $name/
cp ../*.sh ../*.rules ../*.png  $name/


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
