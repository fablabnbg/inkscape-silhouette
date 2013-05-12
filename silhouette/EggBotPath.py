# eggbot.py
# Part of the Eggbot driver for Inkscape
# http://code.google.com/p/eggbotcode/
#
# Version 2.2.1, dated 6/12/2011
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# TODO: Add and honor advisory locking around device open/close for non Win32

from bezmisc import *
from math import sqrt
from simpletransform import *
import gettext
import simplepath
import cspsubdiv
import os
import serial
import string
import sys
import time
import eggbot_scan

F_DEFAULT_SPEED = 1
N_PEN_DOWN_DELAY = 400    # delay (ms) for the pen to go down before the next move
N_PEN_UP_DELAY = 400      # delay (ms) for the pen to up down before the next move
N_PAGE_HEIGHT = 800       # Default page height (each unit equiv. to one step)
N_PAGE_WIDTH = 3200       # Default page width (each unit equiv. to one step)

N_PEN_UP_POS = 50      # Default pen-up position
N_PEN_DOWN_POS = 40      # Default pen-down position
N_SERVOSPEED = 50			# Default pen-lift speed
N_WALK_DEFAULT = 10		# Default steps for walking stepper motors
N_DEFAULT_LAYER = 1			# Default inkscape layer

# if bDebug = True, create an HPGL file to show what is being plotted.
# Pen up moves are shown in a different color if bDrawPenUpLines = True.
# Try viewing the .hpgl file in a shareware program or create a simple viewer.

bDebug = False
miscDebug = False
bDrawPenUpLines = False
bDryRun = False # write the commands to a text file instead of the serial port

platform = sys.platform.lower()

HOME = os.getenv( 'HOME' )
if platform == 'win32':
	HOME = os.path.realpath( "C:/" )  # Arguably, this should be %APPDATA% or %TEMP%

DEBUG_OUTPUT_FILE = os.path.join( HOME, 'test.hpgl' )
DRY_RUN_OUTPUT_FILE = os.path.join( HOME, 'dry_run.txt' )
MISC_OUTPUT_FILE = os.path.join( HOME, 'misc.txt' )

##    if platform == 'darwin':
##	''' There's no good value for OS X '''
##	STR_DEFAULT_COM_PORT = '/dev/cu.usbmodem1a21'
##    elif platform == 'sunos':
##	''' Untested: YMMV '''
##	STR_DEFAULT_COM_PORT = '/dev/term/0'
##    else:
##	''' Works fine on Ubuntu; YMMV '''
##	STR_DEFAULT_COM_PORT = '/dev/ttyACM0'

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

def subdivideCubicPath( sp, flat, i=1 ):
	"""
	Break up a bezier curve into smaller curves, each of which
	is approximately a straight line within a given tolerance
	(the "smoothness" defined by [flat]).

	This is a modified version of cspsubdiv.cspsubdiv(). I rewrote the recursive
	call because it caused recursion-depth errors on complicated line segments.
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

		one, two = beziersplitatt( b, 0.5 )
		sp[i - 1][2] = one[1]
		sp[i][0] = two[2]
		p = [one[2], one[3], two[1]]
		sp[i:1] = [p]

class EggBot( inkex.Effect ):

	def __init__( self ):
		inkex.Effect.__init__( self )

		self.OptionParser.add_option( "--smoothness",
			action="store", type="float",
			dest="smoothness", default=.2,
			help="Smoothness of curves" )
##		self.OptionParser.add_option( "--comPort",
##			action="store", type="string",
##			dest="comport", default=STR_DEFAULT_COM_PORT,
##			help="USB COM port to connect eggbot.")
		self.OptionParser.add_option( "--startCentered",
			action="store", type="inkbool",
			dest="startCentered", default=True,
			help="Start plot with pen centered in the y-axis." )
		self.OptionParser.add_option( "--returnToHome",
			action="store", type="inkbool",
			dest="returnToHome", default=True,
			help="Return to home at end of plot." )
		self.OptionParser.add_option( "--wraparound",
			action="store", type="inkbool",
			dest="wraparound", default=True,
			help="Egg (x) axis wraps around-- take shortcuts!" )
		self.OptionParser.add_option( "--penUpSpeed",
			action="store", type="int",
			dest="penUpSpeed", default=F_DEFAULT_SPEED,
			help="Speed (step/sec) while pen is up." )
		self.OptionParser.add_option( "--penDownSpeed",
			action="store", type="int",
			dest="penDownSpeed", default=F_DEFAULT_SPEED,
			help="Speed (step/sec) while pen is down." )
		self.OptionParser.add_option( "--penDownDelay",
			action="store", type="int",
			dest="penDownDelay", default=N_PEN_DOWN_DELAY,
			help="Delay after pen down (msec)." )
		self.OptionParser.add_option( "--penUpDelay",
			action="store", type="int",
			dest="penUpDelay", default=N_PEN_UP_DELAY,
			help="Delay after pen up (msec)." )
		self.OptionParser.add_option( "--engraving",
			action="store", type="inkbool",
			dest="engraving", default=False,
			help="Enable optional engraving tool." )
		self.OptionParser.add_option( "--tab",
			action="store", type="string",
			dest="tab", default="controls",
			help="The active tab when Apply was pressed" )
		self.OptionParser.add_option( "--penUpPosition",
			action="store", type="int",
			dest="penUpPosition", default=N_PEN_UP_POS,
			help="Position of pen when lifted" )
		self.OptionParser.add_option( "--ServoDownSpeed",
			action="store", type="int",
			dest="ServoDownSpeed", default=N_SERVOSPEED,
			help="Rate of lowering pen " )
		self.OptionParser.add_option( "--ServoUpSpeed",
			action="store", type="int",
			dest="ServoUpSpeed", default=N_SERVOSPEED,
			help="Rate of lifting pen " )
		self.OptionParser.add_option( "--penDownPosition",
			action="store", type="int",
			dest="penDownPosition", default=N_PEN_DOWN_POS,
			help="Position of pen when lowered" )
		self.OptionParser.add_option( "--layernumber",
			action="store", type="int",
			dest="layernumber", default=N_DEFAULT_LAYER,
			help="Selected layer for multilayer plotting" )
		self.OptionParser.add_option( "--setupType",
			action="store", type="string",
			dest="setupType", default="controls",
			help="The active option when Apply was pressed" )
		self.OptionParser.add_option( "--manualType",
			action="store", type="string",
			dest="manualType", default="controls",
			help="The active option when Apply was pressed" )
		self.OptionParser.add_option( "--WalkDistance",
			action="store", type="int",
			dest="WalkDistance", default=N_WALK_DEFAULT,
			help="Selected layer for multilayer plotting" )
		self.OptionParser.add_option( "--cancelOnly",
			action="store", type="inkbool",
			dest="cancelOnly", default=False,
			help="Cancel plot and return home only." )
		self.OptionParser.add_option( "--revPenMotor",
			action="store", type="inkbool",
			dest="revPenMotor", default=False,
			help="Reverse motion of pen motor." )
		self.OptionParser.add_option( "--revEggMotor",
			action="store", type="inkbool",
			dest="revEggMotor", default=False,
			help="Reverse motion of egg motor." )

		self.bPenIsUp = True
		self.virtualPenIsUp = False  #Keeps track of pen postion when stepping through plot before resuming
		self.engraverIsOn = False
		self.penDownActivatesEngraver = False
		self.fX = None
		self.fY = None
		self.fPrevX = None
		self.fPrevY = None
		self.ptFirst = None
		self.bStopped = False
		self.fSpeed = 1
		self.resumeMode = False
		self.nodeCount = int( 0 )		#NOTE: python uses 32-bit ints.
		self.nodeTarget = int( 0 )
		self.pathcount = int( 0 )
		self.LayersPlotted = 0
		self.svgSerialPort = ''
		self.svgLayer = int( 0 )
		self.svgNodeCount = int( 0 )
		self.svgDataRead = False
		self.svgLastPath = int( 0 )
		self.svgLastPathNC = int( 0 )
		self.svgTotalDeltaX = int( 0 )
		self.svgTotalDeltaY = int( 0 )

		self.nDeltaX = 0
		self.nDeltaY = 0

		self.svgWidth = float( N_PAGE_WIDTH )
		self.svgHeight = float( N_PAGE_HEIGHT )
		self.svgTransform = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

		# So that we only generate a warning once for each
		# unsupported SVG element, we use a dictionary to track
		# which elements have received a warning
		self.warnings = {}

		# Hack for mismatched EBB/motors,
		# which have half resolution
		try:
			import motor1600
			self.step_scaling_factor = 2
		except ImportError:
			self.step_scaling_factor = 1

	def effect( self ):
		'''Main entry point: check to see which tab is selected, and act accordingly.'''

		self.svg = self.document.getroot()
		self.CheckSVGforEggbotData()

		if self.options.tab == '"splash"':
			self.allLayers = True
			self.plotCurrentLayer = True
			self.EggbotOpenSerial()
			self.svgNodeCount = 0
			self.svgLastPath = 0
			unused_button = self.doRequest( 'QB\r' ) #Query if button pressed
			self.svgLayer = 12345;  # indicate that we are plotting all layers.
			self.plotToEggBot()


		elif self.options.tab == '"resume"':
			self.EggbotOpenSerial()
			unused_button = self.doRequest( 'QB\r' ) #Query if button pressed
			self.resumePlotSetup()
			if self.resumeMode:
				self.plotToEggBot()
			elif ( self.options.cancelOnly ):
				pass
			else:
				inkex.errormsg( gettext.gettext( "Truly sorry, there does not seem to be any in-progress plot to resume." ) )

		elif self.options.tab == '"layers"':
			self.allLayers = False
			self.plotCurrentLayer = False
			self.LayersPlotted = 0
			self.svgLastPath = 0
			self.EggbotOpenSerial()
			unused_button = self.doRequest( 'QB\r' ) #Query if button pressed
			self.svgNodeCount = 0;
			self.svgLayer = self.options.layernumber
			self.plotToEggBot()
			if ( self.LayersPlotted == 0 ):
				inkex.errormsg( gettext.gettext( "Truly sorry, but I did not find any numbered layers to plot." ) )

		elif self.options.tab == '"setup"':
			self.EggbotOpenSerial()
			self.setupCommand()

		elif self.options.tab == '"manual"':
			self.EggbotOpenSerial()
			self.manualCommand()

##		elif self.options.tab == '"timing"':
##			self.EggbotOpenSerial()
##			if self.serialPort is not None:
##				self.ServoSetupWrapper()
##
##		elif self.options.tab == '"options"':
##			self.EggbotOpenSerial()
##			if self.serialPort is not None:
##
		self.svgDataRead = False
		self.UpdateSVGEggbotData( self.svg )
		self.EggbotCloseSerial()
		return


	def CheckSVGforEggbotData( self ):
		self.svgDataRead = False
		self.recursiveEggbotDataScan( self.svg )
		if ( not self.svgDataRead ):    #if there is no eggbot data, add some:
			eggbotlayer = inkex.etree.SubElement( self.svg, 'eggbot' )
			eggbotlayer.set( 'serialport', '' )
			eggbotlayer.set( 'layer', str( 0 ) )
			eggbotlayer.set( 'node', str( 0 ) )
			eggbotlayer.set( 'lastpath', str( 0 ) )
			eggbotlayer.set( 'lastpathnc', str( 0 ) )
			eggbotlayer.set( 'totaldeltax', str( 0 ) )
			eggbotlayer.set( 'totaldeltay', str( 0 ) )

	def recursiveEggbotDataScan( self, aNodeList ):
		if ( not self.svgDataRead ):
			for node in aNodeList:
				if node.tag == 'svg':
					self.recursiveEggbotDataScan( node )
				elif node.tag == inkex.addNS( 'eggbot', 'svg' ) or node.tag == 'eggbot':
					self.svgSerialPort = node.get( 'serialport' )
					self.svgLayer = int( node.get( 'layer' ) )
					self.svgNodeCount = int( node.get( 'node' ) )

					try:
						self.svgLastPath = int( node.get( 'lastpath' ) )
						self.svgLastPathNC = int( node.get( 'lastpathnc' ) )
						self.svgTotalDeltaX = int( node.get( 'totaldeltax' ) )
						self.svgTotalDeltaY = int( node.get( 'totaldeltay' ) )
						self.svgDataRead = True
					except:
						node.set( 'lastpath', str( 0 ) )
						node.set( 'lastpathnc', str( 0 ) )
						node.set( 'totaldeltax', str( 0 ) )
						node.set( 'totaldeltay', str( 0 ) )
						self.svgDataRead = True

	def UpdateSVGEggbotData( self, aNodeList ):
		if ( not self.svgDataRead ):
			for node in aNodeList:
				if node.tag == 'svg':
					self.UpdateSVGEggbotData( node )
				elif node.tag == inkex.addNS( 'eggbot', 'svg' ) or node.tag == 'eggbot':
					node.set( 'serialport', self.svgSerialPort )
					node.set( 'layer', str( self.svgLayer ) )
					node.set( 'node', str( self.svgNodeCount ) )
					node.set( 'lastpath', str( self.svgLastPath ) )
					node.set( 'lastpathnc', str( self.svgLastPathNC ) )
					node.set( 'totaldeltax', str( self.svgTotalDeltaX ) )
					node.set( 'totaldeltay', str( self.svgTotalDeltaY ) )
					self.svgDataRead = True

	def resumePlotSetup( self ):
		self.LayerFound = False
		if ( self.svgLayer < 101 ) and ( self.svgLayer >= 0 ):
			self.options.layernumber = self.svgLayer
			self.allLayers = False
			self.plotCurrentLayer = False
			self.LayerFound = True
		elif ( self.svgLayer == 12345 ):  # Plot all layers
			self.allLayers = True
			self.plotCurrentLayer = True
			self.LayerFound = True
		if ( self.LayerFound ):
			if ( self.svgNodeCount > 0 ):
				self.nodeTarget = self.svgNodeCount
				self.resumeMode = True
				if ( self.options.cancelOnly ):
					self.resumeMode = False
					self.fPrevX = self.svgTotalDeltaX
					self.fPrevY = self.svgTotalDeltaY
					self.fX = 0
					self.fY = 0
					self.plotLineAndTime()
					self.penUp()   #Always end with pen-up
					self.svgLayer = 0
					self.svgNodeCount = 0
					self.svgLastPath = 0
					self.svgLastPathNC = 0
					self.svgTotalDeltaX = 0
					self.svgTotalDeltaY = 0

	def manualCommand( self ):
		"""Execute commands from the "manual" tab"""

		if self.options.manualType == "none":
			return

		if self.serialPort is None:
			return

##		self.ServoSetup()
		#walks are done at pen-down speed.

		if self.options.manualType == "raise-pen":
			self.ServoSetupWrapper()
			self.penUp()

		elif self.options.manualType == "align-mode":
			self.ServoSetupWrapper()
			self.penUp()
			self.sendDisableMotors()

		elif self.options.manualType == "lower-pen":
			self.ServoSetupWrapper()
			self.penDown()

		elif self.options.manualType == "enable-motors":
			self.sendEnableMotors()

		elif self.options.manualType == "disable-motors":
			self.sendDisableMotors()

		elif self.options.manualType == "version-check":
			strVersion = self.doRequest( 'v\r' )
			inkex.errormsg( 'I asked the EBB for its version info, and it replied:\n ' + strVersion )

		elif self.options.manualType == "enable-engraver":
			if ( not self.options.engraving ):
				inkex.errormsg( gettext.gettext( "The engraver option is disabled. " + \
				" Please enable it first from the \"Options\" tab." ) )
			else:
				self.engraverOn()

		elif self.options.manualType == 'disable-engraver':
			self.engraverOffManual() #Force engraver off, even if it is not enabled.

		else:  # self.options.manualType is "walk-egg-motor" or "walk-pen-motor":
			if self.options.manualType == "walk-egg-motor":
				self.nDeltaX = self.options.WalkDistance
				self.nDeltaY = 0
			elif self.options.manualType == "walk-pen-motor":
				self.nDeltaY = self.options.WalkDistance
				self.nDeltaX = 0
			else:
				return

			#Query pen position: 1 up, 0 down (followed by OK)
			strVersion = self.doRequest( 'QP\r' )
			if strVersion[0] == '0':
				#inkex.errormsg('Pen is down' )
				self.fSpeed = self.options.penDownSpeed
			if strVersion[0] == '1':
				#inkex.errormsg('Pen is up' )
				self.fSpeed = self.options.penUpSpeed

			if ( self.options.revPenMotor ):
				self.nDeltaY = -1 * self.nDeltaY
			if ( self.options.revEggMotor ):
				self.nDeltaX = -1 * self.nDeltaX
			self.nTime = int( round( 1000.0 / self.fSpeed * distance( self.nDeltaX, self.nDeltaY ) ) )
			strOutput = ','.join( ['SM', str( self.nTime ), str( self.nDeltaY ), str( self.nDeltaX )] ) + '\r'
			self.doCommand( strOutput )



	def setupCommand( self ):
		"""Execute commands from the "setup" tab"""

		if self.serialPort is None:
			return

		self.ServoSetupWrapper()

		if self.options.setupType == "align-mode":
			self.penUp()
			self.sendDisableMotors()

		elif self.options.setupType == "toggle-pen":
			self.doCommand( 'TP\r' )		#Toggle pen



	def plotToEggBot( self ):
		'''Perform the actual plotting, if selected in the interface:'''
		#parse the svg data as a series of line segments and send each segment to be plotted

		if self.serialPort is None:
			return

		if self.options.startCentered and ( not self.getDocProps() ):
			# Cannot handle the document's dimensions!!!
			inkex.errormsg( gettext.gettext(
			'The document to be plotted has invalid dimensions. ' +
			'The dimensions must be unitless or have units of pixels (px) or ' +
			'percentages (%). Document dimensions may be set in Inkscape with ' +
			'File > Document Properties' ) )
			return

		# Viewbox handling
		# Also ignores the preserveAspectRatio attribute
		viewbox = self.svg.get( 'viewBox' )
		if viewbox:
			vinfo = viewbox.strip().replace( ',', ' ' ).split( ' ' )
			if ( vinfo[2] != 0 ) and ( vinfo[3] != 0 ):
				sx = self.svgWidth / float( vinfo[2] )
				sy = self.svgHeight / float( vinfo[3] )
				self.svgTransform = parseTransform( 'scale(%f,%f) translate(%f,%f)' % (sx, sy, -float( vinfo[0] ), -float( vinfo[1] ) ) )

		self.ServoSetup()

		# Ensure that the engraver is turned off for the time being
		# It will be turned back on when the first non-virtual pen-down occurs
		if self.options.engraving:
			self.engraverOff()

		if bDebug:
			self.debugOut = open( DEBUG_OUTPUT_FILE, 'w' )
			if bDrawPenUpLines:
				self.debugOut.write( 'IN;SP1;' )
			else:
				self.debugOut.write( 'IN;PD;' )

		try:
			# wrap everything in a try so we can for sure close the serial port
			#self.recursivelyTraverseSvg(self.document.getroot())
			self.penDownActivatesEngraver = True
			self.recursivelyTraverseSvg( self.svg, self.svgTransform )
			self.penUp()   #Always end with pen-up

			# Logically, we want to turn the engraver off here as well,
			# but we put that in our finally clause instead
			# self.engraverOff()

			# return to home, if returnToHome = True
			if ( ( not self.bStopped ) and self.options.returnToHome and ( self.ptFirst ) ):
				self.fX = self.ptFirst[0]
				self.fY = self.ptFirst[1]
				#self.penUp()
				self.nodeCount = self.nodeTarget    # enablesfpx return-to-home only option
				self.plotLineAndTime()
			#inkex.errormsg('Final node count: ' + str(self.svgNodeCount))  #Node Count - Debug option
			if ( not self.bStopped ):
				self.svgLayer = 0
				self.svgNodeCount = 0
				self.svgLastPath = 0
				self.svgLastPathNC = 0
				self.svgTotalDeltaX = 0
				self.svgTotalDeltaY = 0

		finally:
			# We may have had an exception and lost the serial port...
			self.penDownActivatesEngraver = False
			if ( not ( self.serialPort is None ) ) and ( self.options.engraving ):
				self.engraverOff()

	def recursivelyTraverseSvg( self, aNodeList,
			matCurrent=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
			parent_visibility='visible' ):
		"""
		Recursively traverse the svg file to plot out all of the
		paths.  The function keeps track of the composite transformation
		that should be applied to each path.

		This function handles path, group, line, rect, polyline, polygon,
		circle, ellipse and use (clone) elements.  Notable elements not
		handled include text.  Unhandled elements should be converted to
		paths in Inkscape.
		"""
		for node in aNodeList:
			# Ignore invisible nodes
			v = node.get( 'visibility', parent_visibility )
			if v == 'inherit':
				v = parent_visibility
			if v == 'hidden' or v == 'collapse':
				pass

			# first apply the current matrix transform to this node's tranform
			matNew = composeTransform( matCurrent, parseTransform( node.get( "transform" ) ) )

			if node.tag == inkex.addNS( 'g', 'svg' ) or node.tag == 'g':

				self.penUp()
				if ( node.get( inkex.addNS( 'groupmode', 'inkscape' ) ) == 'layer' ):
					if not self.allLayers:
						#inkex.errormsg('Plotting layer named: ' + node.get(inkex.addNS('label', 'inkscape')))
						self.DoWePlotLayer( node.get( inkex.addNS( 'label', 'inkscape' ) ) )
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
				if refid:
					# [1:] to ignore leading '#' in reference
					path = '//*[@id="%s"]' % refid[1:]
					refnode = node.xpath( path )
					if refnode:
						x = float( node.get( 'x', '0' ) )
						y = float( node.get( 'y', '0' ) )
						# Note: the transform has already been applied
						if ( x != 0 ) or (y != 0 ):
							matNew2 = composeTransform( matNew, parseTransform( 'translate(%f,%f)' % (x,y) ) )
						else:
							matNew2 = matNew
						v = node.get( 'visibility', v )
						self.recursivelyTraverseSvg( refnode, matNew2, parent_visibility=v )
					else:
						pass
				else:
					pass

			elif node.tag == inkex.addNS( 'path', 'svg' ):

				self.pathcount += 1

				# if we're in resume mode AND self.pathcount < self.svgLastPath,
				#    then skip over this path.
				# if we're in resume mode and self.pathcount = self.svgLastPath,
				#    then start here, and set
				# self.nodeCount equal to self.svgLastPathNC
				if self.resumeMode and ( self.pathcount == self.svgLastPath ):
					self.nodeCount = self.svgLastPathNC
				if self.resumeMode and ( self.pathcount < self.svgLastPath ):
					pass
				else:
					self.plotPath( node, matNew )
					if ( not self.bStopped ):	#an "index" for resuming plots quickly-- record last complete path
						self.svgLastPath += 1
						self.svgLastPathNC = self.nodeCount

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

				self.pathcount += 1
				# if we're in resume mode AND self.pathcount < self.svgLastPath,
				#    then skip over this path.
				# if we're in resume mode and self.pathcount = self.svgLastPath,
				#    then start here, and set
				# self.nodeCount equal to self.svgLastPathNC
				if self.resumeMode and ( self.pathcount == self.svgLastPath ):
					self.nodeCount = self.svgLastPathNC
				if self.resumeMode and ( self.pathcount < self.svgLastPath ):
					pass
				else:
					# Create a path with the outline of the rectangle
					newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
					x = float( node.get( 'x' ) )
					y = float( node.get( 'y' ) )
					w = float( node.get( 'width' ) )
					h = float( node.get( 'height' ) )
					s = node.get( 'style' )
					if s:
						newpath.set( 'style', s )
					t = node.get( 'transform' )
					if t:
						newpath.set( 'transform', t )
					a = []
					a.append( ['M ', [x, y]] )
					a.append( [' l ', [w, 0]] )
					a.append( [' l ', [0, h]] )
					a.append( [' l ', [-w, 0]] )
					a.append( [' Z', []] )
					newpath.set( 'd', simplepath.formatPath( a ) )
					self.plotPath( newpath, matNew )

			elif node.tag == inkex.addNS( 'line', 'svg' ) or node.tag == 'line':

				# Convert
				#
				#   <line x1="X1" y1="Y1" x2="X2" y2="Y2/>
				#
				# to
				#
				#   <path d="MX1,Y1 LX2,Y2"/>

				self.pathcount += 1
				# if we're in resume mode AND self.pathcount < self.svgLastPath,
				#    then skip over this path.
				# if we're in resume mode and self.pathcount = self.svgLastPath,
				#    then start here, and set
				# self.nodeCount equal to self.svgLastPathNC

				if self.resumeMode and ( self.pathcount == self.svgLastPath ):
					self.nodeCount = self.svgLastPathNC
				if self.resumeMode and ( self.pathcount < self.svgLastPath ):
					pass
				else:
					# Create a path to contain the line
					newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
					x1 = float( node.get( 'x1' ) )
					y1 = float( node.get( 'y1' ) )
					x2 = float( node.get( 'x2' ) )
					y2 = float( node.get( 'y2' ) )
					s = node.get( 'style' )
					if s:
						newpath.set( 'style', s )
					t = node.get( 'transform' )
					if t:
						newpath.set( 'transform', t )
					a = []
					a.append( ['M ', [x1, y1]] )
					a.append( [' L ', [x2, y2]] )
					newpath.set( 'd', simplepath.formatPath( a ) )
					self.plotPath( newpath, matNew )
					if ( not self.bStopped ):	#an "index" for resuming plots quickly-- record last complete path
						self.svgLastPath += 1
						self.svgLastPathNC = self.nodeCount

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

				self.pathcount += 1
				#if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
				#if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
				# self.nodeCount equal to self.svgLastPathNC

				if self.resumeMode and ( self.pathcount == self.svgLastPath ):
					self.nodeCount = self.svgLastPathNC

				if self.resumeMode and ( self.pathcount < self.svgLastPath ):
					pass

				else:
					pa = pl.split()
					if not len( pa ):
						pass
					# Issue 29: pre 2.5.? versions of Python do not have
					#    "statement-1 if expression-1 else statement-2"
					# which came out of PEP 308, Conditional Expressions
					#d = "".join( ["M " + pa[i] if i == 0 else " L " + pa[i] for i in range( 0, len( pa ) )] )
					d = "M " + pa[0]
					for i in range( 1, len( pa ) ):
						d += " L " + pa[i]
					newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
					newpath.set( 'd', d );
					s = node.get( 'style' )
					if s:
						newpath.set( 'style', s )
					t = node.get( 'transform' )
					if t:
						newpath.set( 'transform', t )
					self.plotPath( newpath, matNew )
					if ( not self.bStopped ):	#an "index" for resuming plots quickly-- record last complete path
						self.svgLastPath += 1
						self.svgLastPathNC = self.nodeCount

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

				self.pathcount += 1
				#if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
				#if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
				# self.nodeCount equal to self.svgLastPathNC

				if self.resumeMode and ( self.pathcount == self.svgLastPath ):
					self.nodeCount = self.svgLastPathNC

				if self.resumeMode and ( self.pathcount < self.svgLastPath ):
					pass

				else:
					pa = pl.split()
					if not len( pa ):
						pass
					# Issue 29: pre 2.5.? versions of Python do not have
					#    "statement-1 if expression-1 else statement-2"
					# which came out of PEP 308, Conditional Expressions
					#d = "".join( ["M " + pa[i] if i == 0 else " L " + pa[i] for i in range( 0, len( pa ) )] )
					d = "M " + pa[0]
					for i in range( 1, len( pa ) ):
						d += " L " + pa[i]
					d += " Z"
					newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
					newpath.set( 'd', d );
					s = node.get( 'style' )
					if s:
						newpath.set( 'style', s )
					t = node.get( 'transform' )
					if t:
						newpath.set( 'transform', t )
					self.plotPath( newpath, matNew )
					if ( not self.bStopped ):	#an "index" for resuming plots quickly-- record last complete path
						self.svgLastPath += 1
						self.svgLastPathNC = self.nodeCount

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

					self.pathcount += 1
					#if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
					#if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
					# self.nodeCount equal to self.svgLastPathNC

					if self.resumeMode and ( self.pathcount == self.svgLastPath ):
						self.nodeCount = self.svgLastPathNC

					if self.resumeMode and ( self.pathcount < self.svgLastPath ):
						pass

					else:
						cx = float( node.get( 'cx', '0' ) )
						cy = float( node.get( 'cy', '0' ) )
						x1 = cx - rx
						x2 = cx + rx
						d = 'M %f,%f ' % ( x1, cy ) + \
							'A %f,%f ' % ( rx, ry ) + \
							'0 1 0 %f,%f ' % ( x2, cy ) + \
							'A %f,%f ' % ( rx, ry ) + \
							'0 1 0 %f,%f' % ( x1, cy )
						newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
						newpath.set( 'd', d );
						s = node.get( 'style' )
						if s:
							newpath.set( 'style', s )
						t = node.get( 'transform' )
						if t:
							newpath.set( 'transform', t )
						self.plotPath( newpath, matNew )
						if ( not self.bStopped ):	#an "index" for resuming plots quickly-- record last complete path
							self.svgLastPath += 1
							self.svgLastPathNC = self.nodeCount
			elif node.tag == inkex.addNS( 'metadata', 'svg' ) or node.tag == 'metadata':
				pass
			elif node.tag == inkex.addNS( 'defs', 'svg' ) or node.tag == 'defs':
				pass
			elif node.tag == inkex.addNS( 'namedview', 'sodipodi' ) or node.tag == 'namedview':
				pass
			elif node.tag == inkex.addNS( 'eggbot', 'svg' ) or node.tag == 'eggbot':
				pass
			elif node.tag == inkex.addNS( 'title', 'svg' ) or node.tag == 'title':
				pass
			elif node.tag == inkex.addNS( 'desc', 'svg' ) or node.tag == 'desc':
				pass
			elif node.tag == inkex.addNS( 'text', 'svg' ) or node.tag == 'text':
				if not self.warnings.has_key( 'text' ):
					inkex.errormsg( gettext.gettext( 'Warning: unable to draw text; ' +
						'please convert it to a path first.  Consider using the ' +
						'Hershey Text extension which is located under the '+
						'"Render" category of extensions.' ) )
					self.warnings['text'] = 1
				pass
			elif node.tag == inkex.addNS( 'image', 'svg' ) or node.tag == 'image':
				if not self.warnings.has_key( 'image' ):
					inkex.errormsg( gettext.gettext( 'Warning: unable to draw bitmap images; ' +
						'please convert them to line art first.  Consider using the "Trace bitmap..." ' +
						'tool of the "Path" menu.  Mac users please note that some X11 settings may ' +
						'cause cut-and-paste operations to paste in bitmap copies.' ) )
					self.warnings['image'] = 1
				pass
			elif node.tag == inkex.addNS( 'pattern', 'svg' ) or node.tag == 'pattern':
				pass
			elif node.tag == inkex.addNS( 'radialGradient', 'svg' ) or node.tag == 'radialGradient':
				# Similar to pattern
				pass
			elif node.tag == inkex.addNS( 'linearGradient', 'svg' ) or node.tag == 'linearGradient':
				# Similar in pattern
				pass
			elif node.tag == inkex.addNS( 'style', 'svg' ) or node.tag == 'style':
				# This is a reference to an external style sheet and not the value
				# of a style attribute to be inherited by child elements
				pass
			elif node.tag == inkex.addNS( 'cursor', 'svg' ) or node.tag == 'cursor':
				pass
			elif node.tag == inkex.addNS( 'color-profile', 'svg' ) or node.tag == 'color-profile':
				# Gamma curves, color temp, etc. are not relevant to single color output
				pass
			elif not isinstance( node.tag, basestring ):
				# This is likely an XML processing instruction such as an XML
				# comment.  lxml uses a function reference for such node tags
				# and as such the node tag is likely not a printable string.
				# Further, converting it to a printable string likely won't
				# be very useful.
				pass
			else:
				if not self.warnings.has_key( str( node.tag ) ):
					t = str( node.tag ).split( '}' )
					inkex.errormsg( gettext.gettext( 'Warning: unable to draw <' + str( t[-1] ) +
						'> object, please convert it to a path first.' ) )
					self.warnings[str( node.tag )] = 1
				pass

	def DoWePlotLayer( self, strLayerName ):
		"""
		We are only plotting *some* layers. Check to see
		whether or not we're going to plot this one.

		First: scan first 4 chars of node id for first non-numeric character,
		and scan the part before that (if any) into a number

		Then, see if the number matches the layer.
		"""

		TempNumString = 'x'
		stringPos = 1
		CurrentLayerName = string.lstrip( strLayerName ) #remove leading whitespace

		# Look at layer name.  Sample first character, then first two, and
		# so on, until the string ends or the string no longer consists of
		# digit characters only.

		MaxLength = len( CurrentLayerName )
		if MaxLength > 0:
			while stringPos <= MaxLength:
				if str.isdigit( CurrentLayerName[:stringPos] ):
					TempNumString = CurrentLayerName[:stringPos] # Store longest numeric string so far
					stringPos = stringPos + 1
				else:
					break

		self.plotCurrentLayer = False    #Temporarily assume that we aren't plotting the layer
		if ( str.isdigit( TempNumString ) ):
			if ( self.svgLayer == int( float( TempNumString ) ) ):
				self.plotCurrentLayer = True	#We get to plot the layer!
				self.LayersPlotted += 1
		#Note: this function is only called if we are NOT plotting all layers.

	def getLength( self, name, default ):
		'''
		Get the <svg> attribute with name "name" and default value "default"
		Parse the attribute into a value and associated units.  Then, accept
		no units (''), units of pixels ('px'), and units of percentage ('%').
		'''
		str = self.svg.get( name )
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
		self.svgHeight = self.getLength( 'height', N_PAGE_HEIGHT )
		self.svgWidth = self.getLength( 'width', N_PAGE_WIDTH )
		if ( self.svgHeight == None ) or ( self.svgWidth == None ):
			return False
		else:
			return True

	def plotPath( self, path, matTransform ):
		'''
		Plot the path while applying the transformation defined
		by the matrix [matTransform].
		'''
		# turn this path into a cubicsuperpath (list of beziers)...

		d = path.get( 'd' )

		if len( simplepath.parsePath( d ) ) == 0:
			return

		p = cubicsuperpath.parsePath( d )

		# ...and apply the transformation to each point
		applyTransformToPath( matTransform, p )

		# p is now a list of lists of cubic beziers [control pt1, control pt2, endpoint]
		# where the start-point is the last point in the previous segment.
		for sp in p:

			subdivideCubicPath( sp, self.options.smoothness )
			nIndex = 0

			for csp in sp:

				if self.bStopped:
					return

				if self.plotCurrentLayer:
					if nIndex == 0:
						self.penUp()
						self.virtualPenIsUp = True
					elif nIndex == 1:
						self.penDown()
						self.virtualPenIsUp = False

				nIndex += 1

				self.fX = float( csp[1][0] ) / self.step_scaling_factor
				self.fY = float( csp[1][1] ) / self.step_scaling_factor

				# store home
				if self.ptFirst is None:

					# if we should start at center, then the first line segment should draw from there
					if self.options.startCentered:
						self.fPrevX = self.svgWidth / ( 2 * self.step_scaling_factor )
						self.fPrevY = self.svgHeight / ( 2 * self.step_scaling_factor )

						self.ptFirst = ( self.fPrevX, self.fPrevY )
					else:
						self.ptFirst = ( self.fX, self.fY )

				if self.plotCurrentLayer:
					self.plotLineAndTime()
					self.fPrevX = self.fX
					self.fPrevY = self.fY

	def sendEnableMotors( self ):
		self.doCommand( 'EM,1,1\r' )

	def sendDisableMotors( self ):
		# Insist on turning the engraver off.  Otherwise, if it is on
		# and the pen is down, then the engraver's vibration may cause
		# the loose pen arm to start moving or the egg to start turning.
		self.engraverOffManual()
		self.doCommand( 'EM,0,0\r' )

	def doTimedPause( self, nPause ):
		while ( nPause > 0 ):
			if ( nPause > 750 ):
				td = int( 750 )
			else:
				td = nPause
				if ( td < 1 ):
					td = int( 1 ) # don't allow zero-time moves
			if ( not self.resumeMode ):
				self.doCommand( 'SM,' + str( td ) + ',0,0\r' )
			nPause -= td

	def penUp( self ):
		if ( ( not self.resumeMode ) or ( not self.virtualPenIsUp ) ):
			self.doCommand( 'SP,1\r' )
			self.doTimedPause( self.options.penUpDelay ) # pause for pen to go up
			self.bPenIsUp = True
		self.virtualPenIsUp = True

	def penDown( self ):
		self.virtualPenIsUp = False  # Virtual pen keeps track of state for resuming plotting.
		if ( not self.resumeMode ):
			if self.penDownActivatesEngraver:
					self.engraverOn() # will check self.enableEngraver
			self.doCommand( 'SP,0\r' )
			self.doTimedPause( self.options.penDownDelay ) # pause for pen to go down
			self.bPenIsUp = False

	def engraverOff( self ):
		# Note: we don't bother checking self.engraverIsOn -- turn it off regardless
		# Reason being that we may not know the true hardware state
		if self.options.engraving:
			self.doCommand( 'PO,B,3,0\r' )
			self.engraverIsOn = False
			
	def engraverOffManual( self ):
		# Turn off engraver, whether or not the engraver is enabled. 
		# This is only called by manual commands like "engraver off" and "motors off."
		self.doCommand( 'PO,B,3,0\r' )
		self.engraverIsOn = False			
			
	def engraverOn( self ):
		if self.options.engraving and ( not self.engraverIsOn ):
			self.engraverIsOn = True
			self.doCommand( 'PD,B,3,0\r' )	#Added 6/6/2011, necessary.
			self.doCommand( 'PO,B,3,1\r' )

	def ServoSetupWrapper( self ):
		self.ServoSetup()
		strVersion = self.doRequest( 'QP\r' ) #Query pen position: 1 up, 0 down (followed by OK)
		if strVersion[0] == '0':
			#inkex.errormsg('Pen is down' )
			self.doCommand( 'SP,0\r' ) #Lower Pen
		else:
			self.doCommand( 'SP,1\r' ) #Raise pen

	def ServoSetup( self ):
		# Pen position units range from 0% to 100%, which correspond to
		# a timing range of 6000 - 30000 in units of 1/(12 MHz).
		# 1% corresponds to 20 us, or 240 units of 1/(12 MHz).

		intTemp = 240 * ( self.options.penUpPosition + 25 )
		self.doCommand( 'SC,4,' + str( intTemp ) + '\r' )
		intTemp = 240 * ( self.options.penDownPosition + 25 )
		self.doCommand( 'SC,5,' + str( intTemp ) + '\r' )

		# Servo speed units are in units of %/second, referring to the
		# percentages above.  The EBB takes speeds in units of 1/(12 MHz) steps
		# per 21 ms.  Scaling as above, 1% in 1 second corresponds to
		# 240 steps/s, which corresponds to 0.240 steps/ms, which corresponds
		# to 5.04 steps/21 ms.  Rounding this to 5 steps/21 ms is correct
		# to within 1 %.

##		intTemp = 5 * self.options.ServoSpeed
##		self.doCommand( 'SC,10,' + str( intTemp ) + '\r' )
		#inkex.errormsg('Setting up Servo Motors!')
		intTemp = 5 * self.options.ServoUpSpeed
		self.doCommand( 'SC,11,' + str( intTemp ) + '\r' )
		intTemp = 5 * self.options.ServoDownSpeed
		self.doCommand( 'SC,12,' + str( intTemp ) + '\r' )

	def stop( self ):
		self.bStopped = True

	def plotLineAndTime( self ):
		'''
		Send commands out the com port as a line segment (dx, dy) and a time (ms) the segment
		should take to implement
		'''

		if self.bStopped:
			return
		if ( self.fPrevX is None ):
			return

		self.nDeltaX = int( self.fX ) - int( self.fPrevX )
		self.nDeltaY = int( self.fY ) - int( self.fPrevY )

		if self.bPenIsUp:
			self.fSpeed = self.options.penUpSpeed

			if ( self.options.wraparound ):
				if ( self.nDeltaX > 1600 / self.step_scaling_factor ):
					while ( self.nDeltaX > 1600 / self.step_scaling_factor ):
						self.nDeltaX -= 3200 / self.step_scaling_factor
				elif ( self.nDeltaX < -1600 / self.step_scaling_factor ):
					while ( self.nDeltaX < -1600 / self.step_scaling_factor ):
						self.nDeltaX += 3200 / self.step_scaling_factor

		else:
			self.fSpeed = self.options.penDownSpeed


		if ( distance( self.nDeltaX, self.nDeltaY ) > 0 ):
			self.nodeCount += 1

			if self.resumeMode:
				if ( self.nodeCount > self.nodeTarget ):
					self.resumeMode = False
					#inkex.errormsg('First node plotted will be number: ' + str(self.nodeCount))
					if ( not self.virtualPenIsUp ):
						self.penDown()
						self.fSpeed = self.options.penDownSpeed

			nTime = int( math.ceil( 1000 / self.fSpeed * distance( self.nDeltaX, self.nDeltaY ) ) )

			while ( ( abs( self.nDeltaX ) > 0 ) or ( abs( self.nDeltaY ) > 0 ) ):
				if ( nTime > 750 ):
					xd = int( round( ( 750.0 * self.nDeltaX ) / nTime ) )
					yd = int( round( ( 750.0 * self.nDeltaY ) / nTime ) )
					td = int( 750 )
				else:
					xd = self.nDeltaX
					yd = self.nDeltaY
					td = nTime
					if ( td < 1 ):
						td = 1		# don't allow zero-time moves.

				if ( not self.resumeMode ):
					if ( self.options.revPenMotor ):
						yd2 = yd
					else:
						yd2 = -yd
					if ( self.options.revEggMotor ):
						xd2 = -xd
					else:
						xd2 = xd

					strOutput = ','.join( ['SM', str( td ), str( yd2 ), str( xd2 )] ) + '\r'
					self.svgTotalDeltaX += xd
					self.svgTotalDeltaY += yd
					self.doCommand( strOutput )

				self.nDeltaX -= xd
				self.nDeltaY -= yd
				nTime -= td

			#self.doCommand('NI\r')  #Increment node counter on EBB
			strButton = self.doRequest( 'QB\r' ) #Query if button pressed
			if strButton[0] == '0':
				pass #button not pressed
			else:
				self.svgNodeCount = self.nodeCount;
				inkex.errormsg( 'Plot paused by button press after segment number ' + str( self.nodeCount ) + '.' )
				inkex.errormsg( 'Use the "resume" feature to continue.' )
				#self.penUp()  # Should be redundant...
				self.engraverOff()
				self.bStopped = True
				return

	# note: the pen-motor is first, and it corresponds to the y-axis on-screen

	def EggbotOpenSerial( self ):
		if not bDryRun:
			self.serialPort = self.getSerialPort()
		else:
			self.serialPort = open( DRY_RUN_OUTPUT_FILE, 'w' )

		if self.serialPort is None:
			inkex.errormsg( gettext.gettext( "Unable to find an Eggbot on any serial port. :(" ) )

	def EggbotCloseSerial( self ):
		try:
			if self.serialPort:
				self.serialPort.flush()
				self.serialPort.close()
			if bDebug:
				self.debugOut.close()
		finally:
			self.serialPort = None
			return

	def testSerialPort( self, strComPort ):
		'''
		look at COM1 to COM20 and return a SerialPort object
		for the first port with an EBB (eggbot board).

		YOU are responsible for closing this serial port!
		'''

		try:
			serialPort = serial.Serial( strComPort, timeout=1 ) # 1 second timeout!

			serialPort.setRTS()  # ??? remove
			serialPort.setDTR()  # ??? remove
			serialPort.flushInput()
			serialPort.flushOutput()

			time.sleep( 0.1 )

			serialPort.write( 'v\r' )
			strVersion = serialPort.readline()

			if strVersion and strVersion.startswith( 'EBB' ):
				# do version control here to check the firmware...
				return serialPort
			serialPort.close()
		except serial.SerialException:
			pass
		return None

	def getSerialPort( self ):

		# Before searching, first check to see if the last known
		# serial port is still good.

		serialPort = self.testSerialPort( self.svgSerialPort )
		if serialPort:
			return serialPort

		# Try any devices which seem to have EBB boards attached
		for strComPort in eggbot_scan.findEiBotBoards():
			serialPort = self.testSerialPort( strComPort )
			if serialPort:
				self.svgSerialPort = strComPort
				return serialPort

		# Try any likely ports
		for strComPort in eggbot_scan.findPorts():
			serialPort = self.testSerialPort( strComPort )
			if serialPort:
				self.svgSerialPort = strComPort
				return serialPort

		return None

	def doCommand( self, cmd ):
		try:
			self.serialPort.write( cmd )
			response = self.serialPort.readline()
			if ( response != 'OK\r\n' ):
				if ( response != '' ):
					inkex.errormsg( 'After command ' + cmd + ',' )
					inkex.errormsg( 'Received bad response from EBB: ' + str( response ) + '.' )
					#inkex.errormsg('BTW:: Node number is ' + str(self.nodeCount) + '.')

				else:
					inkex.errormsg( 'EBB Serial Timeout.' )

		except:
			pass

	def doRequest( self, cmd ):
		response = ''
		try:
			self.serialPort.write( cmd )
			response = self.serialPort.readline()
			unused_response = self.serialPort.readline() #read in extra blank/OK line
		except:
			inkex.errormsg( gettext.gettext( "Error reading serial data." ) )

		return response

def distance( x, y ):
	'''
	Pythagorean theorem!
	'''
	return sqrt( x * x + y * y )

e = EggBot()
#e.affect(output=False)
e.affect()
