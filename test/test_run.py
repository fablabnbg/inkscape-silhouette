#!/bin/env python

import unittest
import subprocess
import sys
import os


class TestRun(unittest.TestCase):

    def test_00import_inkex(self):
        try:
            result = subprocess.check_output([sys.executable, "-c", "import sendto_silhouette;import inkex;print(inkex)"], stderr=subprocess.STDOUT)
            #print(result.decode())
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False


    def test_01help(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py" ,"--help"], stderr=subprocess.STDOUT)
            #print(result.decode())
            self.assertIn('sage: sendto_silhouette.py', str(result))
            self.assertIn('--help', str(result))
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False


    def test_02version(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py" ,"--version", "examples/testcut_square_triangle.svg"], stderr=subprocess.STDOUT)
            #print(result.decode())
            self.assertIn('1.', str(result))
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False


    def test_03run(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py"], stderr=subprocess.STDOUT)
            print(result.decode())
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False


    def test_04dummy_cut(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py" ,"--dummy=True", "examples/testcut_square_triangle.svg"], stderr=subprocess.STDOUT)
            print(result.decode())
            self.assertIn('Dump written to', str(result))
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False


    def test_05dummy_cut(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py" ,"--dummy=True", "examples/testcut_square_triangle_o.svg"], stderr=subprocess.STDOUT)
            print(result.decode())
            self.assertIn('Dump written to', str(result))
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False


    def test_06dummy_cut(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py" ,"--dummy=True", "examples/sharp_turns.svg"], stderr=subprocess.STDOUT)
            print(result.decode())
            self.assertIn('Dump written to', str(result))
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False
