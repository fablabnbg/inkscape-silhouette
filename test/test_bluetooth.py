#!/usr/bin/env python3

# Tests for the Bluetooth (RFCOMM) transport and the model detection that lets
# a SilhouetteCameo talk to a cutter over Bluetooth instead of USB.
#
# These tests do not need real hardware (nor a Bluetooth stack): they drive the
# driver through a fake socket that speaks just enough of the Graphtec protocol
# (firmware query "FG" and the ESC-ENQ status request).

import io
import socket
import unittest
from unittest import mock

from silhouette.Transport import BluetoothTransport, Transport
from silhouette.Graphtec import (
    SilhouetteCameo,
    _match_bluetooth_hardware,
    PRODUCT_ID_SILHOUETTE_CAMEO5ALPHA,
    PRODUCT_ID_SILHOUETTE_CAMEO3,
)


class FakeRfcommSocket:
    """Minimal stand-in for an RFCOMM socket speaking the Graphtec protocol."""

    def __init__(self, firmware=b"CAMEO 5 ALPHA V1.02    ", status=b"0"):
        self.firmware = firmware
        self.status = status
        self.buf = b""
        self.sent = []
        self.timeout = None
        self.closed = False

    def settimeout(self, t):
        self.timeout = t

    def sendall(self, data):
        self.sent.append(bytes(data))
        if data == b"FG\x03":                 # firmware version query
            self.buf = self.firmware + b"\x03"
        elif data == b"\x1b\x05":             # ESC ENQ -> status request
            self.buf = self.status + b"\x03"
        else:
            self.buf = b""

    def recv(self, size):
        if not self.buf:
            # Mirror a real socket read timeout with no data pending.
            raise socket.timeout("no data")
        data, self.buf = self.buf[:size], self.buf[size:]
        return data

    def close(self):
        self.closed = True


def make_bt_cameo(firmware=b"CAMEO 5 ALPHA V1.02    ", status=b"0",
                  force_hardware=None):
    """Build a SilhouetteCameo wired to a FakeRfcommSocket."""
    fake = FakeRfcommSocket(firmware=firmware, status=status)
    transport = BluetoothTransport(fake, address="00:11:22:33:44:55")
    with mock.patch.object(BluetoothTransport, "connect",
                           classmethod(lambda cls, addr, ch=None, timeout=None: transport)):
        dev = SilhouetteCameo(log=io.StringIO(),
                              bluetooth_addr="00:11:22:33:44:55",
                              force_hardware=force_hardware)
    return dev, fake


def is_silhouette_name(name):
    """The predicate the Bluetooth scan uses: matches known Silhouette models.

    Deliberately reuses Graphtec's model table (via _match_bluetooth_hardware)
    so there is no second list of device names to keep in sync."""
    return _match_bluetooth_hardware(name) is not None


class MatchBluetoothHardwareTest(unittest.TestCase):
    """The advertised BLE name / FG response resolves to a DEVICE entry."""

    def test_cameo5_alpha_with_firmware_suffix(self):
        hw = _match_bluetooth_hardware("CAMEO 5 ALPHA V1.02")
        self.assertIsNotNone(hw)
        self.assertEqual(hw["product_id"], PRODUCT_ID_SILHOUETTE_CAMEO5ALPHA)

    def test_specificity_ordering(self):
        # "CAMEO 5 ALPHA PLUS" must not be shadowed by "CAMEO 5 ALPHA".
        hw = _match_bluetooth_hardware("CAMEO 5 ALPHA PLUS V1.0")
        self.assertEqual(hw["name"], "Silhouette_Cameo5_Alpha_Plus")

    def test_plain_cameo5(self):
        self.assertEqual(
            _match_bluetooth_hardware("CAMEO 5 V2.1")["name"],
            "Silhouette_Cameo5")

    def test_cameo3_no_space(self):
        self.assertEqual(
            _match_bluetooth_hardware("CAMEO3 V1")["product_id"],
            PRODUCT_ID_SILHOUETTE_CAMEO3)

    def test_case_insensitive(self):
        self.assertEqual(
            _match_bluetooth_hardware("cameo 5 alpha v1.02")["product_id"],
            PRODUCT_ID_SILHOUETTE_CAMEO5ALPHA)

    def test_unknown_returns_none(self):
        self.assertIsNone(_match_bluetooth_hardware("SOME RANDOM DEVICE"))

    def test_empty_returns_none(self):
        self.assertIsNone(_match_bluetooth_hardware(""))
        self.assertIsNone(_match_bluetooth_hardware(None))


class BluetoothTransportTest(unittest.TestCase):
    """The RFCOMM transport's low level byte transfer."""

    def test_is_a_transport(self):
        self.assertTrue(issubclass(BluetoothTransport, Transport))

    def test_write_bytes_uses_sendall(self):
        fake = FakeRfcommSocket()
        t = BluetoothTransport(fake, address="AA:BB")
        n = t.write_bytes(b"HELLO", timeout=5000)
        self.assertEqual(n, len(b"HELLO"))
        self.assertEqual(fake.sent[-1], b"HELLO")
        # timeout is converted from ms to seconds
        self.assertAlmostEqual(fake.timeout, 5.0)

    def test_read_bytes_returns_recv(self):
        fake = FakeRfcommSocket()
        t = BluetoothTransport(fake, address="AA:BB")
        fake.sendall(b"FG\x03")
        data = t.read_bytes(64, timeout=1000)
        self.assertEqual(data, b"CAMEO 5 ALPHA V1.02    \x03")
        self.assertAlmostEqual(fake.timeout, 1.0)

    def test_zero_timeout_is_blocking(self):
        fake = FakeRfcommSocket()
        t = BluetoothTransport(fake, address="AA:BB")
        t.write_bytes(b"x", timeout=0)
        self.assertIsNone(fake.timeout)

    def test_close(self):
        fake = FakeRfcommSocket()
        t = BluetoothTransport(fake, address="AA:BB")
        t.close()
        self.assertTrue(fake.closed)

    def test_location_string(self):
        fake = FakeRfcommSocket()
        t = BluetoothTransport(fake, address="00:1B:41:33:44:55", channel=1)
        self.assertIn("00:1B:41:33:44:55", t.location)

    def test_connect_requires_bluetooth_support(self):
        with mock.patch.object(BluetoothTransport, "is_available",
                               classmethod(lambda cls: False)):
            with self.assertRaises(RuntimeError):
                BluetoothTransport.connect("00:11:22:33:44:55")


class CameoOverBluetoothTest(unittest.TestCase):
    """End to end: a SilhouetteCameo driven over the fake RFCOMM socket."""

    def test_model_detected_from_firmware(self):
        dev, fake = make_bt_cameo()
        self.assertEqual(dev.hardware["name"], "Silhouette_Cameo5_Alpha")
        self.assertEqual(dev.product_id(), PRODUCT_ID_SILHOUETTE_CAMEO5ALPHA)
        self.assertIsInstance(dev.transport, BluetoothTransport)

    def test_status_and_version_over_bt(self):
        dev, fake = make_bt_cameo()
        self.assertEqual(dev.status(), "ready")
        # get_version returns the raw firmware string (padding preserved).
        self.assertEqual(dev.get_version().strip(), "CAMEO 5 ALPHA V1.02")
        # The firmware query really went out over the socket.
        self.assertIn(b"FG\x03", fake.sent)

    def test_force_hardware_overrides_detection(self):
        dev, fake = make_bt_cameo(force_hardware="Silhouette_Cameo3")
        self.assertEqual(dev.hardware["name"], "Silhouette_Cameo3")

    def test_unknown_model_is_flagged(self):
        dev, fake = make_bt_cameo(firmware=b"MYSTERY CUTTER V9")
        self.assertIn("Unknown Bluetooth", dev.hardware["name"])
        # We still have a working transport; only the model is unresolved.
        self.assertIsInstance(dev.transport, BluetoothTransport)

    def test_dry_run_falls_back_to_dummy_on_connect_failure(self):
        def boom(cls, addr, ch=None, timeout=None):
            raise OSError("no such device")
        with mock.patch.object(BluetoothTransport, "connect",
                               classmethod(boom)):
            dev = SilhouetteCameo(log=io.StringIO(),
                                  dry_run=True,
                                  bluetooth_addr="00:11:22:33:44:55")
        self.assertIsNone(dev.transport)
        self.assertEqual(dev.hardware["name"], "Crashtest Dummy Device")

    def test_connect_failure_without_dry_run_raises(self):
        def boom(cls, addr, ch=None, timeout=None):
            raise OSError("no such device")
        with mock.patch.object(BluetoothTransport, "connect",
                               classmethod(boom)):
            with self.assertRaises(ValueError):
                SilhouetteCameo(log=io.StringIO(),
                                bluetooth_addr="00:11:22:33:44:55")


class DiscoveryParsingTest(unittest.TestCase):
    """Parsing of the platform tools' output and name/address helpers."""

    def test_format_addr(self):
        self.assertEqual(BluetoothTransport._format_addr("001B41334455"),
                         "00:1B:41:33:44:55")

    def test_parse_windows_pnp_keeps_classic_ignores_ble(self):
        # A cutter shows up twice: as a BLE (BTHLE) node and a classic (BTHENUM)
        # node. Only the classic node is RFCOMM-connectable, so only it is kept.
        text = "\r\n".join([
            "CAMEO 5 ALPHA-000000|BTHLE\\DEV_C01B41334455\\B&1111111&0&C01B41334455",
            "CAMEO 5 ALPHA-000000|BTHENUM\\DEV_001B41334455\\B&2222222&0&BLUETOOTHDEVICE_001B41334455",
            "Some Mouse|USB\\VID_1234&PID_5678\\6&abcd",
            "",
        ])
        devices = BluetoothTransport._parse_windows_pnp(text)
        self.assertEqual(devices, [("00:1B:41:33:44:55", "CAMEO 5 ALPHA-000000")])

    def test_parse_bluetoothctl(self):
        text = "\n".join([
            "Device 00:1B:41:33:44:55 CAMEO 5 ALPHA-000000",
            "Device 11:22:33:44:55:66 Generic BT Speaker",
            "garbage line",
        ])
        devices = BluetoothTransport._parse_bluetoothctl(text)
        self.assertIn(("00:1B:41:33:44:55", "CAMEO 5 ALPHA-000000"), devices)
        self.assertIn(("11:22:33:44:55:66", "Generic BT Speaker"), devices)


class CollectDevicesTest(unittest.TestCase):
    """The platform-independent aggregation core of discover().

    Backends are injected directly, so these test the real merge / filter /
    short-circuit logic without any reference to the host platform.
    """

    CUTTER = ("00:1B:41:33:44:55", "CAMEO 5 ALPHA-000000")
    OTHER = ("11:22:33:44:55:66", "Generic BT Speaker")

    @staticmethod
    def backend(devices):
        """A fake discovery backend that returns a fixed device list."""
        return lambda timeout: list(devices)

    def collect(self, paired, inquiry, name_filter=None):
        return BluetoothTransport._collect_devices(paired, inquiry, 8, name_filter)

    def test_name_filter_selects_matching_devices(self):
        paired = [self.backend([self.CUTTER, self.OTHER])]
        # Filtered to Silhouette cutters via Graphtec's model table.
        self.assertEqual(
            self.collect(paired, None, name_filter=is_silhouette_name),
            [self.CUTTER])
        # With no filter, every device is returned.
        self.assertEqual(len(self.collect(paired, None)), 2)

    def test_fast_backend_short_circuits_inquiry(self):
        # A paired backend already found a matching cutter: the slow live
        # inquiry backend must never be invoked.
        inquiry_called = []

        def inquiry(timeout):
            inquiry_called.append(True)
            return []
        self.collect([self.backend([self.CUTTER])], inquiry,
                     name_filter=is_silhouette_name)
        self.assertEqual(inquiry_called, [])

    def test_inquiry_runs_when_no_paired_match(self):
        # Paired backend found only a non-matching device, so we fall back to
        # the live inquiry, which turns up the cutter.
        inquiry_called = []

        def inquiry(timeout):
            inquiry_called.append(True)
            return [self.CUTTER]
        result = self.collect([self.backend([self.OTHER])], inquiry,
                              name_filter=is_silhouette_name)
        self.assertEqual(inquiry_called, [True])
        self.assertEqual(result, [self.CUTTER])

    def test_backend_exception_is_swallowed(self):
        def boom(timeout):
            raise RuntimeError("tool missing")
        result = self.collect([boom], self.backend([self.CUTTER]))
        self.assertEqual(result, [self.CUTTER])

    def test_dedups_by_address_preferring_named(self):
        # The same address arrives twice (different case, one unnamed); the
        # named sighting wins and only one entry remains.
        paired = [self.backend([
            ("00:1B:41:33:44:55", ""),
            ("00:1b:41:33:44:55", "CAMEO 5 ALPHA-000000"),
        ])]
        self.assertEqual(self.collect(paired, None),
                         [("00:1B:41:33:44:55", "CAMEO 5 ALPHA-000000")])


class PairedBackendSelectionTest(unittest.TestCase):
    """_paired_backends() picks the right fast backend for each platform."""

    def _backends_on(self, platform):
        with mock.patch("silhouette.Transport.sys.platform", platform):
            return BluetoothTransport._paired_backends()

    def test_windows_uses_pnp(self):
        self.assertEqual(self._backends_on("win32"),
                         [BluetoothTransport._discover_windows])

    def test_linux_uses_bluetoothctl(self):
        self.assertEqual(self._backends_on("linux"),
                         [BluetoothTransport._discover_linux])

    def test_macos_has_no_paired_backend(self):
        # macOS lacks RFCOMM sockets; only the (optional) live inquiry applies.
        self.assertEqual(self._backends_on("darwin"), [])


if __name__ == "__main__":
    unittest.main()
