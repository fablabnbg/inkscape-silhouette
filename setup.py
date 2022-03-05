import io
from os import path

from distutils.core import setup

# read the contents of your README file
this_directory = path.abspath(path.dirname(__file__))
with io.open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(name='inkscape-silhouette',
      # keep this in sync with the version in sendto_silhouette.inx and with
      # the version in silhouette/__init__.py
      version="1.25",
      description='Inkscape extension for driving a silhouette cameo',
      author="Juergen Weigert",
      author_mail="juergen@fabmail.org",
      url='https://github.com/fablabnbg/inkscape-silhouette',
      packages=['silhouette'],
      entry_points={"console_scripts": ["sendto_silhouette=silhouette.send:main",
                                        "silhouette_multi=silhouette.multi:main"]},
      license='GPL-2.0',
      classifiers=[
          'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
          'Environment :: Console',
          'Development Status :: 5 - Production/Stable',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          ],
      long_description=long_description,
      long_description_content_type='text/markdown',
      # tests_require=['pytest', 'scipy'],
      # packages=['pyPdf', 'reportlab.pdfgen', 'reportlab.lib.colors',
      #           'pygame.font' ],
      )
