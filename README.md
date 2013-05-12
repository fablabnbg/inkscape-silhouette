inkscape-silhouette
===================

An extension to drive a Silhoutte Cameo from within inkscape.
100% pure python, (except maybe for the libusb backend)

Features: 
* Coordinate system now conforms to inkscape SVG via flip_cut()
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
* Robust communication with the device. Small writes and timeouts are
  handled gracefully.

Misfeatures:
* Uses lousy path conversion from inkcut. Thought this was a nice tool. Sorry.

TODO:
* Rework everything with the eggbotcode path conversion.
* Find out, if inkscape could keep the current selection, after running an extension.
  It is not nice, that the selection gets deselected, and I have to close and reopen 
  the extension dialogue to re-activate a selection.
