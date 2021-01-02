# inkscape-silhouette

[![Build Status](https://travis-ci.com/fablabnbg/inkscape-silhouette.svg?branch=master)](https://travis-ci.com/fablabnbg/inkscape-silhouette)

An extension to drive a Silhoutte Cameo and similar plotter devices from within inkscape.
100% pure python, ontop of the libusb backend.

Here is the wiki with photos and a video: https://github.com/fablabnbg/inkscape-silhouette/wiki

## Suported Devices

This extension should work with the following devices:

* Silhouette Portrait
* Silhouette Portrait 2 (working confirmed)
* Silhouette Cameo
* Silhouette Cameo 2
* Silhouette Cameo 3
* Silhouette Cameo 4
* Silhouette Curio (partial success confirmed in #36)
* Craft Robo CC200-20
* Craft Robo CC300-20
* Silhouette SD 1
* Silhouette SD 2

## Installation

### Ubuntu 16.04

* `apt install python-usb`
* https://github.com/fablabnbg/inkscape-silhouette/releases
  Scroll down to Downloads and click on the *.deb file.

### Ubuntu 14.04

* `apt install python-pip python-setuptools`
* `sudo pip install pyusb`
* https://github.com/fablabnbg/inkscape-silhouette/releases
  Scroll down to Downloads and click on the *.deb file.

### Other Debian based Linux

* Download https://github.com/fablabnbg/inkscape-silhouette/archive/master.zip
* Copy the folder `silhouette` and the two files `sendto_silhouette.inx` and
`sendto_silhouette.py` to `~/.config/inkscape/extensions/` or (if you have permissions) `/usr/share/inkscape/extensions/`

* `sudo apt-get install python-usb`
* restart inkscape, check the menu entry "Extensions -> Export -> Send to Silhouette"


### openSUSE

* `~/.config/inkscape/extensions/` or
* `/usr/share/inkscape/extensions/`
* and run `sudo zypper in python-usb`

### Arch Linux

```shell
sudo pacman -S inkscape python2 python2-lxml python2-pyusb
git clone https://github.com/fablabnbg/inkscape-silhouette.git
cd inkscape-silhouette
sudo python2 setup.py build && sudo python2 setup.py install
sudo cp sendto_silhouette.* /usr/share/inkscape/extensions/
sudo cp -R silhouette /usr/share/inkscape/extensions/
```

### Mac OS X

* Install prerequisites:
  * install homebrew http://brew.sh/
  * `brew install libusb`
* Install the extension:
  * `sudo ./install_osx.py`

### Windows

#### Requirements

* Download http://zadig.akeo.ie/downloads/zadig-2.3.exe
* Go to menu options `List all devices`
* Look for USB Printing Support in the dropdown list
* Use manufacturer ID: 10B4D Graftek America`
* Select driver `libusb0 (v1.2.6.0)`
* Click install driver
* If you don't have python installed, then install the latest stable version.
* Download and unpack http://sourceforge.net/projects/pyusb/
* cd ..\pyusb-1.0.0b1; python.exe setup.py install
* An error message `ImportError: No module named usb.core` means you are close, but `pyusb` was not correctly installed. Please check, if there are multiple python installations in your system, e.g. one that came with inkscape.
* Find the path to the `python.exe` in the inkscape directory, e.g. on a Windows 7 (64 bits) it may be `C:\Program Files (x86)\Inkscape\python\python.exe`
* Change directory to the `pyusb` one and run it again.

#### Silhouette inkscape extension itself

* Download and install `7zip` from https://www.7-zip.org/download.html
* Download https://github.com/fablabnbg/inkscape-silhouette/archive/master.zip
* Navigate to your `Downloads` folder and double-click on `inkscape-silhouette-master.zip`
* Click open the `inkscape-silhouette-master` folder.
* Select the following three items (with Ctrl-Click): `silhouette`, `sendto_silhouette.inx`, and `sendto_silhouette.py`
* Extract to `My Computer`: `C:\Program Files\Inkscape\share\extensions` or `C:\Program Files (x86)\Inkscape\share\extensions` if first does not exists.
* Restart inkscape

## Usage

1. Open your document with inkscape.
2. Ensure the unit of document width and height is mm or inch, but not px. (File - Document settings - Page - Custom - Unit mm) Otherwise you may observe differences in dimensions at inkscape 0.91/0.92, because default dpi has changed from 90 to 96.
3. Convert all objects and texts to paths (Path - Convert object to path)
4. Select the parts you want to plot.
5. Open Extension (Extensions - Export - Send to Silhouette)
6. Set your desired plot parameters:
  * **X-Offset, Y-Offset**  An addtitional offset of your drawing from the top left corner. Default is 0/0
  * **Tool Cut/Pen**        Cut mode drews small circles for orientation of the blade, Pen mode draws exactly as given.
  * **Media**               Select a predfined media or set to custom settings.
  * **Speed**               Custom speed of the movements
  * **Pressure**            Custom Pressure on the blade. One unit is said to be 7g force.
7. Press Apply button to start cut.

## Templates
* Templates showing the cutting mat on a background layer can be found in `examples/mat_templates`
* Copy those files into the `templates` subdirectory below inkscapes configuration directory
* To identify the correct path open inkscape's preferences and selecting `System`. There you find the path as `User templates`
* Those templates can then be selected within the dialog available through `File` &rarr; `New from Template...`
* Once you have created a new document from those templates you can import other `*.svg`-files and place the contained objects for cutting

## Troubleshooting

```python
>>> import usb.core
>>> usb.core.find()
<usb.core.Device object at 0xb720fb8c>
>>>
```

If this reports `no usb.core.Device` to you, please help troubleshoot.

```python
python
>>> import usb.core
>>> usb.version_info[0]
```

This fails on win32/64 with 'module has no attribute 'version info' which then causes Graphtec.py to error even though usb.core is installed.

## Using of registration marks

The plotter will search the registration marks at the given positions.
If it founds the marks, they will serve as accurate reference and define the origin.
Therefore it is necessary to set the correct offset values of the mark.
As a result the cut will go precisely along the graphics.


To plot with registration marks do the following:

1. Open the document which fit to your setup, e.g. `examples/registration-marks-cameo-silhouette-a4-maxi.svg` for Silhouette Cameo using A4 paper format.
2. Insert your cutting paths and graphics on the apropriate layers.
3. Printout the whole document including registration marks. You probably want to hide the cutting layer.
4. Select your cutting paths in the document, but exclude regmarks and graphics.
5. On the **Regmarks** tab:
  * Check **Document has registration marks**
  * Check **Search for registration marks**
6. Set all following parameters according to the registration file used:
  * **X mark distance** (e.g. *190*)
  * **Y mark distance** (e.g. *277*)
  * **Position of regmark from document left** (e.g. *10*)
  * **Position of regmark from document top** (e.g. *10*)
7. Start cut.

On some devices have an offset between the search optics and the cutting knife.
For enhanced precision, you may have to set an offset on **X-Offset** and/or **Y-Offset** on the **Silhouette** tab to compensate.

## Features

* Path sorting for monotonic cut. We limit backwards movement to only a few
  millimeters, and make the knive pull only towards sharp corners
  so that most designs can be done without a cutting mat!
* Coordinate system conforms to inkscape SVG.
* Exact Margins. Can start at (0,0).
* Pen mode used to avoid the precut movement of the knive.
  Those movements are visible a) at the left hand side, when
  starting, b) at each sharp turn.
* Bounding Box. Can optionally plot (or calculate only)
  the bounding box instead of plotting all strokes.
  This can be used (with low pressure=1 or removed knive) to just
  check, where the plot would be.
* The standalone script `arrow_test.py` can be used to test drive
  the `SilhoutteCameo` class.
* Robust communication with the device. Small writes and timeouts are
  handled gracefully. Timeouts will occur, when we travel far with low speed.
* Multipass: Can repeat each stroke multiple times to enhance plot or
  cut quality. This can also be used to attempt a cut without cutting mat, by
  applying very little pressure.
* reverse toggle options, to cut the opposite direction. This might also be
  helpful with mat-free cutting via multipass.
* honors hidden layers.

## Misfeatures of InkCut that we do not 'feature'

* object transforms are missing most of the time.
* Stars, polygons, and boxes are plotted not closed, the final stroke
  is missing. (Must be me, no?)
* always plots all layers, even if hidden.

## TODO

* Implement the triangle in a square test cut.

* test MatFree cutting strategy with the WC-Wunderbach-Wimpern font, which is especially
  well suited as a test-case.

* improve MatFree cutting by finding a better scan sort algorithm.
  Wide shadow casting towards negative y?

* Implement paper-zip as a seperate inkscape extension.

## References

* http://wiki.inkscape.org/wiki/index.php/Extensions
* http://wiki.inkscape.org/wiki/index.php/INX_Parameters
* http://wiki.inkscape.org/wiki/index.php/ExtensionsSystem
