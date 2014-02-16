#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys 

from distutils.core import setup
from setuptools.command.test import test as TestCommand
import sendto_silhouette	# for author(), version()

e = sendto_silhouette.SendtoSilhouette()
m = re.match('(.*)\s+<(.*)>', e.author())

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(name='inkscape-silhouette',
      version = e.version()
      description='Inkscape extension for driving a silhouette cameo'
      author=m.groups()[0]
      author_email=m.groups()[1]
      url='https://github.com/jnweiger/inkscape-silhouette',
      scripts=['sendto_silhouette.py', 'sendto_silhouette.inx'],
      license='GPL-2.0',
      classifiers=[
          'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
          'Environment :: Console',
          'Development Status :: 5 - Production/Stable',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
                  ],
      cmdclass={'test': PyTest},
      long_description="".join(open('README.md').readlines()),
      # tests_require=['pytest', 'scipy'],
      #packages=['pyPdf','reportlab.pdfgen','reportlab.lib.colors','pygame.font' ],
# 
)
