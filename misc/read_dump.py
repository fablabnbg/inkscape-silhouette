#!/usr/bin/python
# this script reads inkscape dumpfiles and shows the plotter path
import sys
import matplotlib.pyplot as plt
filename = sys.argv[1] if len(sys.argv)==2 else "/tmp/silhouette.dump"
f = open(filename)
lines = f.readlines()
f.close()
dump = eval(lines[-1])
xy = sum(dump, [])
plt.plot(*zip(*sum(dump, [])), color="lightsteelblue")
for xy in dump:
    plt.plot(*zip(*xy), color="tab:blue")
plt.axis([plt.axis()[0], plt.axis()[1], plt.axis()[3], plt.axis()[2]])
plt.show()
