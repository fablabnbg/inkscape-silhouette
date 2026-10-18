# Experimental Windows USBPRINT transport

The optional `usbprint` connection uses the CAMEO 4's existing Windows printer
driver. It does not require installing a libusb driver through Zadig. The default
`usb` connection and other transports are unchanged.

Contributed by [Eron Greco (@eronGreco)](https://github.com/eronGreco).
The transport uses persistent input and overlapped Win32 I/O.
**This Inkscape integration has not yet been physically validated.** Only
VID `0B4D` / PID `1137` is selected. Other cutter models are not enabled by
overriding the model name.

## Trying the transport

Use a current Windows version with `pnputil /enum-interfaces` support, the normal
USB Printing Support driver, and exactly one connected CAMEO 4. Close Silhouette
Studio and any other cutter application: access is exclusive. If you replaced
the printer driver with Zadig, restore it first using the existing Windows
installation instructions. Keep the extension's Python dependencies installed.

In the extension's **Bluetooth** tab, select **Windows USBPRINT (CAMEO 4,
experimental)** in **Connection type**. The existing tab name is retained to
avoid unrelated layout changes. Alternatively:

```text
python sendto_silhouette.py --connection_type=usbprint --dry_run=True --preview=False examples/testcut_square_triangle.svg
```

The existing `dry_run` option still permits queries to an attached device, but
does not send cutting commands. Without a device, it uses the existing simulated
query responses. Removing `--dry_run=True` sends a real job; use the normal
material, tool and registration options rather than copying a fixed geometry.

## I/O behavior

One background reader keeps input pending. Short diagnostic reads time out at
the response queue without cancelling native input. Input is assembled up to
ETX, preserving padding and retaining coalesced responses or partial frames.
Reads respect the requested byte limit.

Writes check their transferred byte count. A write failure poisons the session
and is not classified as retryable `ETIMEDOUT`: delivery may be uncertain.
Native buffers and handles stay alive until completion, including after
`CancelIoEx`. Draining a cancelled write may extend its nominal timeout if the
Windows driver delays cancellation completion. Closing cancels pending I/O;
the device handle is released only after outstanding operations finish.
No recovery command or automatic cut retransmission is introduced.

## Validation still needed

Unit tests use simulated I/O and Win32 calls; they do not prove USB driver or
hardware behavior. Before declaring this transport supported, record an
Inkscape status/firmware exchange, a pen job, registration alignment, pause and
cancel recovery, cable removal during pending I/O, and repeated open/close on
a physical CAMEO 4. No Inkscape hardware job was sent while preparing this PR.
