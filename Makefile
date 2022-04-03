# a simple makefile to pull a tar ball.

PREFIX?=/usr
DISTNAME=inkscape-silhouette
EXCL=--exclude \*.orig --exclude \*.pyc
ALL=README.md *.png *.sh *.rules *.py *.inx examples misc silhouette
VERS=$$(python3 ./silhouette/send.py --version)

## echo python3 ./sendto_silhouette.py
# 'module' object has no attribute 'core'
# 'module' object has no attribute 'core'
# done. 0 min 0 sec
#
# debian 8
# --------
# echo > /etc/apt/sources.list.d/backports.list 'deb http://ftp.debian.org debian jessie-backports main'
# apt-get update
# apt-get -t jessie-backports install python3-usb
# vi /etc/group
# lp:x:debian


DEST=$(DESTDIR)$(PREFIX)/share/inkscape/extensions
UDEV=$(DESTDIR)/lib/udev

# User-specifc inkscape extensions folder for local install
DESTLOCAL=$(HOME)/.config/inkscape/extensions

dist:
	cd distribute; sh ./distribute.sh

#install is used by dist.
install:
	mkdir -p $(DEST)
	# CAUTION: cp -a does not work under fakeroot. Use cp -r instead.
	cp -r silhouette $(DEST)
	install -m 755 -t $(DEST) *silhouette*.py
	install -m 644 -t $(DEST) *.inx
	mkdir -p $(UDEV)/rules.d
	install -m 644 -T silhouette-udev.rules $(UDEV)/rules.d/40-silhouette-udev.rules
	install -m 644 -t $(UDEV) silhouette-icon.png
	install -m 644 -t $(UDEV) silhouette-udev-notify.sh

install-local:
	mkdir -p $(DESTLOCAL)
	pip install .
	install -m 644 -t $(DESTLOCAL) *.inx

tar_dist_classic: clean
	name=$(DISTNAME)-$(VERS); echo "$$name"; echo; \
	tar jcvf $$name.tar.bz2 $(EXCL) --transform="s,^,$$name/," $(ALL)
	grep about_version ./sendto_silhouette.inx
	@echo version should be $(VERS)

tar_dist:
	python3 setup.py sdist --format=bztar
	mv dist/*.tar* .
	rm -rf dist

clean:
	rm -f *.orig */*.orig
	rm -rf distribute/$(DISTNAME)
	rm -rf distribute/deb/files
