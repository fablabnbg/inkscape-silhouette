#! /usr/bin/python
#
# This test cut differs from the test cut in Silhouette Studio:
# as our triangle is not a simple triangle, but a more complex
# Arrow head. The outer square is an ordinary 1cm x 1cm square.
#

from __future__ import print_function

import sys
sys.path.append('/usr/share/inkscape/extensions')
sys.path.append('/home/jw/src/github/fablabnbg/inkscape-silhouette')
from silhouette.Graphtec import SilhouetteCameo

__version__ = '0.1'
__author__ = 'Juergen Weigert <juewei@fabmail.org>'

k=0.2   # knive-center offset, (0.1 is not enough)

test_sq_tr = \
[
  [(4+k, 5+k), (2, 3), (2, 1), (3, 1), (9, 5), (3, 9), (2, 9), (2, 7), (4+k, 5-k)],
  [(0, 0), (0, 10), (10, 10), (10, 0), (0, 0-k)]
]


def write_progress(done, total, msg):
    perc = 100.*done/total
    print("%d%% %s\r" % (perc, msg))

dev = SilhouetteCameo(progress_cb=write_progress, no_device=False)
state = dev.status()    # hint at loading paper, if not ready.
print("status=%s" % (state))
print("device version: '%s'" % dev.get_version())

dev.setup(media=132, pen=False, pressure=1, speed=10)
dev.plot(pathlist=test_sq_tr, offset=(30, 30))
