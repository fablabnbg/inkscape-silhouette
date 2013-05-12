inkscape-silhouette
===================

An extension to drive a Silhoutte Cameo from within inkscape.
100% pure python, (except maybe for the libusb backend)

Features: 
* Coordinate system conforms to inkscape SVG (or HPGL)
* Exact Margins. Can start at (0,0).
* Pen mode used to avoid the precut movement of the knive.
  Those movements are visible a) at the left hand side, when 
  starting, b) at each sharp turn.
* Bounding Box. Can optionally plot (or calculate only) 
  the bounding box instead of plotting all strokes.
  This can be used (with low pressure=1 or removed knive) to just 
  check, where the plot would be.
* The standalone script arrow_test.py can be used to test drive
  the SilhoutteCameo class.

Misfeatures:
* Uses lousy path conversion from inkcut. Thought this was a nice tool. Sorry.
* Plotter stops, when we send "too much" data. Is this the 4096 limit?

TODO:
* Rework everything with the eggbotcode path conversion.
