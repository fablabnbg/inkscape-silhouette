#!/usr/bin/env python3

import unittest
import subprocess
import sys
from pathlib import Path
import difflib
from unittest import mock

import silhouette_multi


class TestMacOSLibraryPath(unittest.TestCase):

    def test_removes_only_inkscape_library_directory(self):
        inkscape_lib = "/Applications/Inkscape.app/Contents/Resources/lib"
        other_lib = "/opt/example/lib"

        cleaned = silhouette_multi._without_inkscape_library_path(
            f"{other_lib}:{inkscape_lib}"
        )

        self.assertEqual(cleaned, other_lib)

    def test_restarts_with_clean_environment_on_macos(self):
        inkscape_lib = "/Applications/Inkscape.app/Contents/Resources/lib"
        environment = {"DYLD_LIBRARY_PATH": inkscape_lib}

        with (
            mock.patch.object(silhouette_multi.sys, "platform", "darwin"),
            mock.patch.object(silhouette_multi.os, "environ", environment),
            mock.patch.object(silhouette_multi.os, "execve") as execve,
        ):
            silhouette_multi._restart_without_inkscape_libraries()

        restarted_environment = execve.call_args.args[2]
        self.assertNotIn("DYLD_LIBRARY_PATH", restarted_environment)
        self.assertEqual(
            restarted_environment[silhouette_multi._DYLD_RESTART_MARKER], "1"
        )


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
