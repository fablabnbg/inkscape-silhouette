#!/usr/bin/env python3
# this script reads inkscape dumpfiles and shows the plotter path
from __future__ import print_function

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

def plotcuts(cuts, buttons=False):
    """
        Show a graphical representation of the cut paths in (the argument) cuts,
        and block until the display window has been closed.

        Displays Cut/Cancel buttons if the buttons argument is true (not implemented yet).

        Returns whether the cut should be canceled; in other words,
        returns false unless buttons was true, the graphics were displayed, and
        the Cancel button was pushed, in which case returns true.
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
    for xy in cuts:
        plt.plot(*zip(*xy), color="tab:blue")
        plt.arrow(xy[-2][0], xy[-2][1], xy[-1][0]-xy[-2][0], xy[-1][1]-xy[-2][1],
                  color="lightblue", length_includes_head=True,
                  head_width=min(3,scale/50))
    plt.axis([plt.axis()[0], plt.axis()[1], plt.axis()[3], plt.axis()[2]])
    plt.gca().set_aspect('equal')
    class Response:
        canceled = False
        def pushedcut(self, event):
            plt.close('all')
        def pushedcancel(self, event):
            self.canceled = True
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
                if 'com.github.jnweiger.inskscape-silhouette.logfile' in line:
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

