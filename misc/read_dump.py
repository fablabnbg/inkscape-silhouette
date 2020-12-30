#!/usr/bin/python
# this script reads inkscape dumpfiles and shows the plotter path
import matplotlib.pyplot as plt
f = open('/tmp/silhouette.dump')
lines = f.readlines()
f.close()
dump = eval(lines[-1])
xy = sum(dump, [])
plt.plot(*zip(*xy))
plt.axis([plt.axis()[0],plt.axis()[1],plt.axis()[3],plt.axis()[2]])
plt.show()
