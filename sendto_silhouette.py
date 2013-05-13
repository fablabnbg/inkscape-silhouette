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
# 2013-05-12 jw, v0.4 -- No unintended multipass when nothing is selected. 
#                        Explicit multipass option added.
#                        Emplying recursivelyTraverseSvg() from eggbotcode
#                        TODO: coordinate system of page is not exact.

import sys, os, shutil, time, logging
sys.path.append('/usr/share/inkscape/extensions')

# We will use the inkex module with the predefined Effect base class.
import inkex
import simpletransform
import simplepath
import cubicsuperpath
import cspsubdiv
import bezmisc

from silhouette.Graphtec import SilhouetteCameo
## from silhouette.InkcutPath import *
## # The simplestyle module provides functions for style parsing.
## from simplestyle import *

__version__ = '0.4'
__author__ = 'Juergen Weigert <jnweiger@gmail.com>'

N_PAGE_WIDTH = 3200
N_PAGE_HEIGHT = 800


def distanceSquared( P1, P2 ):
  '''
  Pythagorean distance formula WITHOUT the square root.  Since
  we just want to know if the distance is less than some fixed
  fudge factor, we can just square the fudge factor once and run
  with it rather than compute square roots over and over.
  '''
  dx = P2[0] - P1[0]
  dy = P2[1] - P1[1]

  return ( dx * dx + dy * dy )

def parseLengthWithUnits( str ):
  '''
  Parse an SVG value which may or may not have units attached
  This version is greatly simplified in that it only allows: no units,
  units of px, and units of %.  Everything else, it returns None for.
  There is a more general routine to consider in scour.py if more
  generality is ever needed.
  '''
  u = 'px'
  s = str.strip()
  if s[-2:] == 'px':
    s = s[:-2]
  elif s[-1:] == '%':
    u = '%'
    s = s[:-1]
  try:
    v = float( s )
  except:
    return None, None
  return v, u

# Lifted with impunity from eggbot.py

def subdivideCubicPath( sp, flat, i=1 ):
  """
  Break up a bezier curve into smaller curves, each of which
  is approximately a straight line within a given tolerance
  (the "smoothness" defined by [flat]).

  This is a modified version of cspsubdiv.cspsubdiv() rewritten
  to avoid recurrence.
  """

  while True:
    while True:
      if i >= len( sp ):
        return

      p0 = sp[i - 1][1]
      p1 = sp[i - 1][2]
      p2 = sp[i][0]
      p3 = sp[i][1]

      b = ( p0, p1, p2, p3 )

      if cspsubdiv.maxdist( b ) > flat:
        break

      i += 1

    one, two = bezmisc.beziersplitatt( b, 0.5 )
    sp[i - 1][2] = one[1]
    sp[i][0] = two[2]
    p = [one[2], one[3], two[1]]
    sp[i:1] = [p]



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

    self.paths = {}
    self.transforms = {}
    # For handling an SVG viewbox attribute, we will need to know the
    # values of the document's <svg> width and height attributes as well
    # as establishing a transform from the viewbox to the display.
    self.docWidth = float( N_PAGE_WIDTH )
    self.docHeight = float( N_PAGE_HEIGHT )
    self.docTransform = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

    try:
      self.tty = open("/dev/tty", 'w')
    except:
      self.tty = open("/dev/null", 'w')
    print >>self.tty, "__init__"
    
    self.OptionParser.add_option('-b', '--bbox', '--bbox-only', '--bbox_only', 
          action = 'store', dest = 'bboxonly', type = 'inkbool', default = False, 
          help='draft the objects bounding box instead of the objects')
    self.OptionParser.add_option('-m', '--media', '--media-id', '--media_id', 
          action = 'store', dest = 'media', default = '132', 
          choices=('100','101','102','106','111','112','113',
             '120','121','122','123','124','125','126','127','128','129','130',
             '131','132','133','134','135','136','137','138','300'), 
          help="113 = pen, 132 = printer paper, 300 = custom")
    self.OptionParser.add_option('-M', '--multipass', 
          action = 'store', dest = 'multipass', type = 'int', default = '1', 
           help="[1..8], cut/draw each path object multiple times.")
    self.OptionParser.add_option('-p', '--pressure', 
          action = 'store', dest = 'pressure', type = 'int', default = 10, 
          help="[1..33], or 0 for media default")
    self.OptionParser.add_option('-s', '--speed', 
          action = 'store', dest = 'speed', type = 'int', default = 10, 
          help="[1..10], or 0 for media default")
    self.OptionParser.add_option('-t', '--tool', action = 'store',
          choices=('cut', 'pen'), dest = 'tool', default = None, help="Optimize for pen or knive")
    self.OptionParser.add_option('-w', '--wait', '--wait-done', '--wait_done', 
          action = 'store', dest = 'wait_done', type = 'inkbool', default = False, 
          help='After sending wait til device reports ready')
    self.OptionParser.add_option('-x', '--x-off', '--x_off', action = 'store',
          type = 'float', dest = 'x_off', default = 0.0, help="X-Offset [mm]")
    self.OptionParser.add_option('-y', '--y-off', '--y_off', action = 'store',
          type = 'float', dest = 'y_off', default = 0.0, help="Y-Offset [mm]")


  def addPathVertices( self, path, node=None, transform=None ):
    '''
    Decompose the path data from an SVG element into individual
    subpaths, each starting with an absolute move-to (x, y)
    coordinate followed by one or more absolute line-to (x, y)
    coordinates.  Each subpath is stored as a list of (x, y)
    coordinates, with the first entry understood to be a
    move-to coordinate and the rest line-to coordinates.  A list
    is then made of all the subpath lists and then stored in the
    self.paths dictionary using the path's lxml.etree node pointer
    as the dictionary key.
    '''
    if ( not path ) or ( len( path ) == 0 ):
      return

    # parsePath() may raise an exception.  This is okay
    sp = simplepath.parsePath( path )
    if ( not sp ) or ( len( sp ) == 0 ):
      return

    # Get a cubic super duper path
    p = cubicsuperpath.CubicSuperPath( sp )
    if ( not p ) or ( len( p ) == 0 ):
      return

    # Apply any transformation
    if transform != None:
      simpletransform.applyTransformToPath( transform, p )

    # Now traverse the simplified path
    subpaths = []
    subpath_vertices = []
    for sp in p:
      # We've started a new subpath
      # See if there is a prior subpath and whether we should keep it
      if len( subpath_vertices ):
        if distanceSquared( subpath_vertices[0], subpath_vertices[-1] ) < 1:
          # Keep the prior subpath: it appears to be a closed path
          subpaths.append( subpath_vertices )
      subpath_vertices = []
      subdivideCubicPath( sp, float( 0.2 ) )
      for csp in sp:
        # Add this vertex to the list of vetices
        subpath_vertices.append( csp[1] )

    # Handle final subpath
    if len( subpath_vertices ):
      if distanceSquared( subpath_vertices[0], subpath_vertices[-1] ) < 1:
        # Path appears to be closed so let's keep it
        subpaths.append( subpath_vertices )

    # Empty path?
    if len( subpaths ) == 0:
      return

    # And add this path to our dictionary of paths
    self.paths[node] = subpaths

    # And save the transform for this element in a dictionary keyed
    # by the element's lxml node pointer
    self.transforms[node] = transform


  ## lifted from eggbot.py, gratefully bowing to the author
  def recursivelyTraverseSvg( self, aNodeList,
      matCurrent=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
      parent_visibility='visible' ):
    '''
    Recursively walk the SVG document, building polygon vertex lists
    for each graphical element we support.

    Rendered SVG elements:
            <circle>, <ellipse>, <line>, <path>, <polygon>, <polyline>, <rect>

    Supported SVG elements:
            <group>, <use>

    Ignored SVG elements:
            <defs>, <eggbot>, <metadata>, <namedview>, <pattern>

    All other SVG elements trigger an error (including <text>)
    '''
    for node in aNodeList:
      # Ignore invisible nodes
      v = node.get( 'visibility', parent_visibility )
      if v == 'inherit':
        v = parent_visibility
      if v == 'hidden' or v == 'collapse':
        pass

      # first apply the current matrix transform to this node's tranform
      matNew = simpletransform.composeTransform( matCurrent,
        simpletransform.parseTransform( node.get( "transform" ) ) )

      if node.tag == inkex.addNS( 'g', 'svg' ) or node.tag == 'g':
        self.recursivelyTraverseSvg( node, matNew, parent_visibility=v )

      elif node.tag == inkex.addNS( 'use', 'svg' ) or node.tag == 'use':

        # A <use> element refers to another SVG element via an xlink:href="#blah"
        # attribute.  We will handle the element by doing an XPath search through
        # the document, looking for the element with the matching id="blah"
        # attribute.  We then recursively process that element after applying
        # any necessary (x,y) translation.
        #
        # Notes:
        #  1. We ignore the height and width attributes as they do not apply to
        #     path-like elements, and
        #  2. Even if the use element has visibility="hidden", SVG still calls
        #     for processing the referenced element.  The referenced element is
        #     hidden only if its visibility is "inherit" or "hidden".

        refid = node.get( inkex.addNS( 'href', 'xlink' ) )
        if not refid:
          pass

        # [1:] to ignore leading '#' in reference
        path = '//*[@id="%s"]' % refid[1:]
        refnode = node.xpath( path )
        if refnode:
          x = float( node.get( 'x', '0' ) )
          y = float( node.get( 'y', '0' ) )
          # Note: the transform has already been applied
          if ( x != 0 ) or ( y != 0 ):
            matNew2 = composeTransform( matNew, parseTransform( 'translate(%f,%f)' % (x,y) ) )
          else:
            matNew2 = matNew
          v = node.get( 'visibility', v )
          self.recursivelyTraverseSvg( refnode, matNew2, parent_visibility=v )

      elif node.tag == inkex.addNS( 'path', 'svg' ):
        path_data = node.get( 'd')
        if path_data:
          self.addPathVertices( path_data, node, matNew )

      elif node.tag == inkex.addNS( 'rect', 'svg' ) or node.tag == 'rect':
        # Manually transform
        #
        #    <rect x="X" y="Y" width="W" height="H"/>
        #
        # into
        #
        #    <path d="MX,Y lW,0 l0,H l-W,0 z"/>
        #
        # I.e., explicitly draw three sides of the rectangle and the
        # fourth side implicitly

        # Create a path with the outline of the rectangle
        x = float( node.get( 'x' ) )
        y = float( node.get( 'y' ) )
        if ( not x ) or ( not y ):
                pass
        w = float( node.get( 'width', '0' ) )
        h = float( node.get( 'height', '0' ) )
        a = []
        a.append( ['M ', [x, y]] )
        a.append( [' l ', [w, 0]] )
        a.append( [' l ', [0, h]] )
        a.append( [' l ', [-w, 0]] )
        a.append( [' Z', []] )
        self.addPathVertices( simplepath.formatPath( a ), node, matNew )

      elif node.tag == inkex.addNS( 'line', 'svg' ) or node.tag == 'line':
        # Convert
        #
        #   <line x1="X1" y1="Y1" x2="X2" y2="Y2/>
        #
        # to
        #
        #   <path d="MX1,Y1 LX2,Y2"/>

        x1 = float( node.get( 'x1' ) )
        y1 = float( node.get( 'y1' ) )
        x2 = float( node.get( 'x2' ) )
        y2 = float( node.get( 'y2' ) )
        if ( not x1 ) or ( not y1 ) or ( not x2 ) or ( not y2 ):
                pass
        a = []
        a.append( ['M ', [x1, y1]] )
        a.append( [' L ', [x2, y2]] )
        self.addPathVertices( simplepath.formatPath( a ), node, matNew )

      elif node.tag == inkex.addNS( 'polyline', 'svg' ) or node.tag == 'polyline':
        # Convert
        #
        #  <polyline points="x1,y1 x2,y2 x3,y3 [...]"/>
        #
        # to
        #
        #   <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...]"/>
        #
        # Note: we ignore polylines with no points

        pl = node.get( 'points', '' ).strip()
        if pl == '':
          pass

        pa = pl.split()
        d = "".join( ["M " + pa[i] if i == 0 else " L " + pa[i] for i in range( 0, len( pa ) )] )
        self.addPathVertices( d, node, matNew )

      elif node.tag == inkex.addNS( 'polygon', 'svg' ) or node.tag == 'polygon':
        # Convert
        #
        #  <polygon points="x1,y1 x2,y2 x3,y3 [...]"/>
        #
        # to
        #
        #   <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...] Z"/>
        #
        # Note: we ignore polygons with no points

        pl = node.get( 'points', '' ).strip()
        if pl == '':
          pass

        pa = pl.split()
        d = "".join( ["M " + pa[i] if i == 0 else " L " + pa[i] for i in range( 0, len( pa ) )] )
        d += " Z"
        self.addPathVertices( d, node, matNew )

      elif node.tag == inkex.addNS( 'ellipse', 'svg' ) or \
            node.tag == 'ellipse' or \
            node.tag == inkex.addNS( 'circle', 'svg' ) or \
            node.tag == 'circle':
        # Convert circles and ellipses to a path with two 180 degree arcs.
        # In general (an ellipse), we convert
        #
        #   <ellipse rx="RX" ry="RY" cx="X" cy="Y"/>
        #
        # to
        #
        #   <path d="MX1,CY A RX,RY 0 1 0 X2,CY A RX,RY 0 1 0 X1,CY"/>
        #
        # where
        #
        #   X1 = CX - RX
        #   X2 = CX + RX
        #
        # Note: ellipses or circles with a radius attribute of value 0 are ignored

        if node.tag == inkex.addNS( 'ellipse', 'svg' ) or node.tag == 'ellipse':
          rx = float( node.get( 'rx', '0' ) )
          ry = float( node.get( 'ry', '0' ) )
        else:
          rx = float( node.get( 'r', '0' ) )
          ry = rx
        if rx == 0 or ry == 0:
          pass

        cx = float( node.get( 'cx', '0' ) )
        cy = float( node.get( 'cy', '0' ) )
        x1 = cx - rx
        x2 = cx + rx
        d = 'M %f,%f ' % ( x1, cy ) + \
          'A %f,%f ' % ( rx, ry ) + \
          '0 1 0 %f,%f ' % ( x2, cy ) + \
          'A %f,%f ' % ( rx, ry ) + \
          '0 1 0 %f,%f' % ( x1, cy )
        self.addPathVertices( d, node, matNew )

      elif node.tag == inkex.addNS( 'pattern', 'svg' ) or node.tag == 'pattern':
        pass

      elif node.tag == inkex.addNS( 'metadata', 'svg' ) or node.tag == 'metadata':
        pass

      elif node.tag == inkex.addNS( 'defs', 'svg' ) or node.tag == 'defs':
        pass

      elif node.tag == inkex.addNS( 'namedview', 'sodipodi' ) or node.tag == 'namedview':
        pass

      elif node.tag == inkex.addNS( 'eggbot', 'svg' ) or node.tag == 'eggbot':
        pass

      elif node.tag == inkex.addNS( 'text', 'svg' ) or node.tag == 'text':
        inkex.errormsg( 'Warning: unable to draw text, please convert it to a path first.' )
        pass

      elif not isinstance( node.tag, basestring ):
        pass

      else:
        inkex.errormsg( 'Warning: unable to draw object <%s>, please convert it to a path first.' % node.tag )
        pass


  def getLength( self, name, default ):
    '''
    Get the <svg> attribute with name "name" and default value "default"
    Parse the attribute into a value and associated units.  Then, accept
    no units (''), units of pixels ('px'), and units of percentage ('%').
    '''
    str = self.document.getroot().get( name )
    if str:
      v, u = parseLengthWithUnits( str )
      if not v:
        # Couldn't parse the value
        return None
      elif ( u == '' ) or ( u == 'px' ):
        return v
      elif u == '%':
        return float( default ) * v / 100.0
      else:
        # Unsupported units
        return None
    else:
      # No width specified; assume the default value
      return float( default )


  def getDocProps( self ):
    '''
    Get the document's height and width attributes from the <svg> tag.
    Use a default value in case the property is not present or is
    expressed in units of percentages.
    '''
    self.docHeight = self.getLength( 'height', N_PAGE_HEIGHT )
    self.docWidth = self.getLength( 'width', N_PAGE_WIDTH )
    if ( self.docHeight == None ) or ( self.docWidth == None ):
      return False
    else:
      return True


  def handleViewBox( self ):
    '''
    Set up the document-wide transform in the event that the document has an SVG viewbox
    '''
    if self.getDocProps():
      viewbox = self.document.getroot().get( 'viewBox' )
      if viewbox:
        vinfo = viewbox.strip().replace( ',', ' ' ).split( ' ' )
        if ( vinfo[2] != 0 ) and ( vinfo[3] != 0 ):
          sx = self.docWidth / float( vinfo[2] )
          sy = self.docHeight / float( vinfo[3] )
          self.docTransform = simpletransform.parseTransform( 'scale(%f,%f)' % (sx, sy) )

  def effect(self):
    try:
      dev = SilhouetteCameo(log=self.tty)
    except Exception as e:
      print >>self.tty, e
      print >>sys.stderr, e
      return
    state = dev.status()    # hint at loading paper, if not ready.
    print >>self.tty, "status=%s" % (state)
    print >>self.tty, "device version: '%s'" % dev.get_version()

    # Viewbox handling
    self.handleViewBox()
    # Build a list of the vertices for the document's graphical elements
    if self.options.ids:
      # Traverse the selected objects
      for id in self.options.ids:
        self.recursivelyTraverseSvg( [self.selected[id]], self.docTransform )
    else:
      # Traverse the entire document
      self.recursivelyTraverseSvg( self.document.getroot(), self.docTransform )
    ## # -------------------------
    ## nodes = self.selected.keys()
    ## # If no nodes are selected, then cut the whole document. 
    ## # if len(nodes) == 0: 
    ## #   nodes = self.doc_ids.keys()[0]    # only the first. All other objects are children anyway.

    ## def getSelectedById(IDlist): # returns lxml elements that have an id in IDlist in the svg
    ##   ele=[]
    ##   svg = self.document.getroot()
    ##   for e in svg.iterfind('.//*[@id]'):
    ##     if IDlist is None or e.get('id') in IDlist:
    ##       ele.append(e)
    ##   return ele

    ## lxml_nodes = []
    ## if len(nodes):
    ##   selected = getSelectedById(nodes)
    ## else:
    ##   selected = self.document.getroot()
    ## for node in selected:
    ##   tag = node.tag[node.tag.rfind("}")+1:]
    ##   if tag in ('grid','namedview','defs','metadata'): continue
    ##   lxml_nodes.append(node)
    ## print >>self.tty, "Nodecount: %d\n" % len(lxml_nodes)

    ## # import xml.etree.ElementTree as ET
    ## # ET.tostring(lxml_nodes[0])

    ## ## This is from better_dxf_output.py: quite lousy implementation.
    ## ## it silently ignores transformation on path objects and cannot really handle rects.
    ## self.plot = Plot({
    ##   'scale':25.4/units['in'], 'margin':0, 'startPosition':(0,0), 
    ##   'smoothness':0.2*units['mm']})
    ## self.plot.loadGraphic(lxml_nodes)
    ## cut = self.plot.toCutList(self.options.multipass)
    ## # print >>self.tty, self.plot.graphic, cut
    ## cut = dev.flip_cut(cut)

    ## FIXME: recursivelyTraverseSvg() from egbot.py looks much more mature.

    cut = []
    for pathlist in self.paths.values():
      for px_path in pathlist:
        mm_path = [] 
        for pt in px_path:
          mm_path.append((pt[0]/3.5433070866, pt[1]/3.5433070866))
        for i in range(0,self.options.multipass): 
          cut.append(mm_path)

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
