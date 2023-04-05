# a simple makefile to pull a tar ball.

PREFIX?=/usr
DISTNAME=inkscape-silhouette
EXCL=--exclude \*.orig --exclude \*.pyc
ALL=README.md *.png *.sh *.rules *.py *.inx examples misc silhouette locale
VERS=$$(python3 ./sendto_silhouette.py --version)

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
LOCALE=$(DESTDIR)$(PREFIX)/share/locale
UDEV=$(DESTDIR)/lib/udev
INKSCAPE_TEMPLATES=$(DESTDIR)$(PREFIX)/share/inkscape/templates

# User-specifc inkscape extensions folder for local install
DESTLOCAL=$(HOME)/.config/inkscape/extensions

.PHONY: dist install install-local tar_dist_classic tar_dist clean generate_pot update_po mo
dist: mo
	cd distribute; sh ./distribute.sh

#install is used by dist.
install: mo
	mkdir -p $(DEST)
	@# CAUTION: cp -a does not work under fakeroot. Use cp -r instead.
	cp -r silhouette $(DEST)
	install -m 755 *silhouette*.py $(DEST)
	install -m 644 *.inx $(DEST)
	cp -r locale $(LOCALE)
	mkdir -p $(UDEV)/rules.d
	install -m 644 -T silhouette-udev.rules $(UDEV)/rules.d/40-silhouette-udev.rules
	install -m 644 silhouette-icon.png $(UDEV)
	install -m 644 silhouette-udev-notify.sh $(UDEV)
	mkdir -p $(INKSCAPE_TEMPLATES)
	install -m 644 templates/*.svg $(INKSCAPE_TEMPLATES)

install-local: mo
	mkdir -p $(DESTLOCAL)
	@# CAUTION: cp -a does not work under fakeroot. Use cp -r instead.
	cp -r silhouette $(DESTLOCAL)
	install -m 755 *silhouette*.py $(DESTLOCAL)
	install -m 644 *.inx $(DESTLOCAL)
	cp -r locale $(DESTLOCAL)

tar_dist_classic: clean mo
	name=$(DISTNAME)-$(VERS); echo "$$name"; echo; \
	tar jcvf $$name.tar.bz2 $(EXCL) --transform="s,^,$$name/," $(ALL)
	grep about_version ./sendto_silhouette.inx 
	@echo version should be $(VERS)

tar_dist: mo
	python3 setup.py sdist --format=bztar
	mv dist/*.tar* .
	rm -rf dist

clean:
	rm -f *.orig */*.orig
	rm -rf distribute/$(DISTNAME)
	rm -rf distribute/deb/files
	rm -rf locale

generate_pot:
	mkdir -p po/its
	curl -s -o po/its/inx.its https://gitlab.com/inkscape/inkscape/-/raw/master/po/its/inx.its
	xgettext --its po/its/inx.its --no-wrap -o po/inkscape-silhouette.pot *.inx
	xgettext --no-wrap -j -o po/inkscape-silhouette.pot *silhouette*.py

update_po:
	$(foreach po, $(wildcard po/*.po), \
		msgmerge -q --update --no-wrap $(po) po/inkscape-silhouette.pot; )

mo:
	mkdir -p locale
	$(foreach po, $(wildcard po/*.po), \
		mkdir -p locale/$(basename $(notdir $(po)))/LC_MESSAGES; \
		msgfmt -c -o locale/$(basename $(notdir $(po)))/LC_MESSAGES/inkscape-silhouette.mo $(po); )
