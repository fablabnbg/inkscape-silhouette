#!/bin/env python

import pytest
import unittest
import subprocess
import sys
import platform

@pytest.mark.skipif(platform.system() != "Linux", reason="only runs on Linux")
class TestUmockdev(unittest.TestCase):

    def test_run_cameo3(self):
        try:
            result = subprocess.check_output(["umockdev-run", "--device=test/umockdev/cameo3.umockdev", "--ioctl=/dev/bus/usb/003/017=test/umockdev/cameo3.ioctl", sys.executable, "sendto_silhouette.py"], stderr=subprocess.STDOUT)
            print(result.decode())
            return result
        except subprocess.CalledProcessError as e:
            print(e)
            print(e.output.decode())
            self.assertEqual(e.returncode, 0)
            assert False
