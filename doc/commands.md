FROM: https://github.com/fablabnbg/inkscape-silhouette/issues/72#issue-357943739

Just an FYI:

I've been talking with the Silhouette America support people, and the development team is "exploring development of an official SDK for general release".

The idea is that we would finally have real official documentation on the protocol.  All I had asked for was a 'cheat sheet' of the commands, so that we could make some progress on updating the export functions.

In the mean time, here's what I've come up with so far by sniffing the protocol:

# Table of Contents

1.  [Commands for Silhouette Cameo 3](#org368d528)
2.  [Units](#org44c9db7)
3.  [Examples](#orgbe65902)
    1.  [Initialization (US Letter, Portrait)](#org910d281)
    2.  [Initialize Autoblade In Tool 1](#org6925a25)
    3.  [Initialize Ratchet Blade in Tool 2](#org6c1d32c)
    4.  [End Sequence](#orged666d2)
    5.  [Status (Ready)](#org12ecad4)
    6.  [Status (Moving)](#orgff234cc)
    7.  [Status (Pause)](#orgb18a6a6)
    8.  [Status (Cancel)](#org6022836)
    9.  [Startup Sequence From Power Up](#orgab63b55)



<a id="org368d528"></a>

# Commands for Silhouette Cameo 3

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">KEY</th>
<th scope="col" class="org-left">Description</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">00 - ff</td>
<td class="org-left">Two hexadecimal digits, unquoted, are sent as is.</td>
</tr>


<tr>
<td class="org-left">'&#x2026;'</td>
<td class="org-left">Text inside quotes is a character string sent verbatim.</td>
</tr>


<tr>
<td class="org-left">xxx</td>
<td class="org-left">X coordinate.<sup><a id="fnr.1" class="footref" href="#fn.1">1</a></sup></td>
</tr>


<tr>
<td class="org-left">yyy</td>
<td class="org-left">Y coordinate.<sup><a id="fnr.1.100" class="footref" href="#fn.1">1</a></sup></td>
</tr>


<tr>
<td class="org-left">n</td>
<td class="org-left">Pen number</td>
</tr>


<tr>
<td class="org-left">d</td>
<td class="org-left">Auto Blade Depth</td>
</tr>


<tr>
<td class="org-left">s</td>
<td class="org-left">Speed</td>
</tr>


<tr>
<td class="org-left">o</td>
<td class="org-left">Blade Offset</td>
</tr>


<tr>
<td class="org-left">z</td>
<td class="org-left">unknown</td>
</tr>


<tr>
<td class="org-left">f</td>
<td class="org-left">Force (0-33)</td>
</tr>


<tr>
<td class="org-left">nnn</td>
<td class="org-left">First unknown purpose number.<sup><a id="fnr.1.100" class="footref" href="#fn.1">1</a></sup></td>
</tr>


<tr>
<td class="org-left">mmm</td>
<td class="org-left">Second unknown purpose number.<sup><a id="fnr.1.100" class="footref" href="#fn.1">1</a></sup></td>
</tr>


<tr>
<td class="org-left">&#xa0;</td>
<td class="org-left">&#xa0;</td>
</tr>
</tbody>
</table>

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />

<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">Category</th>
<th scope="col" class="org-left">Command Format</th>
<th scope="col" class="org-left">Response Format</th>
<th scope="col" class="org-left">Description</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Action</td>
<td class="org-left">'BE1' &#x2026; 03</td>
<td class="org-left">n/a</td>
<td class="org-left">New drawing command.<sup><a id="fnr.2" class="footref" href="#fn.2">2</a></sup></td>
</tr>


<tr>
<td class="org-left">Action</td>
<td class="org-left">'BE2' &#x2026; 03</td>
<td class="org-left">n/a</td>
<td class="org-left">New drawing command.</td>
</tr>


<tr>
<td class="org-left">Action</td>
<td class="org-left">'M' xxx ',' yyy 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Move selected pen to coordinates.</td>
</tr>


<tr>
<td class="org-left">Auto Blade</td>
<td class="org-left">'FY' n 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Reset Auto Blade<sup><a id="fnr.3" class="footref" href="#fn.3">3</a></sup></td>
</tr>


<tr>
<td class="org-left">Auto Blade</td>
<td class="org-left">'TF' d ',' n 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Set Auto Blade<sup><a id="fnr.4" class="footref" href="#fn.4">4</a></sup></td>
</tr>


<tr>
<td class="org-left">Get Info</td>
<td class="org-left">'FA' 03</td>
<td class="org-left">nnnnn ',' mmmmm     03<sup><a id="fnr.5" class="footref" href="#fn.5">5</a></sup></td>
<td class="org-left">Unknown: 2 five digit numbers.</td>
</tr>


<tr>
<td class="org-left">Get Info</td>
<td class="org-left">'FG' 03</td>
<td class="org-left">'CAMEO 3 V1.50    ' 03</td>
<td class="org-left">Get Version: 17 Chars</td>
</tr>


<tr>
<td class="org-left">Get Info</td>
<td class="org-left">'FQ0' 03</td>
<td class="org-left">nnnnn               03</td>
<td class="org-left">Unknown: 1 five digit number.  Maybe last speed set?</td>
</tr>


<tr>
<td class="org-left">Get Info</td>
<td class="org-left">'FQ2' 03</td>
<td class="org-left">nnnnn               03</td>
<td class="org-left">Unknown: 1 five digit number.  Maybe last blade offset?</td>
</tr>


<tr>
<td class="org-left">Get Info</td>
<td class="org-left">'TB71' 03</td>
<td class="org-left">nnnnn ',' mmmmm     03<sup><a id="fnr.5.100" class="footref" href="#fn.5">5</a></sup></td>
<td class="org-left">Unknown: 2 five digit numbers.</td>
</tr>


<tr>
<td class="org-left">Get Info</td>
<td class="org-left">'U' 03</td>
<td class="org-left">xxxxxx ',' yyyyyy   03</td>
<td class="org-left">Get Lower Right Coordinates: 2 six digit numbers.</td>
</tr>


<tr>
<td class="org-left">Get Info</td>
<td class="org-left">'[' 03</td>
<td class="org-left">xxxxxx ',' yyyyyy   03</td>
<td class="org-left">Get Upper Left Coords: 2 six digit numbers.</td>
</tr>


<tr>
<td class="org-left">Set Config</td>
<td class="org-left">'!' s ',' n 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Set Speed to 5 for Pen #1</td>
</tr>


<tr>
<td class="org-left">Set Config</td>
<td class="org-left">'FC' o ',' z ',' n 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Set Cutting Offset to 18 for Pen #1</td>
</tr>


<tr>
<td class="org-left">Set Config</td>
<td class="org-left">'FX' f ',' n 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Set Force to 33 for Pen #1</td>
</tr>


<tr>
<td class="org-left">Set Config</td>
<td class="org-left">'Z,4288' 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Set Lower Right Boundary</td>
</tr>


<tr>
<td class="org-left">Set Config</td>
<td class="org-left">'\\30,30' 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Set Upper Left Boundary</td>
</tr>


<tr>
<td class="org-left">Set Pen</td>
<td class="org-left">'J' n 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Select Pen #N<sup><a id="fnr.6" class="footref" href="#fn.6">6</a></sup></td>
</tr>


<tr>
<td class="org-left">Status</td>
<td class="org-left">1b 05</td>
<td class="org-left">30 03</td>
<td class="org-left">Status?  Ready</td>
</tr>


<tr>
<td class="org-left">Status</td>
<td class="org-left">1b 05</td>
<td class="org-left">31 03</td>
<td class="org-left">Status?  Moving</td>
</tr>


<tr>
<td class="org-left">Status</td>
<td class="org-left">1b 05</td>
<td class="org-left">32 03</td>
<td class="org-left">Status?  ???</td>
</tr>


<tr>
<td class="org-left">Status</td>
<td class="org-left">1b 05</td>
<td class="org-left">33 03</td>
<td class="org-left">Status?  Paused</td>
</tr>


<tr>
<td class="org-left">Unknown</td>
<td class="org-left">'FN0' 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Unknown</td>
</tr>


<tr>
<td class="org-left">Unknown</td>
<td class="org-left">'L0' 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Line type?<sup><a id="fnr.7" class="footref" href="#fn.7">7</a></sup></td>
</tr>


<tr>
<td class="org-left">Unknown</td>
<td class="org-left">'TB50,0' 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Unknown</td>
</tr>


<tr>
<td class="org-left">Unknown</td>
<td class="org-left">'TG1' 03</td>
<td class="org-left">n/a</td>
<td class="org-left">Unknown</td>
</tr>
</tbody>
</table>


<a id="org44c9db7"></a>

# Units

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<tbody>
<tr>
<td class="org-left">um</td>
<td class="org-left">micrometer</td>
<td class="org-left">&#xa0;</td>
</tr>


<tr>
<td class="org-left">SU</td>
<td class="org-left">Silhouette Unit</td>
<td class="org-left">All command coordinates are in Silhouette Units</td>
</tr>


<tr>
<td class="org-left">in</td>
<td class="org-left">Inches</td>
<td class="org-left">&#xa0;</td>
</tr>
</tbody>
</table>

     50   um =    1 SU
    508   SU =    1 in
      8.5 in = 4318 SU
     11   in = 5588 SU


<a id="orgbe65902"></a>

# Examples

All of the examples are using US Letter size paper (8.5 x 11 in OR 4318 x 5588 SU).

All command strings end with ETX (0x03) unless otherwise specified.

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">Occurance</th>
<th scope="col" class="org-left">Meaning</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Not First</td>
<td class="org-left">This command does not appear on the first such sequence, but does appear on all subsequent sequences of the same type.</td>
</tr>


<tr>
<td class="org-left">All</td>
<td class="org-left">This command appears on all squences of this type.</td>
</tr>


<tr>
<td class="org-left">First</td>
<td class="org-left">This command appears only on the first such sequence, and is absent from all subsequent sequences of the same type.</td>
</tr>
</tbody>
</table>


<a id="org910d281"></a>

## Initialization (US Letter, Portrait)

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<tbody>
<tr>
<td class="org-left">TG1</td>
<td class="org-left">Unknown</td>
</tr>


<tr>
<td class="org-left">FN0</td>
<td class="org-left">Unknown</td>
</tr>


<tr>
<td class="org-left">TB50,0</td>
<td class="org-left">Unknown</td>
</tr>


<tr>
<td class="org-left">\\30,30</td>
<td class="org-left">Write Upper Left - Sets the upper left to 1.5 mm from the true upper left corner.</td>
</tr>


<tr>
<td class="org-left">Z5558,4288</td>
<td class="org-left">Write Lower Right - Sets the lowr right 1.5mm from the true lower right.</td>
</tr>
</tbody>
</table>


<a id="org6925a25"></a>

## Initialize Autoblade In Tool 1

Since an autoblade can only ever be in tool slot one, all pen numbers are always one.

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">Command</th>
<th scope="col" class="org-left">Occurance</th>
<th scope="col" class="org-left">Meaning/Notes</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">L0</td>
<td class="org-left">Not First</td>
<td class="org-left">Unknown<sup><a id="fnr.8" class="footref" href="#fn.8">8</a></sup></td>
</tr>


<tr>
<td class="org-left">J1</td>
<td class="org-left">All</td>
<td class="org-left">Pen Select</td>
</tr>


<tr>
<td class="org-left">FX33,1</td>
<td class="org-left">All</td>
<td class="org-left">Set pen one force to 33.</td>
</tr>


<tr>
<td class="org-left">!5,1</td>
<td class="org-left">All</td>
<td class="org-left">Set pen one speed to 5.</td>
</tr>


<tr>
<td class="org-left">FC0,1,1</td>
<td class="org-left">First</td>
<td class="org-left">Set pen one cutter offset to 0,1.</td>
</tr>


<tr>
<td class="org-left">FC18,1,1</td>
<td class="org-left">Not First</td>
<td class="org-left">Set pen one cutter offset to 18,1.</td>
</tr>


<tr>
<td class="org-left">FE0,1</td>
<td class="org-left">All</td>
<td class="org-left">Unknown</td>
</tr>


<tr>
<td class="org-left">FF1,0,1</td>
<td class="org-left">First</td>
<td class="org-left">Only on first autoblade initalization: Unknown</td>
</tr>


<tr>
<td class="org-left">FF1,1,1</td>
<td class="org-left">All</td>
<td class="org-left">On all autoblade initialization: Unknown</td>
</tr>


<tr>
<td class="org-left">FC18,1,1</td>
<td class="org-left">All</td>
<td class="org-left">Set pen one cutter offset to 0.9mm x 50 um.</td>
</tr>


<tr>
<td class="org-left">FY1</td>
<td class="org-left">All</td>
<td class="org-left">Reset Blade to depth 10<sup><a id="fnr.9" class="footref" href="#fn.9">9</a></sup>.</td>
</tr>


<tr>
<td class="org-left">TF1,1</td>
<td class="org-left">All</td>
<td class="org-left">Set pen one to depth 1<sup><a id="fnr.10" class="footref" href="#fn.10">10</a></sup>.</td>
</tr>
</tbody>
</table>

The initialization sequence is followed by a 'M' (move) command, then
by a 'BE[12]' command sequence that supposedly does the cutting.


<a id="org6c1d32c"></a>

## Initialize Ratchet Blade in Tool 2

This initialization sequence was after 6 autoblade initialization
sequences.

TODO Run a capture of only ratchet blade initializations.

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<tbody>
<tr>
<td class="org-left">L0</td>
<td class="org-left">Unknown<sup><a id="fnr.8.100" class="footref" href="#fn.8">8</a></sup></td>
</tr>


<tr>
<td class="org-left">J2</td>
<td class="org-left">Pen Select.</td>
</tr>


<tr>
<td class="org-left">!4,2</td>
<td class="org-left">Set pen two speed to 4.<sup><a id="fnr.11" class="footref" href="#fn.11">11</a></sup></td>
</tr>


<tr>
<td class="org-left">FX20,2</td>
<td class="org-left">Set pen two force to 20.</td>
</tr>


<tr>
<td class="org-left">FE0,2</td>
<td class="org-left">Unknown</td>
</tr>


<tr>
<td class="org-left">FF1,0,2</td>
<td class="org-left">Unknown</td>
</tr>


<tr>
<td class="org-left">FF1,1,2</td>
<td class="org-left">Unknown</td>
</tr>


<tr>
<td class="org-left">FC0,1,2</td>
<td class="org-left">Set pen two cutter offset to 0.0mm x 50 um.</td>
</tr>


<tr>
<td class="org-left">FC18,1,2</td>
<td class="org-left">Set pen two cutter offset to 0.9mm x 50 um.</td>
</tr>
</tbody>
</table>

As with the autoblade, the initialization sequence is followed by an
'M' (move) command, then by a 'BE[12]' command sequence that
supposedly does the cutting.


<a id="orged666d2"></a>

## End Sequence

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<tbody>
<tr>
<td class="org-left">L0</td>
<td class="org-left">Unknown<sup><a id="fnr.8.100" class="footref" href="#fn.8">8</a></sup></td>
</tr>


<tr>
<td class="org-left">\\0,0</td>
<td class="org-left">Write Upper Left : reset the upper left to zero,zero so that you can move to it.</td>
</tr>


<tr>
<td class="org-left">M0,0</td>
<td class="org-left">Move to zero zero.</td>
</tr>


<tr>
<td class="org-left">J0</td>
<td class="org-left">Select no pen.</td>
</tr>


<tr>
<td class="org-left">FN0</td>
<td class="org-left">Unknown</td>
</tr>


<tr>
<td class="org-left">TB50,0</td>
<td class="org-left">Unknown</td>
</tr>
</tbody>
</table>


<a id="org12ecad4"></a>

## Status (Ready)

Normal exchange when the device is ready.

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<tbody>
<tr>
<td class="org-left">0x1b 0x05</td>
<td class="org-left">&#xa0;</td>
<td class="org-left">Query Status</td>
</tr>


<tr>
<td class="org-left">&#xa0;</td>
<td class="org-left">0x30 0x03</td>
<td class="org-left">Ready</td>
</tr>
</tbody>
</table>


<a id="orgff234cc"></a>

## Status (Moving)

Normal exchange when the device is executing the last command set given.

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<tbody>
<tr>
<td class="org-left">0x1b 0x05</td>
<td class="org-left">&#xa0;</td>
<td class="org-left">Query Status</td>
</tr>


<tr>
<td class="org-left">&#xa0;</td>
<td class="org-left">0x31 0x03</td>
<td class="org-left">Moving</td>
</tr>
</tbody>
</table>


<a id="orgb18a6a6"></a>

## Status (Pause)

The Pause button has been pushed on the device, hold all subsequent commands.

I believe that the device completes the last set of commands sent
before it acts on the pause button.

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<tbody>
<tr>
<td class="org-left">0x1b 0x05</td>
<td class="org-left">&#xa0;</td>
<td class="org-left">Query Status</td>
</tr>


<tr>
<td class="org-left">&#xa0;</td>
<td class="org-left">0x33 0x03</td>
<td class="org-left">Paused</td>
</tr>
</tbody>
</table>


<a id="org6022836"></a>

## Status (Cancel)

The cancel button has been pushed on the device.  Since the cancel
button is only available if the device has been paused, this triggers
an immediate reset sequence followed by a sequence that resembles the
normal startup sequence; but which contains &#x2026; errors &#x2026;  For
example, the upper left coordinates are reported as 0,0 but the lower
right coordinates are reported as less than a US Letter portrait
oriented page.


<a id="orgab63b55"></a>

## Startup Sequence From Power Up

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<tbody>
<tr>
<td class="org-left">0x1b 0x05</td>
<td class="org-left">&#xa0;</td>
<td class="org-left">Query Status</td>
</tr>


<tr>
<td class="org-left">&#xa0;</td>
<td class="org-left">0x34 0x03</td>
<td class="org-left">Cancel</td>
</tr>
</tbody>
</table>


# Footnotes

<sup><a id="fn.1" href="#fnr.1">1</a></sup> If there are three characters, the format is no padding.  If
there are more than three characters, then the format is fixed with,
padded on the left with blanks.

<sup><a id="fn.2" href="#fnr.2">2</a></sup> These new commands use nothing but binary to express the
drawing/cutting desired.  I have, as yet, been unable to decypher
them.  The old drawing commands appear to still work, so it's not
essential that these be decyphered.

<sup><a id="fn.3" href="#fnr.3">3</a></sup> The CAMEO 3 moves the selected pen to a special spot (A) in the
machine, clicks it 10 times, then moves to a second special spot (B)
and clicks once.  I believe that this resets the Auto Blade to 1.

<sup><a id="fn.4" href="#fnr.4">4</a></sup> After "Reset Auto Blade", the CAMEO 3 moves the selected pen to
a special spot (A) and clicks it 10 - N times, where N is the first
number in the command.

<sup><a id="fn.5" href="#fnr.5">5</a></sup> The response seems to always be 0,0.

<sup><a id="fn.6" href="#fnr.6">6</a></sup> Observed on Cameo 3, 0=no pen, 1=first pen, 2=second pen.

<sup><a id="fn.7" href="#fnr.7">7</a></sup> Older documentation claims that this is line type.  I don't
think that's what it means for Cameo 3.  Unless "line type" means
something other than what you draw with a pen.  Cameo 3 does dashed
lines by sending pairs of move and draw commands.

<sup><a id="fn.8" href="#fnr.8">8</a></sup> This is absent on the first initialization of the autoblade,
but present on all subsequent blade initializations, including the
ratchet blade.

<sup><a id="fn.9" href="#fnr.9">9</a></sup> The Cameo 3 always does ten clicks with an autoblade in one
position, followed by another click in a different position.  This
resets the blade to 10.

<sup><a id="fn.10" href="#fnr.10">10</a></sup> After resetting the autoblade, the Cameo 3 always does 10 - N
clicks to set the depth to N.  This means the reset must guarantee
that the autoblade is set to 10, since each subsequent click reduces
the depth by one.

<sup><a id="fn.11" href="#fnr.11">11</a></sup> Note that speed and force are reversed compared to autoblade.


