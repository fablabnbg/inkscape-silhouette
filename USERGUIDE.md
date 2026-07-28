# User Guide

This contains typical usage examples and workflow for users using this plugin.

---

## Prepping new design files


### Adding Print and Cut Layers

You are recommended to add a layer named `Print` and `Cut`.
The `Print` layer in addition to `Regmarks` will be ignored by `Send to Silhouette` extention.


### Add registration mark

<img src="./assets/screenshot_of_the_regmarked_document.png" alt="screenshot of the regmarked document" height=200px>

The plotter will search the registration marks at the given positions.
If it locates the marks, they will serve as accurate reference and define the origin.
Therefore it is necessary to set the correct offset values of the mark.
As a result the cut will go precisely along the graphics.

1. Extention > Render > Silhouette Regmarks
1. For a Cameo 5 Alpha, select **4 corner (four L-marks, e.g. Cameo 5 Alpha)** as the registration mark style
1. Check regmark from document left and top is set to desired value
1. Set mark to mark distance or clear it to zero if autocalculating from document size
1. Press Apply

This will create a new layer called `Regmarks` with the newly generated registration mark.

On the bottom will also be a string shown below that would remind you what settings this was generated with.
- `mark distance from document: Left=10.0mm, Top=10.0mm; mark to mark distance: X=190.0mm, Y=277.0mm;`

Note: You have the option of using the provided template at `examples/registration-marks-cameo-silhouette-a4-maxi.svg` for Silhouette Cameo using A4 paper format. Cameo 5 Alpha users can use the ready-made A4 template at `templates/silhouette-cameo-5-alpha-registration-marks-a4.svg` without running the regmark generator.


---

## Plot

<img src="./assets/screenshot_of_send_to_silhouette.png" alt="screenshot of Send to Silhouette" height=200px>

1. Open your document with inkscape.
  - Note: documents in px are plotted at 96dpi
2. Convert text objects to paths (Path - Convert object to path)
3. Select the parts you want to plot.
4. Open the extension. If you want to use the same cut settings for all of the paths in your file, use "Extensions -> Export -> Send to Silhouette." If you want use different cut settings based on the colors of different items in your file, use "Extensions -> Export -> Silhouette Multi Action."
5. In the case of Multi Action, there is a first screen that is primarily for debugging. Typically you can just leave all of the boxes on this unchecked and click "Apply."
6. Set your desired plot parameters. There are numerous aspects you can control with the dialog, here are just the core highlights:
  - **X-Offset, Y-Offset**  An additional offset of your drawing from the top left corner. Default is 0/0
  - **Tool Cut/Pen**        Cut mode drews small circles for orientation of the blade, Pen mode draws exactly as given.
  - **Media**               Select a predfined media or set to custom settings.
  - **Speed**               Custom speed of the movements
  - **Pressure**            Custom Pressure on the blade. One unit is said to be 7g force.
  - Note: In Multi Action, you can select the color you want settings to apply to and then set all the same parameters, but with potentially different settings for each color. You can also change the order in which the colors are cut, and uncheck the box in the "Perform Action?" column to ignore a color altogether.
7. To start the cut, in "Send to Silhouette, click the "Apply" button; in "Silhouette Multi" click the "Execute" button.


### Plot with registration marks steps

<img src="./assets/screenshot_of_registration_mark_settings_page.png" alt="screenshot of registration mark settings page" height=200px>

1. Open the document which fit to your setup (e.g. With rendered registration mark as illustrated above)
2. Insert your cutting paths and graphics on the apropriate layers.
3. Printout the whole document including registration marks. You probably want to hide the cutting layer.
4. Select your cutting paths in the document, but exclude regmarks and graphics.
  - The extention is smart enough to ignore any layers that has the word `Print` or `Regmarks` in it.
5. On the **Regmarks** tab:
  - Check **Document has registration marks**
  - Check **Search for registration marks**
  - On a Cameo 5 Alpha, also check **Use 4 registration marks**
6. Set all following parameters according to the registration file used:
  - **X mark distance** (e.g. *190*)
  - **Y mark distance** (e.g. *277*)
  - **Position of regmark from document left** (e.g. *10*)
  - **Position of regmark from document top** (e.g. *10*)
  - Note: values are read from regmarks layer if 0 is entered
7. Set desired plot parameters as usual. Already explained in previous section.
8. Start cut.

On some devices have an offset between the search optics and the cutting knife.
For enhanced precision, you may have to set an offset on **X-Offset** and/or **Y-Offset** on the **Silhouette** tab to compensate.

---

## Connecting over Bluetooth

Bluetooth-capable cutters (Cameo 3 and newer, Portrait 2 and newer, Curio 2, and similar) can be driven wirelessly instead of over USB.

**Before you start:** pair the cutter with your operating system's own Bluetooth settings first, exactly as you would any other Bluetooth device. The extension does not do the pairing for you; it only connects to a cutter your computer has already paired. Make sure the cutter is powered on and in range.

**Steps:**

1. Open **Extensions &rarr; Export &rarr; Send to Silhouette** and switch to the **Bluetooth** tab.
2. Find your cutter's address: tick **Scan for Bluetooth devices (list, then stop)** and click **Apply**. A dialog lists each paired Silhouette cutter with its address, name, and detected model, then stops without cutting. For example:
   ```
   Found 1 Bluetooth Silhouette cutter(s):
       00:1B:41:33:44:55   CAMEO 5 ALPHA-000000   [Silhouette_Cameo5_Alpha]

   Copy the address of the cutter you want into the 'Bluetooth MAC address' field.
   ```
3. Copy the address of the cutter you want into the **Bluetooth MAC address** field, and untick the scan box.
4. Set your plot parameters as usual and click **Apply** to cut over Bluetooth.

**Notes:**

- Leave the **Bluetooth MAC address** field empty to use USB (the default).
- You must enter the address explicitly. There is intentionally no "connect to whatever is nearby" option, so a stranger's cutter that comes into range — or the wrong one, if you own several — can never be selected by accident.
- The cutter model is detected automatically from its firmware. If it is not recognised, set it with **Override cutter model** on the **Log and Dump** tab.
- **Bluetooth Classic vs. BLE (important):** some (most?) cutters advertise themselves *twice* — once as a **Bluetooth Classic** device and once as a **Bluetooth Low Energy (BLE)** device, often with the same or a nearly identical name. This extension communicates over Bluetooth Classic (the RFCOMM serial profile), so you must pair the **Classic** entry. If you pair only the BLE entry, the cutter will not show up in the scan and a connection will fail. The scan deliberately lists only the Classic, RFCOMM-connectable address, so if two entries appear in your OS Bluetooth settings, pair the one that lets the cutter appear in the scan.
- The scan lists devices your operating system has already paired. If your cutter is missing, pair it in your OS Bluetooth settings (as a Classic device — see above), confirm it is on and in range, and scan again. On Linux the scan uses `bluetoothctl` (BlueZ); installing PyBluez (`pip install pybluez`) additionally enables a live inquiry.
- **macOS is not currently supported.** Python's Bluetooth RFCOMM sockets are only available on Linux and Windows, so the Bluetooth features described here do not work on macOS. USB still works normally on macOS. Adding macOS Bluetooth support — for example via a `/dev/cu.*` serial port or Apple's IOBluetooth framework — would be a very welcome contribution; see [CONTRIBUTING](./CONTRIBUTING.md).

**From the command line** the same is available without the dialog:

```sh
# list paired Bluetooth cutters and their addresses, then stop
sendto_silhouette.py --bluetooth_scan=True yourfile.svg

# cut over Bluetooth using an explicit address
sendto_silhouette.py --bluetooth_addr=00:1B:41:33:44:55 yourfile.svg
```

---

## Design Tips

### Getting an outline of a vector object

1. Path > Break Apart
1. Path > Union
1. Depening on your sticker cutting requirement:
 - Path > Inset
 - Path > Outset
 - Path > Dynamic Offset


### Getting an outline of a bitmap object

1. Path > Trace Bitmap
  1. Use brightness cutoff detection mode. 
  1. Select threshold to get as much detail of the object in the image.
  1. Press Apply
1. Select all the vector outlines that was detected and generated
1. Path > Break Apart
1. Path > Union
1. Depening on your sticker cutting requirement:
 - Path > Inset
 - Path > Outset
 - Path > Dynamic Offset

 
