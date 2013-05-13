#!/usr/bin/env python 
#
# Inkscape extension for driving a silhouette cameo
# (C) 2013 jw@suse.de. Licensed under CC-BY-SA-3.0 or GPL-2.0 at your choice.
#
# code snippets visited to learn the extension 'effect' interface:
# - http://sourceforge.net/projects/inkcut/
# - http://code.google.com/p/inkscape2tikz/
# - http://wiki.inkscape.org/wiki/index.php/PythonEffectTutorial
# - http://github.com/jnweiger/inkscape-gears-dev
# - http://code.google.com/p/eggbotcode/
# - http://www.bobcookdev.com/inkscape/better_dxf_output.zip
#
# 2013-05-09 jw, V0.1 -- initial draught
# 2013-05-10 jw, V0.2 -- can plot simple cases without transforms.
# 2013-05-11 jw, V0.3 -- still using inkcut/plot.py -- fixed write(), 
#                        improved logging, flipped y-axis.

import sys, os, shutil, time, logging
sys.path.append('/usr/share/inkscape/extensions')

# We will use the inkex module with the predefined Effect base class.
import inkex
from silhouette.InkcutPath import *
from silhouette.Graphtec import SilhouetteCameo

# The simplestyle module provides functions for style parsing.
from simplestyle import *

__version__ = '0.3'
__author__ = 'Juergen Weigert <jnweiger@gmail.com>'


class SendtoSilhouette(inkex.Effect):
  """
  Inkscape Extension to send to a Silhouette Cameo
  """
  def __init__(self):
    # Call the base class constructor.
    inkex.Effect.__init__(self)
    self.cut = []
    self.handle = 255
    self.flatness = 0.1
    try:
      self.tty = open("/dev/tty", 'w')
    except:
      self.tty = open("/dev/null", 'w')
    print >>self.tty, "__init__"
    
    self.OptionParser.add_option('-x', '--x-off', '--x_off', action = 'store',
          type = 'float', dest = 'x_off', default = 0.0, help="X-Offset [mm]")
    self.OptionParser.add_option('-y', '--y-off', '--y_off', action = 'store',
          type = 'float', dest = 'y_off', default = 0.0, help="Y-Offset [mm]")
    self.OptionParser.add_option('-t', '--tool', action = 'store',
          choices=('cut', 'pen'), dest = 'tool', default = None, help="Optimize for pen or knive")
    self.OptionParser.add_option('-m', '--media', '--media-id', '--media_id', 
          action = 'store', dest = 'media', default = '132', 
          choices=('100','101','102','106','111','112','113',
             '120','121','122','123','124','125','126','127','128','129','130',
             '131','132','133','134','135','136','137','138','300'), 
          help="113 = pen, 132 = printer paper, 300 = custom")
    self.OptionParser.add_option('-s', '--speed', 
          action = 'store', dest = 'speed', type = 'int', default = 10, 
          help="[1..10], or 0 for media default")
    self.OptionParser.add_option('-p', '--pressure', 
          action = 'store', dest = 'pressure', type = 'int', default = 10, 
          help="[1..33], or 0 for media default")
    self.OptionParser.add_option('-b', '--bbox', '--bbox-only', '--bbox_only', 
          action = 'store', dest = 'bboxonly', type = 'inkbool', default = False, 
          help='draft the objects bounding box instead of the objects')
    self.OptionParser.add_option('-w', '--wait', '--wait-done', '--wait_done', 
          action = 'store', dest = 'wait_done', type = 'inkbool', default = False, 
          help='After sending wait til device reports ready')


  def cut_line(self,layer,csp):
    self.cut.append([(csp[0][0],csp[0][1]),(csp[1][0],csp[1][1])])

  def cut_point(self,layer,x,y):
    # cutting a point is pretty pointless, no? better_dxf_output.py has code for this...
    pass

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
    print >>self.tty, "effect"
    nodes = self.selected.keys()
    # If no nodes are selected, then cut the whole document. 
    if len(nodes) == 0: 
      nodes = self.doc_ids.keys()

    def getSelectedById(IDlist): # returns lxml elements that have an id in IDlist in the svg
      ele=[]
      svg = self.document.getroot()
      for e in svg.iterfind('.//*[@id]'):
        if IDlist is None or e.get('id') in IDlist:
          ele.append(e)
      return ele

    lxml_nodes = []
    for node in getSelectedById(nodes):
      tag = node.tag[node.tag.rfind("}")+1:]
      if tag in ('grid','namedview','defs','metadata'): continue
      lxml_nodes.append(node)
    print >>self.tty, "Nodecount: %d\n" % len(lxml_nodes)

    # import xml.etree.ElementTree as ET
    # ET.tostring(lxml_nodes[0])

    ## This is from better_dxf_output.py: quite lousy implementation.
    ## it silently ignores transformation on path objects and cannot really handle rects.
    self.plot = Plot({
      'scale':25.4/units['in'], 'margin':0, 'startPosition':(0,0), 
      'smoothness':0.2*units['mm']})
    self.plot.loadGraphic(lxml_nodes)
    cut = self.plot.toCutList()
    # print >>self.tty, self.plot.graphic, cut
    ## FIXME: recursivelyTraverseSvg() from egbot.py looks much more mature.

    try:
      dev = SilhouetteCameo(log=self.tty)
    except Exception as e:
      print >>self.tty, e
      print >>sys.stderr, e
      return

    cut = dev.flip_cut(cut)
    state = dev.status()    # hint at loading paper, if not ready.
    print >>self.tty, "status=%s" % (state)
    print >>self.tty, "device version: '%s'" % dev.get_version()

    if self.options.pressure == 0:     self.options.pressure = None
    if self.options.speed == 0:        self.options.speed = None
    pen=None
    if self.options.tool == 'pen': pen=True
    if self.options.tool == 'cut': pen=False
    if self.options.bboxonly == False: self.options.bboxonly=None
    dev.setup(media=self.options.media, pen=pen, 
      pressure=self.options.pressure, speed=self.options.speed)
    bbox = dev.page(cut=cut, mediaheight=990, 
      offset=(self.options.x_off,self.options.y_off),
      bboxonly=self.options.bboxonly)
    print >>self.tty, " 100%%, bbox: (%.1f,%.1f)-(%.1f,%.1f)mm, %d points" % (
      bbox['bbox']['llx']*bbox['unit'],
      bbox['bbox']['ury']*bbox['unit'],
      bbox['bbox']['urx']*bbox['unit'],
      bbox['bbox']['lly']*bbox['unit'],
      bbox['total'])
    state = dev.status()
    while self.options.wait_done and state == 'moving':
      self.tty.write('.')
      self.tty.flush()
      state = dev.status()
      time.sleep(1)
    print >>self.tty, "\nstatus=%s" % (state)

    # pump the output to the device
    success = True
    if not success:
      logging.error('Failed to put output to device')
    output = ""
    return output

e = SendtoSilhouette()
start = time.time()
e.affect()
ss = int(time.time()-start+.5)
mm = int(ss/60)
ss -= mm*60
print >>e.tty, " done. %d min %d sec" % (mm,ss)
