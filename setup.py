#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# sudo zypper in python-setuptools
# http://docs.python.org/2/distutils/setupscript.html#installing-additional-files
#
import sys
from os import path
import re

from distutils.core import setup
from setuptools.command.test import test as TestCommand
import silhouette  # for author, version

# read the contents of your README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

m = re.match(r'(.*)\s+<(.*)>', silhouette.__author__)

# print('.',['Makefile']+glob.glob('silhouette-*')),('misc',glob.glob('misc/*'))


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(name='inkscape-silhouette',
      version=silhouette.__version__,
      description='Inkscape extension for driving a silhouette cameo',
      author=m.groups()[0],
      author_email=m.groups()[1],
      url='https://github.com/jnweiger/inkscape-silhouette',
      entry_points={"console_scripts": ["sendto_silhouette=silhouette.send:main",
                                        "silhouette_multi=silhouette.multi:main"]},
      packages=['silhouette'],
      license='GPL-2.0',
      classifiers=[
          'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
          'Environment :: Console',
          'Development Status :: 5 - Production/Stable',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          ],
      cmdclass={'test': PyTest},
      long_description=long_description,
      long_description_content_type='text/markdown',
      # tests_require=['pytest', 'scipy'],
      # packages=['pyPdf', 'reportlab.pdfgen', 'reportlab.lib.colors',
      #           'pygame.font' ],
      )
