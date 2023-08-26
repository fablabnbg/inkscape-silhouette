#!/usr/bin/env python3
# this script reads inkscape dumpfiles and shows the plotter path

import sys
try:
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button
except:
    plt = None
from pathlib import Path


# From https://stackoverflow.com/questions/24852345/hsv-to-rgb-color-conversion
def hsv_to_rgb(h, s, v):
    if s == 0.0: return (v, v, v)
    i = int(h*6.)
    f = (h*6.)-i; p,q,t = v*(1.-s), v*(1.-s*f), v*(1.-s*(1.-f)); i%=6
    if i == 0: return (v, t, p)
    if i == 1: return (q, v, p)
    if i == 2: return (p, v, t)
    if i == 3: return (p, q, v)
    if i == 4: return (t, p, v)
    if i == 5: return (v, p, q)

def show_plotcuts(cuts, buttons=False, extraText=None):
    """
        Show a graphical representation of the cut paths in (the argument) cuts,
        and block until the display window has been closed.

        buttons: display Cut/Cancel buttons

        Returns > 0 on failure
        return value:
          1: cut canceled
          2: matplotlib missing
          3: cut path empty
    """
    if plt is None:
        print("Install matplotlib for python to allow graphical display of cuts",
              file=sys.stderr)
        return 2
    if cuts == []:
        print("Empty cut path", file=sys.stderr)
        return 3
    xy = sum(cuts, [])
    least = min(min(p[0],p[1]) for p in xy)
    greatest = max(max(p[0],p[1]) for p in xy)
    scale = greatest - least
    plt.figure("Sendto Silhouette - Preview")
    plt.plot(*zip(*sum(cuts, [])), color="lightsteelblue")
    plt.plot(xy[0][0],xy[0][1],'go')
    plt.plot(xy[-1][0],xy[-1][1],'ro')
    ncuts = len(cuts)
    maxhue = 0.33
    for i, xy in enumerate(cuts):
        plt.plot(*zip(*xy), color=hsv_to_rgb(maxhue*(1.0-i/ncuts),0.9,0.7))
        plt.arrow(xy[-2][0], xy[-2][1], xy[-1][0]-xy[-2][0], xy[-1][1]-xy[-2][1],
                  color="lightblue", length_includes_head=True,
                  head_width=min(3,scale/50))
    plt.axis([plt.axis()[0], plt.axis()[1], plt.axis()[3], plt.axis()[2]])
    plt.gca().set_aspect('equal')
    class Response:
        returnvalue = 1 if buttons == True else 0
        def pushedcut(self, event):
            self.returnvalue = 0
            plt.close('all')
        def pushedcancel(self, event):
            plt.close('all')
    response = Response()
    if buttons:
        bcut = Button(plt.axes([0.7,0.9,0.1,0.075]), 'Cut')
        bcancel = Button(plt.axes([0.81,0.9,0.1,0.075]), 'Cancel')
        bcut.on_clicked(response.pushedcut)
        bcancel.on_clicked(response.pushedcancel)
        bcut.connect_event('key_press_event', lambda event: response.pushedcut(event) if(event.key=='enter') else None)
        bcancel.connect_event('key_press_event', lambda event: response.pushedcancel(event) if(event.key=='escape') else None)
    if extraText:
        plt.text(-1.3, 0.5, str(extraText), fontsize = 8, horizontalalignment='right')

    plt.show()

    return response.returnvalue

if __name__ == "__main__":
    # The below is not correct under Windows; please help to correct.
    # I am not sure if it is correct under MacOS.
    maybeconfig = Path.home() / '.config' / 'inkscape' / 'preferences.xml'

    olddefault = '/tmp/silhouette.dump'
    filename = ''
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    elif maybeconfig.is_file():
        with open(maybeconfig, 'rt') as config:
            for line in config:
                if 'com.github.fablabnbg.inkscape-silhouette.sendto_silhouette.logfile' in line:
                    maybefilename = line.split('"')[1]
                    if Path(maybefilename).is_file():
                        filename = maybefilename
                    break
    if not filename and Path(olddefault).is_file():
        filename = olddefault
    if not filename:
        sys.exit("Cannot find file with cut paths to display.\nUsage:\n  read_dump.py FILENAME_OF_LOG_OR_DUMP")

    print("Reading cut paths from:", filename)
    cutpaths = ''
    triggered = False
    with open(filename, 'rt') as file:
        for line in file:
            if triggered and line[0] != '#':
                cutpaths = line
                break
            if '# driver version' in line:
                triggered = True

    if not cutpaths:
        sys.exit("Cannot find any cut paths in " + filename + ".\n  Make sure it is an inkscape_silhouette dump or log file with log_paths on.")

    retval = show_plotcuts(eval(cutpaths))
    sys.exit(retval)
