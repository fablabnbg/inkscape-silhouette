# inkscape-silhouette

[![Run Python tests](https://github.com/fablabnbg/inkscape-silhouette/actions/workflows/run-tests.yml/badge.svg)](https://github.com/fablabnbg/inkscape-silhouette/actions/workflows/run-tests.yml)

An extension to drive a Silhouette Cameo and similar plotter devices from within inkscape.
100% pure python, ontop of the libusb backend.

Here is the wiki with photos and a video: https://github.com/fablabnbg/inkscape-silhouette/wiki

## Supported Devices

This extension should work with the following devices:

* Silhouette Portrait
* Silhouette Portrait 2 (working confirmed)
* Silhouette Portrait 3
* Silhouette Portrait 4 (working confirmed)
* Silhouette Cameo
* Silhouette Cameo 2
* Silhouette Cameo 3
* Silhouette Cameo 4
* Silhouette Cameo 4 Plus
* Silhouette Cameo 4 Pro
* Silhouette Cameo 5
* Silhouette Cameo 5 Plus
* Silhouette Curio (partial success confirmed in #36)
* Craft Robo CC200-20
* Craft Robo CC300-20
* Silhouette SD 1
* Silhouette SD 2

---

## Installation

### Ubuntu

<details>
<summary>Click to get steps</summary>

WARNING: SNAP packages may cause issues. We use deb file shown later in this section.

#### Install Inkscape and other requirements

```bash
# Add inkscape dev team's PPA key to APT.
# This project require minimum of inkscape V1.0+
# But we want to always keep to latest inkscape version
sudo add-apt-repository ppa:inkscape.dev/stable

# Install Inkscape
sudo apt-get update
sudo apt install inkscape

# Install Inkscape with newer version directly from inkscape dev team
# even if newer than what Ubuntu's package management team is willing
# to certify at the moment
sudo apt-get --with-new-pkgs upgrade inkscape

# Install requirements for usb support
sudo apt-get install python3-usb

# Install requirements for Silhouette Multiple Actions
sudo apt install python3-wxgtk4.0

# Install all requirements from python package manager
sudo apt-get install python3-pip
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt
```

#### Install inkscape-silhouette

From here, you should have all the required python packages and inkscape version.
So now we shall install inkscape-silhouette, so scroll down the latest releases and head to the Assets section of releases and click on the *.deb file. You can then use `sudo apt-get install ./*.deb` where `*.deb` is the name of your newly downloaded file.

* https://github.com/fablabnbg/inkscape-silhouette/releases

</details>

### Other Debian based Linux

<details>
<summary>Click to get steps</summary>

* Download https://github.com/fablabnbg/inkscape-silhouette/archive/main.zip
* Unzip the archive into a directory (which will be called inkscape-silhouette-main by default)
* In a terminal, change into that directory
* Execute `make install-local` to install just in your user account, or (if you have permissions) `sudo make install`
to install for all users

* `sudo apt-get install python3-usb` if you have permissions, otherwise `python3 -m pip install usb`
* restart inkscape, check that you see new menu entries "Extensions -> Export -> Send to Silhouette"
and " ... -> Silhouette Multi Action".

</details>

### openSUSE

* Same as Debian-based, except install the usb package with `sudo zypper in python3-usb`

### Arch Linux

<details>
<summary>Click to get steps</summary>

```shell
sudo pacman -S inkscape python-lxml python-pyusb python-tinycss2 python-matplotlib
git clone https://github.com/fablabnbg/inkscape-silhouette.git
cd inkscape-silhouette
```

and then either `make install-local` to install just for your user account, or `sudo make install`

</details>

### Fedora Linux

<details>
<summary>Click to get steps</summary>

Install the necessary packages:
`sudo dnf install python3-pyusb python3-matplotlib make gettext`

Clone the inkscape-silhoutte repo and make/install the extension:
```shell
git clone https://github.com/fablabnbg/inkscape-silhouette.git
cd inkscape-silhouette
sudo make install
```
Add a new rule file to the udev device manager:
`sudo nano /etc/udev/rules.d/99-graphtec-silhouette.rules`

And add the following:
`SUBSYSTEM=="usb", ATTR{idVendor}=="0b4d", ATTR{idProduct}=="1137", MODE="666"`

Finally, load the file with:
`sudo udevadm trigger`
 
</details>

### Mac OS X

<details>
<summary>Click to get steps</summary>

* Install prerequisites:
  * Install homebrew http://brew.sh/
  * `brew install libusb`
  * Install Inkscape
      * Either with homebrew: `brew install inkscape`
      * Or manually from their [website](https://inkscape.org/)
* Install the extension:
  * `./install_osx.sh`
  * Add the suggested python interpreter for user extensions in `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/preferences.xml` on `<group id="extensions" python-interpreter="/..." />`. For details on selecting a specific interpreter version see [Inkscape Wiki - Extension Interpreters](https://inkscape.gitlab.io/extensions/documentation/authors/interpreters.html):
    * e.g. `python-interpreter="/Users/username/.local/share/venvs/inkscape/bin/python3"`

</details>

### FreeBSD

<details>
<summary>Click to get steps</summary>

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

</details>


### Windows

<details>
<summary>Click to get steps</summary>

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

</details>

---

## Usage

### GUI

Refer to the [userguide instructions](./USERGUIDE.md) for further details.

### CLI

Run `sendto_silhouette.py --help` for information on CLI usage.

---

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

* Test MatFree cutting strategy with the WC-Wunderbach-Wimpern font, which is especially
  well suited as a test-case.

* Improve MatFree cutting by finding a better scan sort algorithm.
  Wide shadow casting towards negative y?

* Implement paper-zip as a separate inkscape extension.

## References

* https://inkscape.gitlab.io/extensions/documentation/authors/
* https://inkscape.gitlab.io/extensions/documentation/authors/inx-widgets.html
* https://wiki.inkscape.org/wiki/ExtensionsSystem
