#!/bin/env python

import unittest
import subprocess
import sys
import os


class TestRun(unittest.TestCase):

    def test_import_inkex(self):
        try:
            result = subprocess.check_output([sys.executable, "-c", "import sendto_silhouette;import inkex;print(inkex)"], stderr=subprocess.STDOUT)
            print(result.decode())
            return result
        except subprocess.CalledProcessError as e:
            print(e)
            print(e.output.decode())
            self.assertEqual(r.returncode, 0)
            assert False


    def test_run(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py"], stderr=subprocess.STDOUT)
            print(result.decode())
            return result
        except subprocess.CalledProcessError as e:
            print(e)
            print(e.output.decode())
            self.assertEqual(r.returncode, 0)
            assert False


    def test_help(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py" ,"--help"], stderr=subprocess.STDOUT)
            print(result.decode())
            self.assertIn('Usage: sendto_silhouette.py [options] SVGfile', str(result))
            self.assertIn('--help', str(result))
        except subprocess.CalledProcessError as e:
            print(e)
            print(e.output.decode())
            self.assertEqual(r.returncode, 0)
            assert False


    def test_dummy_cut(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py" ,"--dummy=True", "examples/testcut_square_triangle.svg"], stderr=subprocess.STDOUT)
            print(result.decode())
            self.assertIn('Dump written to', str(result))
        except subprocess.CalledProcessError as e:
            print(e)
            print(e.output.decode())
            self.assertEqual(r.returncode, 0)
            assert False

