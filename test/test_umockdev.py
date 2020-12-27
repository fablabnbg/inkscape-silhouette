#!/bin/env python

import unittest
import subprocess
import sys
import platform


class TestUmockdev(unittest.TestCase):

    def test_run_cameo3(self):
        if platform.system() == "Linux":
            try:
                result = subprocess.check_output(["umockdev-run", "--device=test/umockdev/cameo3.umockdev", "--ioctl=/dev/bus/usb/003/017=test/umockdev/cameo3.ioctl", sys.executable, "sendto_silhouette.py"], stderr=subprocess.STDOUT)
                print(result.decode())
                return result
            except subprocess.CalledProcessError as e:
                print(e)
                print(e.output.decode())
                self.assertEqual(r.returncode, 0)
                assert False



