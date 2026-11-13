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

    def test_08testcut_dry_run(self):
        # The test cut replaces the document: the log must hold the two test
        # paths, triangle first, and nothing from the SVG that was passed in.
        # The overcut option must leave the fixed paths as they are.
        try:
            subprocess.check_output([sys.executable, "sendto_silhouette.py", "--testcut=True", "--dry_run=True", "--preview=False", "--overcut=2", "--regmark=True", "--log_paths=True", "--logfile=silhouette.log", "--cmdfile=testcut.cmd", "--force_hardware=Silhouette_Portrait2", "examples/testcut_square_triangle_o.svg"], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            self.fail(e)
        with open("silhouette.log", 'r') as filehandle:
            log = filehandle.read()
        self.assertIn("Logging 2 cut paths containing 13 points", log)
        self.assertIn("[[(6.0, 4.577), (6.5, 3.711), (9.721, 9.289), (3.279, 9.289), (6.5, 3.711), (7.0, 4.577)], [(2.5, 1.5), (1.5, 1.5), (1.5, 11.5), (11.5, 11.5), (11.5, 1.5), (1.5, 1.5), (1.5, 2.5)]]", log)
        with open("testcut.cmd", 'r') as filehandle:
            cmd = filehandle.read()
        # No registration mark search for a test cut, even when it was asked for.
        self.assertNotIn("TB123,", cmd)
        self.assertNotIn("TB23,", cmd)
        self.assertEqual(cmd.count("\x03M"), 3)  # triangle, square, final move

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
                if hardware == "Silhouette_Portrait2" and sends_depth:
                    # The Portrait 2 needs the tool selected right before the depth.
                    self.assertIn("J1\x03TF1,1\x03", cmds)
                if hardware == "Silhouette_Cameo3":
                    # The Cameo 3 selects the tool earlier in setup, not again here.
                    self.assertNotIn("J1\x03TF1,1", cmds)

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
