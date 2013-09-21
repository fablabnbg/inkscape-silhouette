inkscape-silhouette
===================

An extension to drive a Silhoutte Cameo from within inkscape.
100% pure python, (except maybe for the libusb backend)

Here is the wiki with photos and a video: https://github.com/jnweiger/inkscape-silhouette/wiki

Installation
------------

Copy the the folder silhouette and the two files sendto_silhouette.inx and 
sendto_silhouette.py to your computer:

Linux:
*  ~/.config/inkscape/extensions/ or
*  /usr/share/inkscape/extensions/

Windows (untested): 
*  C:\Program Files\Inkscape\share\extensions\ .

Mac OS X (untested)
*  easy_install lxml
*  easy_install pyusb
*  /Applications/Inkscape.app/Contents/Resources/extensions/ . 
*  Read the eror message 'no backend available'
*  work some unknown magic, so that devices are found.

Troubleshooting
---------------

 python
 >>> import usb.core
 >>> usb.core.find()
 <usb.core.Device object at 0xb720fb8c>
 >>> 

If this reports no usb.core.Device to you, please help troubleshoot.


Features
--------

* Path sorting for monotonic cut. We limit backwards movement to only a few 
  millimeters, and make the knive pull only towards sharp edges so that most
  designs can be done without a cutting mat!
* Coordinate system conforms to inkscape SVG.
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
  handled gracefully. Timeouts will occur, when we travel far with low speed.
* Multipass: Can repeat each stroke multiple times to enhance plot or 
  cut quality. This can also be used to attempt a cut without cutting mat, by
  applying very little pressure.
* reverse toggle options, to cut the opposite direction. This might also be 
  helpful with mat-free cutting via multipass.
* honors hidden layers.

Misfeatures of InkCut that we do not 'feature'
----------------------------------------------

* object transforms are missing most of the time.
* Stars, polygons, and boxes are plotted not closed, the final stroke 
  is missing. (Must be me, no?)
* always plots all layers, even if hidden.

TODO
----

* Find out, if inkscape could keep the current selection, after running an
  extension.  It is not nice, that the selection gets deselected, and I have
  to close and reopen the extension dialogue to re-activate a selection.
  Idea: Maybe add an option to auto-remember old selections, if it is still
  the same document and there is no new selection.

* test MatFree cutting strategy with the WC-Wunderbach-Wimpern font, which is especially 
  well suited as a test-case.
* improve MatFree cutting by finding a better scan sort algorithm.
  Wide shadow casting towards negative y?

* Implement paper-zip as a seperate inkscape extension. 

REFERENCES
----------

There is very little documentation about extensions. If so, its often historic.
* http://wiki.inkscape.org/wiki/index.php/Extensions
* http://wiki.inkscape.org/wiki/index.php/INX_Parameters
* http://wiki.inkscape.org/wiki/index.php/ExtensionsSystem

