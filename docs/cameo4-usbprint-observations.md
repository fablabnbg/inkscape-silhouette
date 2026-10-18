# CAMEO 4: Windows USBPRINT observations

These notes supplement [Commands.md](../Commands.md) with CAMEO 4 observations
on Windows USBPRINT access, response framing, and registration.

## Scope

Contributed by [Eron Greco (@eronGreco)](https://github.com/eronGreco).
These observations concern one CAMEO 4 communicating through Windows USBPRINT.
They do not establish Inkscape hardware compatibility, cut accuracy, or support
for other models and firmware. Device-specific timing requirements have not
been established.

## Native Windows access

The device identifies as USB VID `0B4D`, PID `1137`. The backend enumerates the
Windows USBPRINT device-interface class
`{28d78fad-5a12-11d1-ae5b-0000f803a8c2}` and opens the selected interface using
`CreateFileW` with:

* `GENERIC_READ | GENERIC_WRITE`;
* share mode `0` (exclusive access);
* `OPEN_EXISTING`;
* `FILE_FLAG_OVERLAPPED`.

This uses the existing Windows USBPRINT driver, without replacing it through
Zadig. Silhouette Studio and other clients must release the device first.
An interface path can identify an individual device and should be redacted
when sharing logs.

A background reader keeps an overlapped input read pending before commands
are sent. A caller's short response timeout does **not** cancel that input
operation. The application cancels it when closing the session. This distinction
matters when adapting a transport to the driver's short diagnostic reads.

USB transfer boundaries are not response boundaries. The wrapper buffers
fragmented input and separates responses at ETX (`0x03`), retaining trailing
input for the next response. It preserves spaces: `b'    0\x03'` (registration
acknowledgement) must not be normalized to `b'0\x03'` (ready).

For overlapped writes, the data buffer, `OVERLAPPED`, and event must remain
alive until I/O actually completes. Calling `CancelIoEx` alone does not establish
completion. Partial writes and uncertain timeouts must not silently retransmit
a cut: some commands may already have reached the device.

## Registration example

For one A4 landscape layout, the inherited backend uses marks inset by 10 mm,
10 mm arms and 1 mm line thickness, with a 277 mm horizontal and 190 mm vertical
registration span. It sends these two blocks:

```text
TG1<ETX>FN0<ETX>TB50,0<ETX>TB99<ETX>
TB52,2<ETX>TB51,200<ETX>TB53,20<ETX>TB55,1<ETX>TB123,3800,5540,118,118<ETX>TB99<ETX>
```

`<ETX>` denotes one byte, `0x03`. With 20 device units per millimetre,
`3800` and `5540` encode the vertical and horizontal spans. The example's
search origin is 5.9 mm (`118` units), 4.1 mm before the 10 mm mark position.
That origin is a parameter used by this backend, not a correction to upstream's
different search-origin choice. `M` and `D` coordinates use the existing
vertical/horizontal order documented in the driver.

The backend waits 108 ms between the blocks, starts status polling 526 ms after
the second block, polls every 1.015 s, and uses a 35 s registration deadline.
These are inherited timing choices. No experiment established them as minimum
delays or requirements across firmware versions. Do not replace other working
registration geometries with this fixed example.

## Pause and cancel observations

After the interrupted calibration, the application received `b'3\x03'` during
status polling and later `b'4\x03'` at an initial ready check. These are ASCII
digits followed by ETX, not binary values `0x03` and `0x04`.

[Issue #72](https://github.com/fablabnbg/inkscape-silhouette/issues/72) already
describes related pause/cancel responses on CAMEO 3. The CAMEO 4 logs corroborate
additional non-ready responses, but do not establish the exact recovery
semantics of either code. Neither response should be treated as ready or cause
automatic retransmission of the previous cut. Preserve the raw response when
reporting an unknown state.

## Further validation

Useful next evidence would include the firmware response, a sanitized USB trace
of a successful Inkscape session, controlled pause/cancel recovery, cable
removal during pending I/O, and measured print-and-cut alignment. Model support
should be expanded only with device-specific evidence. Material calibration,
nesting, and software line-segment overcut are application workflows that reuse
existing commands; they do not add GPGL instructions.
