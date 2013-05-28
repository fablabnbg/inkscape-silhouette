# a simple makefile to pull a tar ball.

TARNAME=inkscape-silhouette
EXCL=--exclude \*.orig --exclude \*.pyc
ALL=README.md *.png *.sh *.rules *.py *.inx examples misc silhouette
VERS=$$(echo '<xml height="0"/>' | python ./sendto_silhouette.py --version)	

clean:
	rm -f *.orig */*.orig

dist: clean
	name=$(TARNAME)-$(VERS); echo "$$name"; echo; \
	tar jcvf $$name.tar.bz2 $(EXCL) --transform="s,^,$$name/," $(ALL)
