#!/usr/bin/env python3

import unittest
import subprocess
import sys
from pathlib import Path
import difflib


class TestMulti(unittest.TestCase):

    def test_01multi_nogui(self):
        try:
            # The -Wignore flag to Python is for the sake of an
            # inkscape-internal use of a deprecated Python construct. When
            # we are no longer testing on the offending version of Inkscape
            # (1.2 as released), it can be removed.
            commands = subprocess.run([sys.executable, "-Wignore::DeprecationWarning", "silhouette_multi.py", "--block=true", "-d=true", "-g=false", "-p=test/data/multi.cPickle", "test/data/multi_color.svg"], check=True, capture_output=True).stderr.decode().replace("\r","")
            commandref = Path("./test/data/multi.commands").read_text()
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
