# (c) 2026 inkscape-silhouette contributors
#
# Distribute under GPLv2 or ask.
#
# Transport abstraction for inkscape-silhouette.
#
# Separates the physical connection to a cutter (USB, Bluetooth, ...) from the
# Graphtec command protocol implemented in Graphtec.py. The protocol layer
# (SilhouetteCameo) only needs to push bytes down and read bytes back; the
# details of *how* those bytes travel live in the Transport subclasses below.

import re
import socket
import subprocess
import sys


class Transport:
  """Abstract connection to a Silhouette cutter.

  Concrete subclasses implement the low level byte transfer. Everything above
  (the Graphtec command protocol) is transport agnostic and talks to a
  Transport exclusively through write_bytes()/read_bytes().
  """

  # Human readable description of where the device sits, used for logging.
  location = "unknown"

  # Exception types raised by read_bytes()/write_bytes() on a timeout or a
  # transient I/O error. The protocol layer catches these when polling.
  timeout_exceptions = (OSError,)

  def write_bytes(self, data, timeout):
    """Write a chunk of bytes. Returns the number of bytes actually written.

    timeout is given in milliseconds (to match the pyusb convention)."""
    raise NotImplementedError

  def read_bytes(self, size, timeout):
    """Read up to size bytes and return them as bytes/bytearray.

    timeout is given in milliseconds."""
    raise NotImplementedError

  def reset(self):
    """Reset the connection, if the transport supports it. Default: no-op."""
    pass

  def close(self):
    """Release the connection. Default: no-op."""
    pass


class USBTransport(Transport):
  """USB connection via pyusb (Linux/Windows) or libusb1 (macOS).

  The raw device object is discovered by Graphtec.SilhouetteCameo (which owns
  the platform specific probing and the USB id tables) and handed to us here.
  We only encapsulate the bulk read/write on the fixed endpoints.
  """

  ENDPOINT_WRITE = 0x01
  ENDPOINT_READ = 0x82

  def __init__(self, dev, need_interface=False):
    self.dev = dev
    # need_interface: some old versions of usb.core require an explicit
    # interface= keyword; harmful on others. Kept for compatibility.
    self.need_interface = need_interface

    try:
      bus = dev.bus
    except Exception:
      bus = -1
    try:
      address = dev.address
    except Exception:
      address = -1
    self.bus = bus
    self.address = address
    self.location = "usb bus=%d addr=%d" % (bus, address)

  def write_bytes(self, data, timeout):
    endpoint = self.ENDPOINT_WRITE
    if self.need_interface:
      try:
        return self.dev.write(endpoint, data, interface=0, timeout=timeout)
      except AttributeError:
        return self.dev.bulkWrite(endpoint, data, interface=0, timeout=timeout)
    else:
      try:
        return self.dev.write(endpoint, data, timeout=timeout)
      except AttributeError:
        return self.dev.bulkWrite(endpoint, data, timeout=timeout)

  def read_bytes(self, size, timeout):
    endpoint = self.ENDPOINT_READ
    if self.need_interface:
      try:
        return self.dev.read(endpoint, size, timeout=timeout, interface=0)
      except AttributeError:
        return self.dev.bulkRead(endpoint, size, timeout=timeout, interface=0)
    else:
      try:
        return self.dev.read(endpoint, size, timeout=timeout)
      except AttributeError:
        return self.dev.bulkRead(endpoint, size, timeout=timeout)

  def reset(self):
    self.dev.reset()

  def close(self):
    # pyusb releases the device when it is garbage collected; historically
    # this driver never explicitly closed it, so keep that behaviour.
    pass


class BluetoothTransport(Transport):
  """Bluetooth connection over an RFCOMM serial port.

  BT enabled cutters expose the very same Graphtec command protocol as over
  USB, so once the socket is connected the protocol layer treats it exactly
  like a USB device. The only differences are that there are no bulk endpoints
  (we simply send/recv on the stream) and that timeouts are expressed in
  seconds rather than milliseconds.
  """

  # RFCOMM channel used by the cutters. Channel 1 works for all known models.
  DEFAULT_CHANNEL = 1

  # socket.timeout is raised on read/write timeouts; it is a subclass of
  # OSError but we list it explicitly for clarity.
  timeout_exceptions = (socket.timeout, OSError)

  def __init__(self, sock, address=None, channel=DEFAULT_CHANNEL):
    self.sock = sock
    self.address = address
    self.channel = channel
    self.bus = "bluetooth"
    self.location = "bluetooth %s channel %d" % (address, channel)

  @classmethod
  def is_available(cls):
    """True if this Python build/platform can open Bluetooth RFCOMM sockets."""
    return (hasattr(socket, "AF_BLUETOOTH")
            and hasattr(socket, "BTPROTO_RFCOMM"))

  @classmethod
  def connect(cls, address, channel=None, timeout=None):
    """Open an RFCOMM connection to the cutter at the given MAC address.

    address: bluetooth MAC address string, e.g. "00:1B:41:33:44:55".
    channel: RFCOMM channel (defaults to DEFAULT_CHANNEL).
    timeout: connection timeout in seconds (None: OS default).
    """
    if not cls.is_available():
      raise RuntimeError(
        "Bluetooth is not supported by this Python build/platform "
        "(socket.AF_BLUETOOTH/BTPROTO_RFCOMM missing).")
    if channel is None:
      channel = cls.DEFAULT_CHANNEL
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM,
                         socket.BTPROTO_RFCOMM)
    try:
      if timeout is not None:
        sock.settimeout(timeout)
      sock.connect((address, channel))
    except Exception:
      sock.close()
      raise
    return cls(sock, address=address, channel=channel)

  # ---- Discovery ---------------------------------------------------------
  #
  # Inkscape's static .inx UI cannot populate a dropdown at runtime, so we
  # expose discovery as a helper that the --bluetooth_scan command uses to list
  # cutters and their addresses for the user to choose from explicitly.
  # Discovery is best effort and platform dependent; the cutter must already be
  # paired with the operating system.

  @staticmethod
  def _format_addr(hex12):
    """Turn a bare 12-hex-digit address into colon notation."""
    h = hex12.upper()
    return ":".join(h[i:i + 2] for i in range(0, 12, 2))

  @classmethod
  def discover(cls, timeout=8, name_filter=None):
    """Discover reachable/paired Bluetooth devices.

    Returns a list of (address, name) tuples, sorted by name. Best effort:
    uses the OS list of paired devices (Windows PnP / BlueZ bluetoothctl) and
    falls back to a live PyBluez inquiry if that library is installed. The
    device must be paired with the OS first.

    name_filter, if given, is a predicate on the device name; only devices for
    which it returns true are returned (and only they short-circuit the slow
    live-inquiry fallback). This keeps the transport model agnostic: callers
    that want just Silhouette cutters pass a filter based on the model tables
    in Graphtec, so there is no second list of model names to maintain here.
    """
    def matches(name):
      return True if name_filter is None else bool(name_filter(name))

    platform = sys.platform.lower()
    backends = []
    if platform.startswith("win"):
      backends.append(cls._discover_windows)
    elif platform.startswith("linux"):
      backends.append(cls._discover_linux)
    # Cross-platform live inquiry, only if PyBluez is available.
    backends.append(cls._discover_pybluez)

    seen = {}
    for backend in backends:
      try:
        results = backend(timeout)
      except Exception:
        results = []
      for addr, name in results:
        key = (addr or "").upper()
        if not key:
          continue
        # Keep the first sighting, but upgrade to a named entry if we get one.
        if key not in seen or (not seen[key] and name):
          seen[key] = name
      # A fast paired-device backend already found a matching device: don't pay
      # the multi-second cost of a live inquiry.
      if backend is not cls._discover_pybluez and any(
          matches(n) for n in seen.values()):
        break

    devices = list(seen.items())
    if name_filter is not None:
      devices = [(a, n) for (a, n) in devices if name_filter(n)]
    return sorted(devices, key=lambda d: (d[1] or "", d[0]))

  @staticmethod
  def _run_quiet(args, timeout=30):
    """Run a helper command, returning stdout (empty string on any failure)."""
    kwargs = dict(capture_output=True, text=True, timeout=timeout)
    if sys.platform.lower().startswith("win"):
      # Avoid a console window flashing up inside the Inkscape UI.
      kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
      return subprocess.run(args, **kwargs).stdout or ""
    except Exception:
      return ""

  @classmethod
  def _discover_windows(cls, timeout):
    out = cls._run_quiet([
      "powershell", "-NoProfile", "-Command",
      "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | "
      "ForEach-Object { $_.FriendlyName + '|' + $_.InstanceId }"])
    return cls._parse_windows_pnp(out)

  @classmethod
  def _parse_windows_pnp(cls, text):
    """Parse 'FriendlyName|InstanceId' lines from Get-PnpDevice.

    Only classic (BTHENUM) device nodes carry an RFCOMM-connectable address;
    the BTHLE (Bluetooth Low Energy) nodes advertise a different, non-RFCOMM
    address and are ignored.
    """
    devices = []
    pat = re.compile(r"BTHENUM\\DEV_([0-9A-Fa-f]{12})")
    for line in text.splitlines():
      if "|" not in line:
        continue
      name, instance_id = line.split("|", 1)
      m = pat.search(instance_id)
      if m:
        devices.append((cls._format_addr(m.group(1)), name.strip()))
    return devices

  @classmethod
  def _discover_linux(cls, timeout):
    devices = []
    for args in (["bluetoothctl", "devices"], ["bluetoothctl", "paired-devices"]):
      devices.extend(cls._parse_bluetoothctl(cls._run_quiet(args)))
    return devices

  @classmethod
  def _parse_bluetoothctl(cls, text):
    """Parse 'Device AA:BB:CC:DD:EE:FF Name' lines from bluetoothctl."""
    devices = []
    pat = re.compile(r"^Device\s+([0-9A-Fa-f:]{17})\s+(.*)$")
    for line in text.splitlines():
      m = pat.match(line.strip())
      if m:
        devices.append((m.group(1).upper(), m.group(2).strip()))
    return devices

  @classmethod
  def _discover_pybluez(cls, timeout):
    try:
      import bluetooth  # PyBluez; optional dependency
    except Exception:
      return []
    found = bluetooth.discover_devices(duration=max(1, int(timeout)),
                                       lookup_names=True)
    return [(addr, name) for addr, name in found]

  @staticmethod
  def _timeout_seconds(timeout_ms):
    if timeout_ms is None or timeout_ms <= 0:
      return None
    return timeout_ms / 1000.0

  def write_bytes(self, data, timeout):
    self.sock.settimeout(self._timeout_seconds(timeout))
    # RFCOMM is a reliable stream: sendall pushes the whole chunk or raises.
    self.sock.sendall(data)
    return len(data)

  def read_bytes(self, size, timeout):
    self.sock.settimeout(self._timeout_seconds(timeout))
    return self.sock.recv(size)

  def close(self):
    try:
      self.sock.close()
    except Exception:
      pass
