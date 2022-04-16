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
 * https://github.com/Snow4DV/graphtec-gp-gl-manual/raw/main/Manual.pdf

Command Summary
---------------

This section summarizes in ASCII order the known and observed commands understood by one or more
models in the Silhouette Cameo line (along with some Graphtec models not sold under the
Silhouette brand). The original source for most of these commands is the GPGL reference for the
CraftRoboPro S, CE5000-60, and CE5000-120 from Graphtec. Ths reference is no longer available
at the first link above but still accessible via

https://web.archive.org/web/20160801023226/http://ohthehugemanatee.net/uploads/2011/07/GP-GL.pdf

Commands listed in the reference have a (G) in their comments. Others were determined by USB
capture or similar means. In the specification of the commands, all characters are literal
(with for example ^C meaning Ctrl-C, i.e. ASCII 03, not the two characters ^ and C)
except for lower case letter-sequences, brackets/parens that occur after the first character,
and ellipses (...). Lower-case letter sequences stand for ASCII-encoded numeric values,
brackets/parens were in the original spec and likely indicate optional elements, athough it's
not clear if there is a difference between brackets and parens, and ellipses stand for arbitrary
repetition of prior elements.

Letter sequences starting with r,x,y,z are coordinates and can include decimals; those starting
with t are angles (theta, in degrees, not sure if decimals are allowed); and the remainder are
integers, usually nonnegative. The commands omit the trailing Ctrl-C (^C) command terminator.

Also note that in the Graphtec reference, many of the commands include a notation of `[t]` at the
end; for example the original spec of the Draw command is `Dx1,y1,x2,y2,...xn,yn[t]`. It is not
clear from the document (at least not to me) what these `[t]` notations mean, but I put it after
the (G) in comments if it was there, to preserve the information.

<pre>
Command                              Name                   Comments
------------------------             -------------------    ----------------------------------------------------
^[^D                                 Initialize Device
^[^E                                 Query Status
^[^K                                 Query Firmware         Not sure how this differs from the FG command below,
                                                            but recent Silhouette Studio with Cameo 4 Pro issues both
^[^O                                 Query Tool Setup
!l[,n]                               Speed                  (G)[t]  n is from 1 to 8, and so is probably the pen
                                                            number; l is labeled as being from 1 to 10 or 101 to 160, with the
                                                            comments that for l < 11, V = (Max Speed) x l/10, and for l > 100,
                                                             V = l - 100
"m,                                  Error Mask             (G)  In "Interface Control" section
#                                    Read Status Word 3     (G)
$n,(m,)                              Font                   (G)  Selects the code chart for the chars (see
                                                            Graphtec manual pdf 1-32 for more
%n,x,y,d,t                           Hatching               (G)[t]  for n from 1 to 3
%n,ra,rb,ta,tb,d,t                   Hatching                       for n from 11 to 13
%n,dt,xa,ya,xb,yb,...;,xn,yn         Hatching                       for n from 21 to 23
&p,q,r,                              Factor                 (G)  Specifies the magnification (All coordinates,
                                                            lengths,
                                                            character sizes are multiplied by p/r or q/r but parameters of OFFSET,
					                                         UR and LL commands are not affected)
(na,nb,...,nn                        User's Pattern         (G)[t]  Marked as a no-op
(P[p,]xa,ya,[p,]xb,yb,...;[p,]xn,yn  User's Program Pattern (G)  This command enables you to draw characters,
                                                            symbols which are not in the character code charts (chart from
					                    Graphtec GP-GL manual may work)
)a,x,y,ra,rb,ta,tb,tc                Ellipse                (G)  a describes how it moves to the start point -
                                                            if a = 0 it moves the pen raised, if a = 1 it moves the pen lowered.
					                    ta and tb - initial and final angles. tc - angle between major axis
					                    and X-axis.
* a,f[,n]                            Pen Acceleration&Force (G)[t] n is from 1 to 8, and so is probably the pen
                                                            number; a is labeled as being from 1 to 3; and f from 1 to some value
					                    in the thirties depending on model. Seems to have been supplanted by
					                    TJ and FX
/x,y,t;,                             Rotate                 (G)  Rotates coordination system
:                                    Clear                  (G)  In "Interface Control" section
;                                    Interface Clear        (G)  In "Interface Control" section
=na nb                               Term                   (G)  In "Interface Control" section, specifies the
                                                                 data terminator(s)
>xa,ya,...;xn,yn                     Clipping               (G)[t]  Coordinates are connected to closed line,
                                                            making it possible to plot only inside of it (last point is connected
					                    to the first one)
?                                    Read Offset            (G)  In "Output Coordinates" section
@                                    Read Status Word 2     (G)
A                                    Alpha Reset            (G)  Returns the parameters of font, alpha scale,
                                                            alpha space, alpha rotate, alpha italic, label position, point mark
					                    to the values set at the initialization of the plotter
Bl,                                  Line Scale             (G)  Specifies the pitch of broken lines (needed if
                                                            non-0 line type is used)
BEn                                                         Binary encoded Relative Draw, n says how many bytes to read (1-3).
                                                            Observed on Cameo 4 Pro and Portrait 3.
                                                            For coordinate encoding see beutil.py
BS sa,sb,sc,sd                       Buffer Size            (G)  Marked as a no-op
BZ a,xa,ya,xb,yb,xc,yc,xd,yd[,d]     Bezier Curve           (G)[t]  Not clear what a or [,d] mean
C                                    Call GIN               (G)  In "Output Coordinates" section, puts the
                                                            plotter in digitaztion mode, and outputs the coords and status
					                    (pen number and up/down)
Dxa,ya,xb,yb,...,xn,yn               Draw                   (G)[t]  Cuts from the current position to each
                                                            of the given points in turn
DPra,ta,tb,tb,...,rn,tn              Draw Polar             (G)[t]  Like Draw but with polar coordinates
Exa,ya,xb,yb,...,xn,yn               Relative Draw          (G)[t]  Coordinates are deltas instead of absolute
                                                            positions; not clear if xb,yb is relative to the result of displacing
                                                            by xa,ya, or from the position at the commencement of the command
EPr,t                                Relative Draw Polar    (G)[t]
Fl                                   Chart Feed             (G)[t]  ??
FA                                   Calibration Query      Returns values set with FBrc,rr.
FBrc,rr                              Set Motion Scaling     rc and rr scale carriage and roller movements by
                                                            basis points (see examples below); used only for calibration, as
                                                            effects are permanent.
FCp,q[,n]                            Cutter Offset          (G)[t]  Not clear what p,q mean, but Silhouette
                                                            Studio definitely emits this command, see below for some apparent
                                                            p-values; silhouette/Graphtec.py says p and q are millimeter
                                                            offsets; n is apparently the pen
FDt                                  Blade Rotation Control (G)[t]  Don't think any Silhouette models can do
                                                            this
FEl[,n]                              Lift Control           l=1 lift, l=0 unlift, n is the pen
FFs,e,n                              Sharpen Corners        s=start, e=end (0 resets?), n is the pen
FG                                   Query Firmware Version
FMn                                                         n can be 0 or 1; Silhouette Studio generally
                                                            seems to emit an FM1, but silhouette/Graphtec.py does not
FNn                                  Set Orientation        n=0 portrait, n=1 landscape
FOn                                  Feed                   n is the distance to feed
FQ0                                  Speed Query            Maybe?
FQ2                                  Offset Query           Maybe?
FQ5                                  Regmark Query
FUh[,w]                              Set Page Dimensions    silhouette/Graphtec.py says only needed for
                                                            trackenhancing
FWn                                  Set Media              n from 100-138 or 300
FXn                                  Set Downward Force     n from 1 to something in thirties depending on model
FYn                                  Track Enhance Control  comments/examples below mean n=0 is on, n=1 off,
                                                            oddly enough
G                                    GIN                    (G)  In "Output Coordinates" section, outputs the
                                                            coordinates of the pen and its status (up/down)
H                                    Home                   (G)
Ip,                                  Alpha Italic           (G)  Presumably makes text drawn with Print italic,
                                                            p - tilt calculated with formula p = 256 * tan(a), where a is angle
					                    in rads
Jn,(m)                               New Pen                (G)  n is labeled as running from 1 to 8, and is
                                                            presumably the pen/tool number; not clear what m is
Kca,cb,...,cn                        Kana(Greek)            (G)[t] In "Character and Symbol" section, so perhaps
                                                            draws/cuts the given Greek or special characters (look to the Graphtec
					                    GP-GL manual)
Lp,                                  Line Type              (G)  Specifies the type of line (like "-- - --" or
                                                            ". . ." where p - parameter from 0 to 8 (see the Graphtec GP-GL manual)
LPn                                  Label Position         (G)[t]  Moves pen to label position, the label
                                                            tself is put in square and n specifies its element (1 - bottom-left
					                    vertex, 2 - middle of left side, 3 - top-left vertex, 4 - middle of
					                    bottom side, 5 - center of square, 6 - middle of top side, 7 -
					                    bottom-right vertex, 8 - middle of right side, 9 - top-right vertex)
Mx,y                                 Move                   (G)  Moves the head without cutting
MPr,t                                Move Polar             (G)[t]
Nn,                                  Mark                   (G)  In "Character and Symbol", so perhaps draws
                                                            the nth point marker (like a small dot, square, triangle, etc)
Ox,y                                 Relative Move          (G)  Coordinates are deltas
OPr,t                                Relative Move Polar    (G)[t]
Pca,cb,...,cn                        Print                  (G)[t] In "Character and Symbol", draws/cuts given
                                                            characters from the pattern chart (see the Graphtec GP-GL manual)
Ql(k,)                               Alpha Space            (G)  Specifies the spacing between the start point
                                                            of one character and the start point of the next character, l -
					                    displacement in X axis, k - displacement in Y axis
Rt,                                  Alpha Rotate           (G)  Rotates text drawn by Print, t - angle with X axis
RC c,xa,ya,[P,],xb,yb,[P1,]...xn,yn  Replot Character       (G)[t]  ??
RPt,za,zb                            Radius Plot            (G)  Unclear what this does
Sn,(m,)                              Alpha Scale            (G)  Sets the size letters are drawn, n - height,
                                                            m - width
SOn                                  Set Origin             (G)  Apparently sets the current location to be the
                                                            coordinate system origin going forward; unclear what n means
SPc                                  Select Point Mark      (G)[t]  Unclear what this does
T n                                  Buzzer                 (G)  Turns on and off the PROMPT lamp (or buzzer)
TB50,n                               Set Orientation        n=0 portrait, n=1 landscape; seems redundant with FN, but
                                                            Silhouette Studio issues both, so we do too; but judging from the following
                                                            commands, maybe has to do with regmarks orientation
TB23,h,w                             Set Regmark Area       Distances between marks, ignoring strokes (mark width)
TB51,l                               Set Regmark Length     Length of one arm of the right angle marks
TB52,n                               Set Regmark Type       n=0 is Original,SD, n=2 is Cameo,Portrait
TB53,w                               Set Regmark Width      Mark stroke thickness
TB55,n                               Regmark                Something to do with Regmarks; see silhouette/Graphtec.py
TB99                                 Use Regmarks           Apparently, anyway
TB70                                 Cut Calibration Cross
TB71                                 Calibration Query      Exact semantics/responses unclear, see silhouette/Graphtec.py
TB72,rv,rh                           Set Regmark Offset     Only for calibration, effect is permanent
TB123,h,w,u,l                        Automatic Regmark      height, width, upper (i.e. top dimension), left
TC                                   <Unknown> Query
TFd,n                                Set Tool Depth         For Autoblade; d is depth, n is tool (generally must be 1)
TGn                                  Set Cutting Mat        n values: 0 - None, 1 - Cameo 12x12, 2 - Cameo 12x24
                                                            8 - Cameo 15x15, 9 - Cameo 24x24 (must be others)
TI                                   Query Name
TJa                                  Set Acceleration       Seems to have supplanted *
TO                                   Query                  Observed in connecting to Silhouette Cameo 4 Pro
TT                                   Home Cutter            Earlier models and/or versions of Silhouette Studio
U                                    Read Upper Right       (G)
V                                    Read Status Word 1     (G)
Wx,y,ra,rb,ta,tb[,d]                 Circle                 (G)[t] x,y - center; ra,rb - initial and final radii,
                                                            ta,tb - initial and final angles; d - angle,when d>0: subtends the given
					                    angle with segments of the circle (d - 100 gives 10° segments), when d<0:
					                    gives the number of segments of the circle (d = -5 divides circle into 5)
WPxa,ya,xb,yb,xc,yc[,d]              3-Point Circle         (G)[t]  d acts in the same way as in Circle?
Xp,q,r[,n1,n2]                       Axis                   (G)[t]  Draws coordinate axis and scale lines parallel
                                                            to X or Y axis. p - sets axial direction and behavior of q param:
					                    p = 0 - axial direction is Y, r - number of repeats of scale lines,
					                    p = 1 - same but axial direction i X. p = 2 - axial direction is Y,
					                    r - number of divisions (of scale lines), p = 3 - same but axial
					                    direction is X
Ya,xa,ya,xb,yb,...;xn,yn             Curve                  (G)[t]  Draws a cubic curve through given points,
                                                            a = 0 - open curve, a = 1 - closed curve
Zx,y,                                Write Upper Right      (G)  Apparently sets the coordinate of the upper right
                                                            of the cut area
[                                    Read Lower Left        (G)
\x,y,                                Write Lower Left       (G)  Apparently sets the coordinate of the lower left
                                                            of the cut area
]ra,rb,ta,tb[,d]                     Relative Circle        (G)[t]  Like Circle but centered at the
                                                            current location;
^x,y,                                Offset                 (G)  Moves the coordinate origin to the specified coordinates
^Px,y[,t[f]]                         Offset Polar           (G)[t]  This is a literal caret and P, parameters unclear
_a,xa,ya,xb,yb,...xn,yn              Relative Curve         (G)[t]  Presumably like Curve, but with deltas rather
                                                            than absolute commands;

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

Cameo 4 Pro
-----------
Captured on Windows 10 using USBpcap running Silhouette Studio 4.4.476ss on 2021 Sep 2

Multiple commands on one line separated by spaces (in place of ^C, command terminator)
were sent in a single packet. The first several commands (up to TG9) were all various
queries; there were also multiple ^[^E status queries and ^[^O tool queries throughout
which have been suppressed in the transcripts below. The BE command appears entirely new
and I have no idea what function it served. Note there is no D command, yet one slit was
cut; I am confused about that.

with Cameo Pro 24x24 mat:

FG
TI
TO
TB71
FA
^[^K
TG9 FN0 TB50,0 FM1 \30,30 Z12162,12162
J1 FX15,1 TJ0 !10,1 FC0,1,1
FE0,1 FF1,0,1 FF1,1,1 FX15,1 TJ3
FC18,1,1
M301,356 BE2
L0 \0,0 M0,0 J0 FN0 TB50,0

with Cameo Plus 15x15 mat, all was the same except the 7th line was replaced with:

TG8 FN0 TB50,0 FM1 \30,9 Z7590,7320

Portrait 3 Firmware Upgrade
---------------------------
Upgrading the firmware is a stream of `S{address}{data}\n`, with no 0x03 in sight.
There is no initialisation protocol, the Portrait3_V104_R0001.S that comes with Silhouette Studio is streamed as is.
This was observed when upgrading from V1.01 to V1.04.
