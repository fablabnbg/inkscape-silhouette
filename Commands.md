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
"FY%d\x03" % enh	# enh=1/0: Trackenhancing on/off
"FN%d\x03" %ori		# ori=1/0: Landscape/Portrait
"FE0\x03"		# ??
"TB71\x03"		# ??
			# Response "    0,    0\x03"
"FA\x03"     		# begin page definition
"FU%d,%d\x03" % (w,h)	# h,w page dimensions without top/left margin. Needed to start left.
"FM1\x03"		# ??
--------------------------------- if registraion marks
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
