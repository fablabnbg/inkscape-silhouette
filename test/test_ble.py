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
    def __init__(self, address, name):
        self.address = address
        self.name = name


class FakeBleakScanner:
    devices: ClassVar[list] = []

    @classmethod
    async def discover(cls, timeout=8):
        del timeout
        return list(cls.devices)


class FakeBleakClient:
    instances: ClassVar[list] = []

    def __init__(self, device, timeout=None, disconnected_callback=None):
        self.device = device
        self.timeout = timeout
        self.disconnected_callback = disconnected_callback
        self.is_connected = False
        self.notifications = {}
        self.writes = []
        self.__class__.instances.append(self)

    async def connect(self):
        self.is_connected = True
        return True

    async def start_notify(self, characteristic, callback):
        self.notifications[characteristic] = callback

    async def write_gatt_char(self, characteristic, data, response=False):
        raw = bytes(data)
        self.writes.append((characteristic, raw, response))
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
        FakeBleakClient.instances = []
        fake_bleak = types.ModuleType("bleak")
        fake_bleak.BleakScanner = FakeBleakScanner
        fake_bleak.BleakClient = FakeBleakClient
        self.bleak_patch = mock.patch.dict(sys.modules, {"bleak": fake_bleak})
        self.bleak_patch.start()
        self.settle_patch = mock.patch.object(
            BLETransport, "HANDSHAKE_SETTLE_SECONDS", 0.0
        )
        self.settle_patch.start()

    def tearDown(self):
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
                {BLETransport.STATUS_UUID, BLETransport.READ_UUID},
            )
            self.assertEqual(
                client.writes[:3],
                [
                    (BLETransport.STATUS_UUID, BLETransport.INIT, True),
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
        dev = SilhouetteCameo(
            log=io.StringIO(), dry_run=True, bluetooth_le=True, bluetooth_name="MISSING"
        )
        self.assertIsNone(dev.transport)
        self.assertEqual(dev.hardware["name"], "Crashtest Dummy Device")


if __name__ == "__main__":
    unittest.main()
