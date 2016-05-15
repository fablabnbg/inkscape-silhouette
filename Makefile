# a simple makefile to pull a tar ball.

TARNAME=inkscape-silhouette
EXCL=--exclude \*.orig --exclude \*.pyc
ALL=README.md *.png *.sh *.rules *.py *.inx examples misc silhouette
VERS=$$(echo '<xml height="0"/>' | python ./sendto_silhouette.py --version)	

DEST=/usr/share/inkscape/extensions

dist:
	cd distribute; sh ./distribute.sh

#install is used by dist.
install:
	echo this does not work under fakeroot.
	mkdir -p $(DEST)
	cp -a silhouette $(DEST)
	install -m 755 -t $(DEST) *.py
	install -m 644 -t $(DEST) *.inx


tar_dist_classic: clean
	name=$(TARNAME)-$(VERS); echo "$$name"; echo; \
	tar jcvf $$name.tar.bz2 $(EXCL) --transform="s,^,$$name/," $(ALL)
	grep about_version ./sendto_silhouette.inx 
	@echo version should be $(VERS)

tar_dist:
	python setup.py sdist --format=bztar
	mv dist/*.tar* .
	rm -rf dist

clean:
	rm -f *.orig */*.orig
