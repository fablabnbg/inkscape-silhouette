#!/usr/bin/env python 
#
# Inkscape extension for driving a silhouette cameo
# (C) 2013 jw@suse.de. Licensed under CC-BY-SA-3.0 or GPL-2.0 at your choice.
#
# code snippets visited to learn the extension 'effect' interface:
# - http://code.google.com/p/inkscape2tikz/
# - http://wiki.inkscape.org/wiki/index.php/PythonEffectTutorial
# - http://github.com/jnweiger/inkscape-gears-dev
# - http://code.google.com/p/eggbotcode/
#
# 2013-05-09 jw, V0.1 -- initial draught

import sys, os, shutil
sys.path.append('/usr/share/inkscape/extensions')

# We will use the inkex module with the predefined Effect base class.
import inkex
# The simplestyle module provides functions for style parsing.
from simplestyle import *

__version__ = '0.1'
__author__ = 'Juergen Weigert <jnweiger@gmail.com>'


class SendtoSilhouette(inkex.Effect):
  """
  Inkscape Extension to send to a Silhouette Cameo
  """
  def __init__(self):
    # Call the base class constructor.
    inkex.Effect.__init__(self)
    
    self.OptionParser.add_option('-x', '--x-off', action = 'store',
          type = 'float', dest = 'x_off', default = 0.0, help="X-Offset [mm]")
    self.OptionParser.add_option('-y', '--y-off', action = 'store',
          type = 'float', dest = 'y_off', default = 0.0, help="Y-Offset [mm]")
    self.OptionParser.add_option('-t', '--tool', action = 'store',
          choices=('cut', 'pen'), dest = 'tool', default = 'cut', help="Optimize for pen or knive")
    self.OptionParser.add_option('-m', '--media', '--media-id', action = 'store',
	  choices=(100, 101, 102, 106, 111, 112, 113, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 300), 
          dest = 'media', default = 132, help="113 = pen, 132 = printer paper, 300 = custom")
    self.OptionParser.add_option('-s', '--speed', action = 'store',
	  type = 'int', dest = 'speed', default = 10, help="[1..10], or 0 for media default")
    self.OptionParser.add_option('-p', '--pressure', action = 'store',
	  type = 'int', dest = 'pressure', default = 10, help="[1..33], or 0 for media default")
    self.OptionParser.add_option('-b', '--bbox-only', action = 'store', type = 'inkbool',
	  dest = 'bbox_only', default=False, help='draft the objects bounding box instead of the objects')


    def parse(self, file_or_string=None):
        """Parse document in specified file or on stdin"""
        try:
            if file_or_string:
                try:
                    stream = open(file_or_string, 'r')
                except:
                    stream = StringIO.StringIO(file_or_string)
            else:
                stream = open(self.args[-1], 'r')
        except:
            stream = sys.stdin
        self.document = inkex.etree.parse(stream)
        stream.close()


    def getselected(self):
        """Get selected nodes in document order

        The nodes are stored in the selected dictionary and as a list of
        nodes in selected_sorted.
        """
        self.selected_sorted = []
        self.selected = {}
        if len(self.options.ids) == 0:
            return
            # Iterate over every element in the document
        for node in self.document.getiterator():
            id = node.get('id', '')
            if id in self.options.ids:
                self.selected[id] = node
                self.selected_sorted.append(node)

    def get_node_from_id(self, node_ref):
        if node_ref.startswith('url('):
            node_id = re.findall(r'url\((.*?)\)', node_ref)
            if len(node_id) > 0:
                ref_id = node_id[0]
        else:
            ref_id = node_ref
        if ref_id.startswith('#'):
            ref_id = ref_id[1:]

        ref_node = self.document.xpath('//*[@id="%s"]' % ref_id,
            namespaces=inkex.NSS)
        if len(ref_node) == 1:
            return ref_node[0]
        else:
            return None

    def effect(self):
        s = ""
        nodes = self.selected_sorted
        # If no nodes is selected convert whole document. 
        if len(nodes) == 0:
            nodes = self.document.getroot()
            graphics_state = GraphicsState(nodes)
        else:
            graphics_state = GraphicsState(None)
	return { 'not_impl': True }


    def convert(self, svg_file, **kwargs):
        self.getoptions()
        self.options.__dict__.update(kwargs)
        self.parse(svg_file)
        self.getselected()
        self.getdocids()
        output = self.effect()

	# pump the output to the device
        if not success:
           logging.error('Failed to put output to device')
        output = ""
        return output


if __name__ == '__main__':
  e = SendtoSilhouette()
  e.affect()
