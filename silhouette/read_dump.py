#!/usr/bin/env python3
# this script reads inkscape dumpfiles and shows the plotter path

import sys
try:
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button
except:
    plt = None
try:
    from pathlib import Path
except:
    from pathlib2 import Path # backport for Python2


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

def plotcuts(cuts, buttons=False):
    """
        Show a graphical representation of the cut paths in (the argument) cuts,
        and block until the display window has been closed.

        Displays Cut/Cancel buttons if the buttons argument is true.

        Returns True if the cut should be canceled,
        which means that buttons were shown and the user did not confirm the cut.
    """
    if plt is None:
        print("Install matplotlib for python to allow graphical display of cuts",
              file=sys.stderr)
        return False
    if cuts == []:
        print("Empty path", file=sys.stderr)
        return False
    xy = sum(cuts, [])
    least = min(min(p[0],p[1]) for p in xy)
    greatest = max(max(p[0],p[1]) for p in xy)
    scale = greatest - least
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
        canceled = buttons
        def pushedcut(self, event):
            self.canceled = False
            plt.close('all')
        def pushedcancel(self, event):
            plt.close('all')
    response = Response()
    if buttons:
        bcut = Button(plt.axes([0.7,0.9,0.1,0.075]), 'Cut')
        bcancel = Button(plt.axes([0.81,0.9,0.1,0.075]), 'Cancel')
        bcut.on_clicked(response.pushedcut)
        bcancel.on_clicked(response.pushedcancel)
    plt.show()

    return response.canceled

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

    plotcuts(eval(cutpaths))

