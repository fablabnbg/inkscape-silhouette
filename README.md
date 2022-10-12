# inkscape-silhouette

[![Run Python tests](https://github.com/fablabnbg/inkscape-silhouette/actions/workflows/run-tests.yml/badge.svg)](https://github.com/fablabnbg/inkscape-silhouette/actions/workflows/run-tests.yml)

An extension to drive a Silhoutte Cameo and similar plotter devices from within inkscape.
100% pure python, ontop of the libusb backend.

Here is the wiki with photos and a video: https://github.com/fablabnbg/inkscape-silhouette/wiki

## Supported Devices

This extension should work with the following devices:

* Silhouette Portrait
* Silhouette Portrait 2 (working confirmed)
* Silhouette Portrait 3
* Silhouette Cameo
* Silhouette Cameo 2
* Silhouette Cameo 3
* Silhouette Cameo 4
* Silhouette Cameo 4 Pro
* Silhouette Curio (partial success confirmed in #36)
* Craft Robo CC200-20
* Craft Robo CC300-20
* Silhouette SD 1
* Silhouette SD 2

## Installation

### Ubuntu 20.10 or newer (features Inkscape 1.0+ natively)

WARNING: SNAP packages may cause issues.

Install Inkscape
* `sudo apt install inkscape`

Install requirements
* `sudo apt install python3-usb`

Install inkscape-silhouette
* https://github.com/fablabnbg/inkscape-silhouette/releases
  Scroll down to Downloads and click on the *.deb file.

### Ubuntu 18.04 or 20.04

WARNING: SNAP packages may cause issues.

Add Inkscape 1.0+ repo
* `sudo add-apt-repository ppa:inkscape.dev/stable`
* `sudo apt-get update`

Install Inkscape
* `sudo apt install inkscape`

Install requirements
* `sudo apt install python3-usb`

Install inkscape-silhouette
* https://github.com/fablabnbg/inkscape-silhouette/releases
  Scroll down to Downloads and click on the *.deb file.

### Other Debian based Linux

* Download https://github.com/fablabnbg/inkscape-silhouette/archive/main.zip
* Unzip the archive into a directory (which will be called inkscape-silhouette-main by default)
* In a terminal, change into that directory
* Execute `make install-local` to install just in your user account, or (if you have permissions) `sudo make install`
to install for all users

* `sudo apt-get install python3-usb` if you have permissions, otherwise `python3 -m pip install usb`
* restart inkscape, check that you see new menu entries "Extensions -> Export -> Send to Silhouette"
and " ... -> Silhouette Multi Action".


### openSUSE

* Same as Debian-based, except install the usb package with `sudo zypper in python-usb`

### Arch Linux

```shell
sudo pacman -S inkscape python-lxml python-pyusb
git clone https://github.com/fablabnbg/inkscape-silhouette.git
cd inkscape-silhouette
```

and then either `make install-local` to install just for your user account, or `sudo make install`

### Mac OS X

* Install prerequisites:
  * install homebrew http://brew.sh/
  * `brew install libusb`
  * `brew install python3`
* Install the extension:
  * `./install_osx.py`
  * Add brew python for user extensions. For details on selecting a specific interpreter version see [Inkscape Wiki - Extension Interpreters](https://wiki.inkscape.org/wiki/index.php/Extension_Interpreters#Selecting_a_specific_interpreter_version_.28via_preferences_file.29):
    * `python-interpreter="/usr/local/bin/python3"` on X86 platform
    * `python-interpreter="/opt/homebrew/bin/python3"` on ARM platform (Apple Silicon)

### FreeBSD

Note the recipe here specifies `py39-libusb1`. In case this is out of date, you need to choose
the usb package appropriate to the version of python that runs by default as `python3`.

```
sudo pkg install inkscape py39-libusb1
cd /tmp
wget -c "https://github.com/fablabnbg/inkscape-silhouette/archive/main.zip"
unzip main.zip
cd inkscape-silhouette-main
sudo make install   # OR: make install-local  # latter installs only for this user
```

### Windows

#### Driver 

These steps must be done with Silhouette device plugged in to USB port.

* Download newest Zadig from http://zadig.akeo.ie/
* Go to menu options `List all devices`
* Look for USB Printing Support in the dropdown list
* Ensure USB ID is: `0B4D` (Graftek America)
* Select driver `libusb-win32 (v1.2.6.0)` which will install a `libusb0`-Port for Windows
* Click replace driver

To later undo:

* Run Zadig again
* Go to menu options `List all devices`
* Look for USB Printing Support in the dropdown list
* Ensure USB ID is: `0B4D` (Graftek America)
* Select driver `WinUsb` which will undo the prior change.
* Click replace driver

#### Python adapter

* Inkscape usually comes with a Version of Python; ensure that feature under `Program Files/Python` is ticked upon installation or change/add features accordingly
* Install pip (a package manager for python):
  * Download `get-pip.py` from https://bootstrap.pypa.io/get-pip.py and copy to the `bin` directory, e.g. `C:\Program Files\Inkscape\bin`
  * Open command line and navigate to the same directory, then enter `.\python.exe '.\get-pip.py'`
* Install pyusb:
  * Still in command line enter `.\python.exe -m pip install pyusb`

#### Silhouette inkscape extension itself

* Download https://github.com/fablabnbg/inkscape-silhouette/archive/main.zip
* Open the downloaded file and select the following five items: `silhouette`, `sendto_silhouette.inx`, `sendto_silhouette.py`, `silhouette_multi.inx`, `silhouette_multi.py`
* Extract them to your `share\inkscape\extensions` directory, e.g. `C:\Program Files\Inkscape\share\inkscape\extensions`
* Restart inkscape

## Usage

1. Open your document with inkscape.
2. Ensure the unit of document width and height is mm or inch, but not px. (File - Document settings - Page - Custom - Unit mm) Otherwise you may observe differences in dimensions at inkscape 0.91/0.92, because default dpi has changed from 90 to 96.
3. Convert all objects and texts to paths (Path - Convert object to path)
4. Select the parts you want to plot.
5. Open the extension. If you want to use the same cut settings for all of the paths in your file, use "Extensions -> Export -> Send to Silhouette." If you want use different cut settings based on the colors of different items in your file, use "Extensions -> Export -> Silhouette Multi Action."
6. In the case of Multi Action, there is a first screen that is primarily for debugging. Typically you can just leave all of the boxes on this unchecked and click "Apply."
7. Set your desired plot parameters. There are numerous aspects you can control with the dialog, here are just the core highlights:
  * **X-Offset, Y-Offset**  An additional offset of your drawing from the top left corner. Default is 0/0
  * **Tool Cut/Pen**        Cut mode drews small circles for orientation of the blade, Pen mode draws exactly as given.
  * **Media**               Select a predfined media or set to custom settings.
  * **Speed**               Custom speed of the movements
  * **Pressure**            Custom Pressure on the blade. One unit is said to be 7g force.

  In Multi Action, you can select the color you want settings to apply to and then set all the same parameters, but with potentially different settings for each color. You can also change the order in which the colors are cut, and uncheck the box in the "Perform Action?" column to ignore a color altogether.
8. To start the cut, in "Send to Silhouette, click the "Apply" button; in "Silhouette Multi" click the "Execute" button.

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
