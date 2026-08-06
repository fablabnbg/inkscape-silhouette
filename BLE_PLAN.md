# Bluetooth Low Energy plan

## Goal

Add Bluetooth Low Energy as a third transport for the existing Graphtec driver,
alongside USB and Bluetooth Classic/RFCOMM. Geometry generation, cutter setup,
model tables, and the Graphtec command language remain shared.

The BLE protocol research lives in `/Users/lexa/silhouette-test`. Its probes
establish the vendor GATT service, characteristic roles, initialization
handshake, 20-byte payload size, and name-based discovery required by macOS.
Those probes are evidence and test fixtures, not production modules to import.
Characteristic roles and the handshake were also cross-checked against
[`bob-takuya/cameo-cut`](https://github.com/bob-takuya/cameo-cut) (MIT).

## Implementation status

Implemented locally:

- Synchronous BLE transport with discovery, handshake, acknowledged chunking,
  buffered reads, timeout handling, and deterministic shutdown.
- `SilhouetteCameo` BLE selection and firmware-based model detection.
- Inkscape/CLI connection selection, BLE name and identifier fields, and an
  intentionally unfiltered scan mode for transport testing.
- macOS installer support for `bleak` and its CoreBluetooth dependencies.
- Fake-stack BLE transport and integration tests.

Still pending:

- Real cutter connection and hardware verification from Inkscape on macOS.
- Connection retry policy beyond ATT backpressure, final user documentation,
  and broader device tests.

Verified on macOS with Inkscape 1.4.4:

- macOS requested Bluetooth permission on the first scan.
- The Inkscape extension completed an unfiltered BLE scan and displayed nearby
  devices without crashing.

## Known GATT protocol

- Vendor service: `e2088282-4fde-42f9-bb22-6ec3c7ed8f91`
- Command writes: `6d92661d-f429-4d67-929b-28e7a9780912`
- Reply indications: `8dcf199a-30e7-4bd4-beb6-beb57dca866c`
- Second indication/control channel: `61490654-b5b4-458c-a867-9e15bc1471e0`
- Subscribe to both indication characteristics before sending commands.
- Initialize by writing `ESC+EOT` (`1b 04`) to all three characteristics with
  an acknowledged GATT write.
- Send normal ETX-terminated Graphtec commands to the command characteristic.
- Split the byte stream into 20-byte chunks and use acknowledged writes
  (`response=True`). Do not depend on write-without-response.

## Phase 0: verify assumptions without motion

Before depending on a specific package combination, record the exact Python,
`bleak`, and PyObjC versions used for each test.

- Test the Python environment used by Inkscape, not only system Python.
- Verify discovery, connection, status, firmware, and cutter tool setup.
- Test the real tool query, `ESC+NAK` (`1b 15`). The research probe currently
  labels `ESC+EOT` (`1b 04`) as the tool query, but that is the initialization
  command used by `Graphtec.py`.
- Correct references that call Python 3.12.3 a `bleak` version.
- Verify a complete macOS job from macOS itself. The current research notes say
  that all physical cuts were initiated from Linux, even though the reusable
  probe is named `mac_ble_cut.py`.

## Phase 1: synchronous BLE transport

Add a `BLETransport` subclass of `Transport` with lazy `bleak` imports.

- Run an asyncio event loop in a dedicated background thread.
- Expose the existing synchronous `write_bytes`, `read_bytes`, and `close`
  interface to `Graphtec.py`.
- Discover by advertised name. macOS CoreBluetooth does not expose a portable
  MAC address; its identifier is opaque and local to one Mac.
- Permit an identifier as an optional platform-local fallback.
- Reject ambiguous discovery rather than selecting an arbitrary cutter.
- Subscribe and perform the three-characteristic initialization handshake.
- Serialize outgoing writes and split them into acknowledged 20-byte chunks.
- Buffer indication data behind a condition variable and preserve reply order.
- Translate async timeouts and disconnects into normal transport exceptions.
- Make disconnect and event-loop shutdown reliable and idempotent.
- Keep `bleak` optional so USB and RFCOMM installations continue to work.

## Phase 2: Graphtec integration

Extend `SilhouetteCameo` with BLE-specific selection without changing the
existing `bluetooth_addr` and `bluetooth_channel` behavior.

- Select USB, Bluetooth Classic, or BLE explicitly.
- Accept an advertised BLE name and optional platform-local identifier.
- Reuse `_match_bluetooth_hardware()` for advertised names and firmware.
- Reuse firmware-based model detection after connecting.
- Close the BLE link immediately when connection or identification fails.
- Add bounded retry behavior for transient scan/connect failures.

## Phase 3: Inkscape UI and CLI

Replace the MAC-only Bluetooth workflow with:

- Connection type: USB, Bluetooth Classic, or Bluetooth Low Energy.
- Optional BLE device name.
- Scan-and-report diagnostics.
- Automatic selection when exactly one supported cutter is found.
- A clear ambiguity error when multiple supported cutters are found.

Keep existing Bluetooth Classic command-line arguments backward compatible.
Do not ask macOS users for a BLE MAC address.

## Phase 4: macOS permission strategy

CoreBluetooth is protected by macOS TCC. The current Inkscape 1.4.4 application
does not declare `NSBluetoothAlwaysUsageDescription`, so its extension process
may be terminated on first CoreBluetooth access before Python can report an
error.

Preferred production path:

1. Ask Inkscape to add `NSBluetoothAlwaysUsageDescription` to its macOS bundle.
2. Detect the missing declaration before importing `bleak` and provide useful
   setup guidance where detection is possible.
3. Use a locally modified/re-signed Inkscape bundle only for development.
4. If Inkscape cannot add the declaration, package a signed BLE helper app and
   communicate with it over local IPC instead of modifying the host app.

## Phase 5: dependencies and installation

- Add an optional BLE requirements file or installation extra.
- Install a tested `bleak` version and its PyObjC dependencies when BLE is
  requested on macOS.
- Do not turn BLE into a mandatory dependency for USB-only users or distro
  packages.
- Document that the BLE GATT path does not require Bluetooth Classic pairing.

## Automated verification

- Fake scanner/client tests for discovery and ambiguity handling.
- Handshake ordering and characteristic UUID tests.
- Acknowledged 20-byte chunking, including splits in the middle of commands.
- Notification buffering, fragmented replies, timeouts, and disconnects.
- Idempotent close and background-loop shutdown.
- End-to-end fake Graphtec firmware/model/status queries over BLE.
- Existing USB and RFCOMM regression suites remain green.

## Hardware acceptance

1. Scan from Inkscape on macOS without entering a MAC address.
2. Query status, firmware, and `ESC+NAK` without motion.
3. Draw a 40 mm square with a pen.
4. Send a real SVG through the complete Inkscape extension.
5. Close the connection and immediately run a second job.
6. Verify Cameo 5 Alpha and, when available, Cameo 4.
7. Confirm USB and Bluetooth Classic still work unchanged.

## Delivery sequence

1. BLE transport and unit tests.
2. Graphtec/CLI integration.
3. Inkscape UI, installer, documentation, and macOS TCC support.
