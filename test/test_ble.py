"""Tests for the synchronous Bluetooth Low Energy transport.

No Bluetooth adapter or cutter is required. A fake asynchronous bleak stack
drives discovery, notifications, writes, and disconnects while the production
transport exercises its real background event-loop thread.
"""

import io
import sys
import types
import unittest
from typing import ClassVar
from unittest import mock

from silhouette.BLETransport import BLETimeoutError, BLETransport
from silhouette.Graphtec import (
    PRODUCT_ID_SILHOUETTE_CAMEO5ALPHA,
    SilhouetteCameo,
)
from silhouette.Transport import Transport


class FakeDevice:
    def __init__(self, address, name, service_uuids=None):
        self.address = address
        self.name = name
        self.service_uuids = service_uuids or [BLETransport.SERVICE_UUID]


class FakeAdvertisement:
    def __init__(self, service_uuids):
        self.service_uuids = service_uuids


class FakeServices:
    def __init__(self, service_uuids):
        self.service_uuids = {uuid.casefold() for uuid in service_uuids}

    def get_service(self, uuid):
        return object() if uuid.casefold() in self.service_uuids else None


class FakeBleakScanner:
    devices: ClassVar[list] = []
    supports_return_adv = True

    def __init__(self, detection_callback=None, **kwargs):
        del kwargs
        self.detection_callback = detection_callback

    async def __aenter__(self):
        # The fake has no real over-the-air timing, so it delivers every
        # configured device to the callback immediately -- the production
        # code's own grace period (patched to 0 in tests, see setUp) is what
        # then lets _async_scan_for_match stop right away in tests.
        if self.detection_callback is not None:
            for device in self.devices:
                self.detection_callback(
                    device, FakeAdvertisement(device.service_uuids)
                )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    @classmethod
    async def discover(cls, timeout=8, return_adv=False):
        del timeout
        if return_adv:
            if not cls.supports_return_adv:
                raise TypeError("return_adv is not supported")
            return {
                device.address: (
                    device,
                    FakeAdvertisement(device.service_uuids),
                )
                for device in cls.devices
            }
        return list(cls.devices)


class FakeBleakClient:
    instances: ClassVar[list] = []
    # Identifiers a direct (skip-discovery) connect can resolve without a
    # scan -- simulating either a Linux/Windows MAC address (always
    # resolvable) or a macOS CoreBluetooth identifier this "Mac" has
    # already seen before. Anything else fails connect(), forcing the
    # scan-based fallback path.
    known_identifiers: ClassVar[set] = set()

    def __init__(self, device, timeout=None, disconnected_callback=None):
        self.device = device
        self.timeout = timeout
        self.disconnected_callback = disconnected_callback
        self.is_connected = False
        if isinstance(device, str):
            # A bare identifier/address, not a FakeDevice from discovery --
            # this is the skip-discovery direct-connect path.
            self.resolvable = device in self.known_identifiers
            self.services = FakeServices([BLETransport.SERVICE_UUID])
        else:
            self.resolvable = True
            self.services = FakeServices(device.service_uuids)
        self.notifications = {}
        self.writes = []
        self.write_failures_remaining = 0
        self.write_failure = RuntimeError("ATT error: 0x0e")
        self.__class__.instances.append(self)

    async def connect(self):
        if not self.resolvable:
            raise RuntimeError(
                "could not resolve identifier without a preceding scan")
        self.is_connected = True
        return True

    async def start_notify(self, characteristic, callback):
        self.notifications[characteristic] = callback

    async def write_gatt_char(self, characteristic, data, response=False):
        raw = bytes(data)
        self.writes.append((characteristic, raw, response))
        if characteristic == BLETransport.WRITE_UUID and self.write_failures_remaining:
            self.write_failures_remaining -= 1
            raise self.write_failure
        if characteristic != BLETransport.WRITE_UUID:
            return

        callback = self.notifications.get(BLETransport.READ_UUID)
        if callback is None:
            return
        if raw == b"FG\x03":
            callback(characteristic, b"CAMEO 5 ALPHA V1.02    \x03")
        elif raw == b"\x1b\x05":
            callback(characteristic, b"0\x03")
        elif raw == b"\x1b\x15":
            callback(characteristic, b" 2, 0\x03")

    async def disconnect(self):
        was_connected = self.is_connected
        self.is_connected = False
        if was_connected and self.disconnected_callback is not None:
            self.disconnected_callback(self)


class BLEFakeStackMixin:
    def setUp(self):
        FakeBleakScanner.devices = [
            FakeDevice("LOCAL-CAMEO-ID", "CAMEO 5 ALPHA-TEST"),
        ]
        FakeBleakScanner.supports_return_adv = True
        FakeBleakClient.instances = []
        FakeBleakClient.known_identifiers = set()
        fake_bleak = types.ModuleType("bleak")
        fake_bleak.BleakScanner = FakeBleakScanner
        fake_bleak.BleakClient = FakeBleakClient
        self.bleak_patch = mock.patch.dict(sys.modules, {"bleak": fake_bleak})
        self.bleak_patch.start()
        self.settle_patch = mock.patch.object(
            BLETransport, "HANDSHAKE_SETTLE_SECONDS", 0.0
        )
        self.settle_patch.start()
        self.retry_delay_patch = mock.patch.object(
            BLETransport, "WRITE_BACKPRESSURE_DELAY_SECONDS", 0.0
        )
        self.retry_delay_patch.start()
        self.grace_patch = mock.patch.object(
            BLETransport, "DISCOVERY_GRACE_SECONDS", 0.0
        )
        self.grace_patch.start()

    def tearDown(self):
        self.grace_patch.stop()
        self.retry_delay_patch.stop()
        self.settle_patch.stop()
        self.bleak_patch.stop()

    def connect(self, **kwargs):
        kwargs.setdefault("name_filter", lambda name: "CAMEO" in name)
        return BLETransport.connect(**kwargs)


class BLETransportTest(BLEFakeStackMixin, unittest.TestCase):
    def test_is_a_transport(self):
        self.assertTrue(issubclass(BLETransport, Transport))

    def test_is_available_uses_optional_bleak_import(self):
        self.assertTrue(BLETransport.is_available())

    def test_connect_subscribes_and_sends_three_part_handshake(self):
        transport = self.connect()
        try:
            client = FakeBleakClient.instances[-1]
            self.assertEqual(
                set(client.notifications),
                {BLETransport.CONTROL_UUID, BLETransport.READ_UUID},
            )
            self.assertEqual(
                client.writes[:3],
                [
                    (BLETransport.CONTROL_UUID, BLETransport.INIT, True),
                    (BLETransport.READ_UUID, BLETransport.INIT, True),
                    (BLETransport.WRITE_UUID, BLETransport.INIT, True),
                ],
            )
            self.assertEqual(transport.identifier, "LOCAL-CAMEO-ID")
            self.assertIn("CAMEO 5 ALPHA-TEST", transport.location)
        finally:
            transport.close()

    def test_exact_name_and_identifier_selection(self):
        FakeBleakScanner.devices.append(FakeDevice("SECOND-ID", "CAMEO 5 ALPHA-OTHER"))
        by_name = BLETransport.connect(name="CAMEO 5 ALPHA-OTHER")
        try:
            self.assertEqual(by_name.identifier, "SECOND-ID")
        finally:
            by_name.close()

        by_identifier = BLETransport.connect(identifier="local-cameo-id")
        try:
            self.assertEqual(by_identifier.name, "CAMEO 5 ALPHA-TEST")
        finally:
            by_identifier.close()

    def test_ambiguous_discovery_is_rejected(self):
        FakeBleakScanner.devices.append(FakeDevice("SECOND-ID", "CAMEO 5 ALPHA-OTHER"))
        with self.assertRaisesRegex(ValueError, "More than one"):
            self.connect()

    def test_service_advertisement_disambiguates_matching_names(self):
        FakeBleakScanner.devices.append(
            FakeDevice(
                "WRONG-SERVICE-ID",
                "CAMEO 5 ALPHA-TEST",
                service_uuids=["0000180a-0000-1000-8000-00805f9b34fb"],
            )
        )
        transport = BLETransport.connect(name="CAMEO 5 ALPHA-TEST")
        try:
            self.assertEqual(transport.identifier, "LOCAL-CAMEO-ID")
        finally:
            transport.close()

    def test_connected_device_must_expose_vendor_service(self):
        FakeBleakScanner.devices = [
            FakeDevice(
                "WRONG-SERVICE-ID",
                "CAMEO 5 ALPHA-TEST",
                service_uuids=["0000180a-0000-1000-8000-00805f9b34fb"],
            )
        ]
        with self.assertRaisesRegex(ValueError, "does not expose vendor service"):
            BLETransport.connect(name="CAMEO 5 ALPHA-TEST")

    def test_older_scanner_without_advertisement_data_falls_back(self):
        FakeBleakScanner.supports_return_adv = False
        transport = BLETransport.connect(name="CAMEO 5 ALPHA-TEST")
        try:
            self.assertEqual(transport.identifier, "LOCAL-CAMEO-ID")
        finally:
            transport.close()

    def test_known_identifier_connects_directly_without_scanning(self):
        # Emptying the scan results proves discovery was skipped entirely:
        # if connect() fell through to the scan-based path, it would find
        # nothing to select and raise "No Bluetooth LE device found".
        FakeBleakClient.known_identifiers = {"LOCAL-CAMEO-ID"}
        FakeBleakScanner.devices = []
        transport = BLETransport.connect(identifier="LOCAL-CAMEO-ID")
        try:
            self.assertEqual(transport.identifier, "LOCAL-CAMEO-ID")
            client = FakeBleakClient.instances[-1]
            self.assertEqual(client.device, "LOCAL-CAMEO-ID")
        finally:
            transport.close()

    def test_unresolvable_identifier_falls_back_to_scanning(self):
        # The identifier is not in known_identifiers, so the direct connect
        # attempt fails -- connect() must fall back to the normal
        # discovery path rather than giving up, and still find the device
        # there (matched by identifier, same as before this feature existed).
        transport = BLETransport.connect(identifier="LOCAL-CAMEO-ID")
        try:
            self.assertEqual(transport.name, "CAMEO 5 ALPHA-TEST")
        finally:
            transport.close()

    def test_discover_filters_and_sorts(self):
        FakeBleakScanner.devices.extend(
            [
                FakeDevice("MOUSE-ID", "Mouse"),
                FakeDevice("A-CAMEO-ID", "CAMEO 4"),
            ]
        )
        result = BLETransport.discover(name_filter=lambda name: "CAMEO" in name)
        self.assertEqual(
            result,
            [
                ("A-CAMEO-ID", "CAMEO 4"),
                ("LOCAL-CAMEO-ID", "CAMEO 5 ALPHA-TEST"),
            ],
        )

    def test_write_is_acknowledged_and_chunked_at_twenty_bytes(self):
        transport = self.connect()
        try:
            client = FakeBleakClient.instances[-1]
            before = len(client.writes)
            payload = b"x" * 45
            self.assertEqual(transport.write_bytes(payload, timeout=1000), 45)
            writes = client.writes[before:]
            self.assertEqual([len(item[1]) for item in writes], [20, 20, 5])
            self.assertTrue(all(item[0] == BLETransport.WRITE_UUID for item in writes))
            self.assertTrue(all(item[2] is True for item in writes))
        finally:
            transport.close()

    def test_write_retries_att_backpressure_with_acknowledgement(self):
        transport = self.connect()
        try:
            client = FakeBleakClient.instances[-1]
            client.write_failures_remaining = 2
            before = len(client.writes)

            self.assertEqual(transport.write_bytes(b"retry", timeout=1000), 5)

            writes = client.writes[before:]
            self.assertEqual(len(writes), 3)
            self.assertTrue(all(write[1] == b"retry" for write in writes))
            self.assertTrue(all(write[2] is True for write in writes))
        finally:
            transport.close()

    def test_write_does_not_retry_non_backpressure_error(self):
        transport = self.connect()
        try:
            client = FakeBleakClient.instances[-1]
            client.write_failures_remaining = 1
            client.write_failure = RuntimeError("permission denied")
            before = len(client.writes)

            with self.assertRaisesRegex(RuntimeError, "permission denied"):
                transport.write_bytes(b"fail", timeout=1000)

            self.assertEqual(len(client.writes[before:]), 1)
        finally:
            transport.close()

    def test_write_backpressure_retries_are_bounded(self):
        transport = self.connect()
        try:
            client = FakeBleakClient.instances[-1]
            client.write_failures_remaining = 10
            before = len(client.writes)

            with self.assertRaisesRegex(RuntimeError, "ATT error: 0x0e"):
                transport.write_bytes(b"busy", timeout=1000)

            self.assertEqual(
                len(client.writes[before:]),
                BLETransport.WRITE_BACKPRESSURE_RETRIES + 1,
            )
        finally:
            transport.close()

    def test_read_combines_fragmented_notification_until_etx(self):
        transport = self.connect()
        try:
            transport._on_notification(None, b"CAMEO 5 ")
            transport._on_notification(None, b"ALPHA\x03trailing")
            self.assertEqual(
                transport.read_bytes(64, timeout=1000), b"CAMEO 5 ALPHA\x03"
            )
            # Bytes after the terminator remain buffered for the next read.
            self.assertEqual(transport.read_bytes(64, timeout=1), b"trailing")
        finally:
            transport.close()

    def test_control_notifications_are_not_returned_as_command_responses(self):
        transport = self.connect()
        try:
            client = FakeBleakClient.instances[-1]
            client.notifications[BLETransport.CONTROL_UUID](None, b"1\x03")

            with self.assertRaises(BLETimeoutError):
                transport.read_bytes(64, timeout=1)

            client.notifications[BLETransport.READ_UUID](None, b"    0\x03")
            self.assertEqual(
                transport.read_bytes(64, timeout=1000), b"    0\x03"
            )
        finally:
            transport.close()

    def test_read_timeout_uses_transport_exception(self):
        transport = self.connect()
        try:
            with self.assertRaises(BLETimeoutError):
                transport.read_bytes(64, timeout=1)
        finally:
            transport.close()

    def test_close_is_idempotent_and_stops_worker(self):
        transport = self.connect()
        thread = transport._thread
        transport.close()
        transport.close()
        self.assertFalse(thread.is_alive())


class CameoOverBLETest(BLEFakeStackMixin, unittest.TestCase):
    def test_model_status_and_tool_query_over_ble(self):
        dev = SilhouetteCameo(
            log=io.StringIO(), bluetooth_le=True, bluetooth_name="CAMEO 5 ALPHA-TEST"
        )
        try:
            self.assertIsInstance(dev.transport, BLETransport)
            self.assertEqual(dev.product_id(), PRODUCT_ID_SILHOUETTE_CAMEO5ALPHA)
            self.assertEqual(dev.status(), "ready")
            self.assertEqual(dev.get_tool_setup(), " 2, 0")
        finally:
            dev.transport.close()

    def test_ble_connect_failure_can_continue_a_dry_run(self):
        FakeBleakScanner.devices = []
        # Nothing will ever match, so _async_scan_for_match's wait_for
        # genuinely blocks for the full timeout before giving up (unlike
        # the old fake's discover(), which returned instantly regardless of
        # the requested timeout) -- shorten it here so the test stays fast
        # rather than waiting out the real default of 20s.
        with mock.patch.object(
            BLETransport.connect.__func__, "__defaults__", (None, None, 0.2, None)
        ):
            dev = SilhouetteCameo(
                log=io.StringIO(), dry_run=True, bluetooth_le=True,
                bluetooth_name="MISSING"
            )
        self.assertIsNone(dev.transport)
        self.assertEqual(dev.hardware["name"], "Crashtest Dummy Device")


if __name__ == "__main__":
    unittest.main()
