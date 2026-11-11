#!/usr/bin/env python3

import unittest
import subprocess
import sys
import os

from tempfile import gettempdir

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
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dry_run=True", "--preview=False", "--log_paths=True", "--logfile=silhouette.log", "--output=silhouette.svg", "examples/sharp_turns.svg"], stderr=subprocess.STDOUT)
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
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dashes=True", "--preview=False", "--dry_run=True", "--log_paths=True", "--logfile=silhouette.log", "--output=silhouette.svg", "examples/dashline.svg"], stderr=subprocess.STDOUT)
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
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dry_run=True", "--preview=False", "--cmdfile=testcut_square_triangle_o.cmd", "--force_hardware=Silhouette_SD_1", "examples/testcut_square_triangle_o.svg"], stderr=subprocess.STDOUT)
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

    def test_08regmark_dry_run(self):
        # Each registration search mode sends its own command; a dry run must
        # get past the search and write the cut paths after it.
        modes = {
            "TB123,": ["--force_hardware=Silhouette_Portrait2", "--regsearch=True"],
            "TB124,": ["--force_hardware=Silhouette_Cameo5_Alpha", "--regsearch=True", "--quadregmarks=True"],
            "TB23,": ["--force_hardware=Silhouette_Portrait2", "--regsearch=False"],
        }
        for cmd, options in modes.items():
            with self.subTest(cmd=cmd):
                try:
                    subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dry_run=True", "--preview=False", "--cmdfile=regmark.cmd", "--regmark=True", "--regoriginx=10", "--regoriginy=10", "--regwidth=190", "--reglength=277"] + options + ["test/data/regmark_cut.svg"], stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError as e:
                    print(e.output.decode())
                    self.fail(e)
                with open("regmark.cmd", 'r') as filehandle:
                    cmds = filehandle.read()
                self.assertIn(cmd, cmds)
                self.assertIn("\x03D", cmds[cmds.index(cmd):])

    def test_08autoblade_depth_dry_run(self):
        # The AutoBlade depth (TF) is sent to the Portrait 2 as well as the
        # Cameo 3 on, and only when the AutoBlade tool is selected.
        cases = [
            ("Silhouette_Portrait2", "autoblade", True),
            ("Silhouette_Portrait2", "cut", False),
            ("Silhouette_Cameo3", "autoblade", True),
        ]
        for hardware, tool, sends_depth in cases:
            with self.subTest(hardware=hardware, tool=tool):
                try:
                    subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dry_run=True", "--preview=False", "--cmdfile=autoblade.cmd", "--force_hardware=" + hardware, "--tool=" + tool, "--depth=1", "examples/testcut_square_triangle_o.svg"], stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError as e:
                    print(e.output.decode())
                    self.fail(e)
                with open("autoblade.cmd", 'r') as filehandle:
                    cmds = filehandle.read()
                if sends_depth:
                    self.assertIn("TF1,1", cmds)
                else:
                    self.assertNotIn("TF1,1", cmds)

    def test_09dry_run(self):
        try:
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dry_run=True", "--preview=False", "--strategy=matfree", "--logfile=silhouette.log", "examples/testcut_matfree.svg"], stderr=subprocess.STDOUT)
            print(result.decode())
            filehandle = open("silhouette.log",'r')
            log = filehandle.read()
            filehandle.close()
            self.assertIn('matfree', log)
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False

    def test_10dry_run(self):
        try:
            # Test that default temporary log filepath is writable
            result = subprocess.check_output([sys.executable, "sendto_silhouette.py", "--dry_run=True", "--preview=False", "--strategy=matfree", "examples/testcut_matfree.svg"], stderr=subprocess.STDOUT)
            print(result.decode())
            filehandle = open(os.path.join(gettempdir(), "silhouette.log"),'r')
            log = filehandle.read()
            filehandle.close()
            self.assertIn('matfree', log)
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            print(e)
            self.assertEqual(e.returncode, 0)
            assert False
