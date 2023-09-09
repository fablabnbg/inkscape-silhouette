# User Guide

This contains typical usage examples and workflow for users using this plugin.

---

## Prepping new design files


### Adding Print and Cut Layers

You are recommended to add a layer named `Print` and `Cut`.
The `Print` layer in addition to `Regmarks` will be ignored by `Send to Silhouette` extention.


### Add registration mark

<img src="./assets/c9c32197-4967-42f9-b8fa-f407d4f12203" alt="screenshot of the regmarked document" height=200px>

The plotter will search the registration marks at the given positions.
If it locates the marks, they will serve as accurate reference and define the origin.
Therefore it is necessary to set the correct offset values of the mark.
As a result the cut will go precisely along the graphics.

1. Extention > Render > Silhouette Regmarks
1. Check regmark from document left and top is set to desired value
1. Set mark to mark distance or clear it to zero if autocalculating from document size
1. Press Apply

This will create a new layer called `Regmarks` with the newly generated registration mark.

On the bottom will also be a string shown below that would remind you what settings this was generated with.
- `mark distance from document: Left=10.0mm, Top=10.0mm; mark to mark distance: X=190.0mm, Y=277.0mm;`

Note: You have the option of using the provided template at `examples/registration-marks-cameo-silhouette-a4-maxi.svg` for Silhouette Cameo using A4 paper format.


---

## Plot

<img src="./assets/859b134f-8765-4768-89c0-a5a9fe569243" alt="screenshot of Send to Silhouette" height=200px>

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


### Plot with registration marks steps

<img src="./assets/672d24e4-7455-4d29-b7b8-dc638fd9305e" alt="screenshot of registration mark settings page" height=200px>

1. Open the document which fit to your setup (e.g. With rendered registration mark as illustrated above)
2. Insert your cutting paths and graphics on the apropriate layers.
3. Printout the whole document including registration marks. You probably want to hide the cutting layer.
4. Select your cutting paths in the document, but exclude regmarks and graphics.
    - The extention is smart enough to ignore any layers that has the word `Print` or `Regmarks` in it.
5. On the **Regmarks** tab:
  * Check **Document has registration marks**
  * Check **Search for registration marks**
6. Set all following parameters according to the registration file used:
  * **X mark distance** (e.g. *190*)
  * **Y mark distance** (e.g. *277*)
  * **Position of regmark from document left** (e.g. *10*)
  * **Position of regmark from document top** (e.g. *10*)
7. Set desired plot parameters as usual. Already explained in previous section.
8. Start cut.

On some devices have an offset between the search optics and the cutting knife.
For enhanced precision, you may have to set an offset on **X-Offset** and/or **Y-Offset** on the **Silhouette** tab to compensate.

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

 
