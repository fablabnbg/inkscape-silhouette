#!/bin/env python

import unittest
import subprocess
import sys
from pathlib import Path
import os
import difflib


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
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--help"], stderr=subprocess.STDOUT)
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
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--version"], stderr=subprocess.STDOUT)
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


    def test_04dry_run(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dry_run=True", "--preview=False", "--log_paths=True", "--logfile=silhouette.log", "examples/testcut_square_triangle.svg"], stderr=subprocess.STDOUT)
            print(result.decode())
            filehandle = open("silhouette.log",'r')
            log = filehandle.read()
            filehandle.close()
            self.assertIn('driver version', log)
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False


    def test_05dry_run(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dry_run=True", "--preview=False", "--log_paths=True", "--logfile=silhouette.log", "examples/testcut_square_triangle_o.svg"], stderr=subprocess.STDOUT)
            print(result.decode())
            filehandle = open("silhouette.log",'r')
            log = filehandle.read()
            filehandle.close()
            self.assertIn('driver version', log)
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False


    def test_06dry_run(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dry_run=True", "--preview=False", "--log_paths=True", "--logfile=silhouette.log", "examples/sharp_turns.svg"], stderr=subprocess.STDOUT)
            print(result.decode())
            filehandle = open("silhouette.log",'r')
            log = filehandle.read()
            filehandle.close()
            self.assertIn('driver version', log)
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False


    def test_07dry_run(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dashes=True", "--preview=False", "--dry_run=True", "--log_paths=True", "--logfile=silhouette.log", "examples/dashline.svg"], stderr=subprocess.STDOUT)
            print(result.decode())
            filehandle = open("silhouette.log",'r')
            log = filehandle.read()
            filehandle.close()
            self.assertIn('driver version', log)
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False

    def test_08cmd_file(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dry_run=True", "--preview=False", "--cmdfile=testcut_square_triangle_o.cmd", "--force_hardware=Silhouette SD 1", "examples/testcut_square_triangle_o.svg"], stderr=subprocess.STDOUT)
            print(result.decode())
            filehandle = open("examples/testcut_square_triangle_o.cmd",'r')
            cmdref = filehandle.read()
            filehandle.close()
            filehandle = open("testcut_square_triangle_o.cmd",'r')
            cmd = filehandle.read()
            filehandle.close()
            self.assertEqual(cmdref, cmd)
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False

    def test_09multi_nogui(self):
        try:
            commands = subprocess.run([sys.executable, "silhouette_multi.py", "--block=true", "-d=true", "-g=false", "-p=examples/multi.cPickle", "examples/multi_color.svg"], check=True, capture_output=True).stderr.decode().replace("\r","")
            commandref = Path("./examples/multi.commands").read_text()
            if (commandref != commands):
                diffs = difflib.context_diff(
                    commandref.split(), commands.split())
                sys.stdout.writelines(diffs)
            self.assertEqual(commandref, commands)
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False
