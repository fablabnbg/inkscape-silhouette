#!/usr/bin/env python3
"""
Quick connectivity and cut test for Silhouette Cameo 5 Alpha Plus.
Runs a 1cm square at low pressure/speed — safe for testing without media loaded.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from silhouette.Graphtec import SilhouetteCameo

# 1cm square, offset 30mm from origin
test_square = [
    [(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)]
]

def progress(done, total, msg):
    print(f"  {100*done//total}% {msg}", flush=True)

print("Searching for device...")
dev = SilhouetteCameo(progress_cb=progress)
print(f"Device: {dev.hardware.get('name')}")
print(f"Status: {dev.status()}")
print(f"Firmware: {dev.get_version()}")
print(f"Hardware: width={dev.hardware.get('width_mm')}mm, max_pressure={dev.hardware.get('max_pressure', 'default')}")

print("\nRunning test cut (1cm square, pressure=1, speed=5)...")
dev.setup(media=132, pen=False, pressure=1, speed=5)
dev.plot(pathlist=test_square, offset=(30, 30))
print("Done.")
