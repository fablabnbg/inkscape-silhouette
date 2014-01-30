inkscape-silhouette
===================

An extension to drive a Silhoutte Cameo from within inkscape.
100% pure python, (except for the libusb backend)

Here is the wiki with photos and a video: https://github.com/jnweiger/inkscape-silhouette/wiki

Installation
------------

Copy the the folder silhouette and the two files sendto_silhouette.inx and 
sendto_silhouette.py to your computer:

openSUSE:
* An automatic build hook updates the rpm package at https://build.opensuse.org/package/show/home:jnweiger/inkscape-silhouette


Linux:
* ~/.config/inkscape/extensions/ or
* /usr/share/inkscape/extensions/
* and run '''sudo zypper in python-usb'''


Windows (untested): 
* Download and install the free test version of **winzip** from http://www.winzip.com
* Download https://github.com/jnweiger/inkscape-silhouette/archive/master.zip
* Navigate to your Downloads folder and double-click on **inkscape-silhouette-master.zip**
* Click open the **inkscape-silhouette-master** folder.
* Select the following three items (with Ctrl-Click): **silhouette**, **sendto_silhouette.inx**, and **sendto_silhouette.py**
* Extract to My Computer **C:\Program Files\Inkscape\share\extensions**
* untested: if you have a Silhouette Studio CD, install the device driver. Then your Silhouette Cameo may show up as a printer device and the extension could now work. If not, installing pywinusb might help.
* The following tips are for a Windows-7 64-bit machine:
 * Download and install http://sourceforge.net/projects/libusb-win32/files/libusb-win32-releases/ 
 * x86\libusb0_x86.dll: x86 32-bit library. Must be renamed to libusb0.dll <br>
   On 64 bit, Installs to Windows\syswow64\libusb0.dll. 
   On 32 bit, Installs to Windows\system32\libusb0.dll. 
 * X86 ONLY ARCHITECTURES:<br> 
   x86\libusb0.sys: x86 32-bit driver.<br>
   Installs to Windows\system32\drivers\libusb0.sys
 * When you get a number of options, chose the printer option.
* If you don't have python installed, then install the latest stable version. 
* Download and unpack http://sourceforge.net/projects/pyusb/ 
* cd ..\pyusb-1.0.0b1; python.exe setup.py install
* Restart inkscape
* An error message 'ImportError: No module named usb.core' means you are close, but pyusb was not correctly installed. Please check, if there are multiple python installations in your system, e.g. one that came with inkscape.


Mac OS X (untested)
*  /Applications/Inkscape.app/Contents/Resources/extensions/ . 
*  easy_install lxml
*  easy_install pyusb
*  Read the eror message 'no backend available'
*  work some unknown magic, so that devices are found.

* Ideas taken from https://github.com/pmonta/gerber2graphtec
**  install XCode and macports
**  port install gerbv
**  port install pstoedit
**  port install libusb
**  Download and install this package: http://pypi.python.org/pypi/libusb1 with the usual "python setup.py install" installation method.
**  https://github.com/pmonta/gerber2graphtec/blob/master/file2graphtec


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

* Implement the triangle in a square test cut.

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

