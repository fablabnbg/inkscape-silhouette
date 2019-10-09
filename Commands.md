Silhouette Cameo Commands
=========================

The protocol is called GPGL (Graphtec Plotter Graphics Language)

Resources
---------

 * http://www.ohthehugemanatee.net/2011/07/gpgl-reference-courtesy-of-graphtec/
 * https://github.com/tonnerre/Inkcut
 * https://github.com/pmonta/gerber2graphtec/blob/master/graphtec.py#L19-L110
 * https://github.com/vishnubob/silhouette/blob/master/src/silhouette.py
 * https://github.com/vishnubob/silhouette/blob/master/src/gpgl.py
 * https://github.com/jnweiger/robocut/blob/master/Plotter.cpp#L344-L586
 * https://github.com/fablabnbg/inkscape-silhouette/blob/master/silhouette/Graphtec.py#L305-L419
 * https://github.com/Skrupellos/silhouette/blob/master/decode

Typical sequence
----------------

<pre>
"\x1b\x04"  		# initialize plotter
"\x1b\x05"  		# status request	(works already before initialize)
	    		# Response "%d\x03" 	0 ready, 1 moving, 2 empty tray
"TT\x03"    		# home the cutter
"FG\x03"    		# query version
	    		# Response  "CAMEO V1.10    \x03"
"FW%d\x03" % media	# 100-138,300
"!%d\x03" % speed	# 1..10
"FX%d\x03" % press	# 1..33
"FC%d\x03" % off	# off=18: cutting, off=0: pen. Other values unknown. 	#FC p,q,[n] [t]
"FY%d\x03" % enh	# enh=0/1: Trackenhancing on/off
"FN%d\x03" %ori		# ori=1/0: Landscape/Portrait
"FE0\x03"		# ??
"TB71\x03"		# ??
			# Response "    0,    0\x03"
"FA\x03"     		# begin page definition
"FU%d,%d\x03" % (w,h)	# h,w page dimensions without top/left margin. Needed to start left.
"FM1\x03"		# ??
--------------------------------- if registration marks
"TB50,381\x03"
"TB99\x03"
"TB55,1\x03"
"TB%d,%d%d\x03" % (s,w,h)	# s=123 if regsearch, 23 else. w=regwidth*20, h=reglength*20
				# registration mark test /1-2: 180.0mm / 1-3: 230.0mm (origin 15mmx20mm)
"FQ5\x03"
				# Response "    0,    0\x03"
				# Response "    0\x03"	// if reg marks work we get 3 messages back
				# Response "    1\x03"
--------------------------------- else
"TB50,1\x03" 			# no registration marks??
--------------------------------- endif registration marks
"FO%d\x03" % h		# feed command?, 5588 max?
"&100,100,100,\\0,0,Z%d,%d,L0," % (w,h)		# Switch to Data mode....
--------------------------------------------------------
"&1,1,1,TB50,0\x03"	# ??			# Back from Data mode.
"FO0\x03"		# feed the page out
"H,"         		# halt?

</pre>


New Commands
------------
More USB sniffing done. This is the code to draw a triangle with a freshly downloaded Silhouette Studio version 3.3.451 . Note that some of the obscure commands (&x,y,z 'Factor'; H, Halt?) are no longer there. 
I used the new 'Feed' option, instead of 'Do Return to Origin' which was a hard coded setting in older versions. This produces an additional M (move command), followed by SO0 (Set Origin 0), which redefines the page origin to be below the drawing. Yeah! This feature finally allows me to fill a page with multiple plots or cuts. It is especially useful for my mat-free cutting feature, where rewinding the cut paper was likely to tear the design apart.

<pre>
0x1B 0x05                                            ..
- 0x30 0x03

FN0
TB50,0
\30,30
FX1
!8
FC18
FE0,0
FF0,0,0
M175.24,577.08
D157.96,587.14
D678.70,884.62
D675.96,284.92
D157.96,587.14
D175.32,597.06

0x1B 0x05
- 0x31 0x03
...
0x1B 0x05
- 0x30 0x03

FX5
!10
FC18
FE0,0
FF0,0,0
L0
\0,0
M678.70,30
SO0
FN0
TB50,0

0x1B 0x05
- 0x31 0x03
...
0x1B 0x05
- 0x30 0x03

</pre>



Typical sequence on portrait with silhouette studio 3.3.642ss
-------------------------------------------------------------

Init
----

"\x1b\x04"  # initialize plotter
"\x1b\x05"  # status request	(works already before initialize)
            # Response "%d\x03" 	0 ready, 1 moving, 2 empty tray
"FG\x03"    # query version
            # Response  "Silhouette V1.10    \x03"

"[\x03"    # response '    0,    0'
"U\x03"    # response' 20320,   3840'	# device limits?
"FQ0\x03"  # response '    5'
"FQ2\x03"  # response '   17'
"TB71\x03" # response '    0,    4'	# ask for machine stored calibration offset of the regmark sensor optics (y,x / unit 1/20 mm)
"FA\x03"   # response '    0,    0'	# ask for machine stored calibration factors of carriage and roller (carriage, roller / unit 1/100% i.e. 0.0001)

Additional Commands
-------------------
"FB70"	# start calibration

"\x1b\x00\x01"	key press down
"\x1b\x00\x02"	key press up
"\x1b\x00\x04"	key press right
"\x1b\x00\x08"	key press left
"\x1b\x00\x00"	key set none

Kalibration Cut
---------------

FB0,0
FN0
TB50,0
\30,0
Z5910,4070

FX15
!10
FC17
FC18
FE0,0
FF0,0,0

M476.66,0
D576.62,0
M576.62,4000
D476.66,4000
M1202.62,3642.28
D1202.62,3542.32
M5202.62,3542.32
D5202.62,3642.28

FX5
!10
FC18
FE0,0
FF0,0,0
L0
\0,0
M0,0
FB0,0
FN0
TB50,0


Store calibration factors permanently in the machine
----------------------------------------------------

FB-92.02,0  # scale down carriage movements by 0,9202%
FB200,134   # scale up carriage movement by 2%, scale up roller movements by 1,34%


Cut a calibration test cross
----------------------------

TB 70


Store regmark sensor offset calibration permanently in the machine
------------------------------------------------------------------

TB72,0,4.01  # move 0.1mm to the right


Cut without mat
---------------

FN0.TB50,0.\30,0.Z5440,4070.
FX33.!5.FC18.FE0,0.FF0,0,0.FY1.
M382.10,1256.62.D391.40,568.98.
FX5.!10.FC18.FE0,0.FF0,0,0.L0.\0,0.M0,0.FN0.TB50,0.

FN0TB50,0\30,0Z5440,4070
FX33!5FC18FE0,0FF0,0,0FY1
M382.10,1256.62D391.40,568.98
FX5!10FC18FE0,0FF0,0,0L0\0,0M0,0FN0TB50,0

with mat a4
-----------

FN0 TB50,0 \30,0 Z5910,4070
FX33 !5 FC18 FE0,0 FF0,0,0 FY1
M382.10,1256.62 D391.40,568.98
FX5!10FC18FE0,0FF0,0,0L0\0,0M0,0FN0TB50,0

with mat 8"x12"

FN0TB50,0\30,0Z5910,4120
FX33!5FC18FE0,0FF0,0,0FY1
M382.10,1314.62D391.40,626.98
FX5!10FC18FE0,0FF0,0,0L0\0,0M0,0FN0TB50,0

with a4, additional feed 1.0mm

FN0TB50,0\30,0Z5910,4070
FX33!5FC18FE0,0FF0,0,0FY1
M382.10,1256.62D391.40,568.98
FX5!10FC18FE0,0FF0,0,0L0\0,0M411.40,0SO0FN0TB50,0

----> SO0 sets new origin


with a4, double cut, strength 15


FN0TB50,0\30,0Z5910,4070
FX15!5FC18FE0,0FF0,0,0FY1
M382.10,1256.62D391.40,568.98M382.10,1256.62D391.40,568.98
FX5!10FC18FE0,0FF0,0,0L0\0,0M0,0FN0TB50,0


with a4, trackenhancing, strength 22 (rollers three times back and forth)


FN0 TB50,0 FX20 FY0 FU5440 \30,0 Z5910,4070
FX22!5FC18FE0,0
FF0,0,0FY0
M382.10,1256.62D391.40,568.98
FX5!10FC18FE0,0FF0,0,0L0\0,0M0,0FN0TB50,0

---> FY0 track enhancing
---> FU5440 usable length (rollers not to end of page)
