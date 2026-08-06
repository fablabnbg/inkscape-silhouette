# (c) 2026 inkscape-silhouette contributors
#
# Distribute under GPLv2 or ask.
# ruff: noqa: N999

"""Synchronous adapter for Silhouette cutters using Bluetooth Low Energy.

``bleak`` is asynchronous while Graphtec.py deliberately uses a small,
synchronous transport interface. BLETransport owns an asyncio event loop in a
background thread and exposes blocking write_bytes()/read_bytes() methods to
the protocol layer.

The import of bleak is intentionally lazy. USB and RFCOMM users must remain
able to import and use the driver without installing the optional BLE stack.

Characteristic roles and the initialization handshake were cross-checked
against bob-takuya/cameo-cut (MIT): https://github.com/bob-takuya/cameo-cut
"""

import asyncio
import concurrent.futures
import threading
import time

from silhouette.Transport import Transport


class BLETimeoutError(OSError):
    """A BLE operation exceeded the timeout supplied by the protocol layer."""


class BLEDisconnectedError(OSError):
    """The BLE peripheral disconnected while an operation was pending."""


class BLETransport(Transport):
    """Graphtec byte stream carried by the cutter's vendor GATT service."""

    SERVICE_UUID = "e2088282-4fde-42f9-bb22-6ec3c7ed8f91"
    WRITE_UUID = "6d92661d-f429-4d67-929b-28e7a9780912"
    READ_UUID = "8dcf199a-30e7-4bd4-beb6-beb57dca866c"
    CONTROL_UUID = "61490654-b5b4-458c-a867-9e15bc1471e0"

    INIT = b"\x1b\x04"
    CHUNK_SIZE = 20
    HANDSHAKE_SETTLE_SECONDS = 1.0
    WRITE_BACKPRESSURE_RETRIES = 3
    WRITE_BACKPRESSURE_DELAY_SECONDS = 0.1

    timeout_exceptions = (BLETimeoutError, BLEDisconnectedError, OSError)

    def __init__(self):
        self.bus = "bluetooth-le"
        self.location = "bluetooth-le (not connected)"
        self.identifier = None
        self.name = None
        self.client = None

        self._loop = asyncio.new_event_loop()
        self._loop_ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run_loop, name="inkscape-silhouette-ble", daemon=True
        )
        self._thread.start()
        self._loop_ready.wait()

        self._incoming = bytearray()
        self._incoming_condition = threading.Condition()
        self._write_lock = threading.Lock()
        self._closed = False
        self._disconnected = False
        self._disconnect_reason = None

    @classmethod
    def is_available(cls):
        """Return True when the optional bleak package can be imported."""
        try:
            import bleak  # noqa: F401

            return True
        except (ImportError, OSError):
            return False

    @staticmethod
    def _timeout_seconds(timeout_ms):
        if timeout_ms is None or timeout_ms <= 0:
            return None
        return timeout_ms / 1000.0

    @staticmethod
    def _device_name(device):
        return getattr(device, "name", None) or ""

    @staticmethod
    def _device_identifier(device):
        return getattr(device, "address", None) or ""

    @classmethod
    def _discovery_records(cls, discovered):
        """Normalize Bleak discovery into ``(device, advertisement)`` pairs."""
        values = discovered.values() if isinstance(discovered, dict) else discovered
        records = []
        for value in values:
            if isinstance(value, tuple) and len(value) == 2:
                records.append(value)
            else:
                records.append((value, None))
        return records

    @classmethod
    def _prefer_service_advertisements(cls, discovered):
        """Prefer peripherals advertising the known vendor service.

        Some platforms and older Bleak versions omit service UUIDs from scan
        results. In that case selection falls back to name/identifier and the
        connected GATT service is validated before the handshake.
        """
        records = cls._discovery_records(discovered)
        matching = []
        for device, advertisement in records:
            service_uuids = getattr(advertisement, "service_uuids", None) or []
            if cls.SERVICE_UUID in {uuid.casefold() for uuid in service_uuids}:
                matching.append((device, advertisement))
        return matching or records

    @classmethod
    def _client_has_vendor_service(cls, client):
        """Return whether a connected client exposes the expected GATT service."""
        services = getattr(client, "services", None)
        if services is None:
            # Compatibility with old Bleak clients that did not expose the
            # resolved service collection as a property.
            return True
        get_service = getattr(services, "get_service", None)
        if get_service is not None:
            return get_service(cls.SERVICE_UUID) is not None
        return cls.SERVICE_UUID in {
            getattr(service, "uuid", "").casefold() for service in services
        }

    @classmethod
    def _select_device(cls, devices, name=None, identifier=None, name_filter=None):
        """Choose one device without assuming that its identifier is a MAC.

        macOS exposes an opaque per-host UUID in ``device.address``. Advertised
        name is therefore the portable selector; identifier remains useful as an
        optional local override.
        """
        candidates = cls._discovery_records(devices)

        if identifier:
            wanted = identifier.casefold()
            candidates = [
                record
                for record in candidates
                if cls._device_identifier(record[0]).casefold() == wanted
            ]
        elif name:
            wanted = name.casefold()
            exact = [
                record
                for record in candidates
                if cls._device_name(record[0]).casefold() == wanted
            ]
            candidates = exact or [
                record
                for record in candidates
                if wanted in cls._device_name(record[0]).casefold()
            ]
        elif name_filter is not None:
            candidates = [
                record
                for record in candidates
                if name_filter(cls._device_name(record[0]))
            ]

        candidates = cls._prefer_service_advertisements(candidates)

        if not candidates:
            selector = identifier or name or "a supported Silhouette cutter"
            raise ValueError(f"No Bluetooth LE device found matching {selector}")

        if len(candidates) > 1:
            descriptions = [
                f"{cls._device_name(d) or 'unnamed'} "
                f"({cls._device_identifier(d) or 'no identifier'})"
                for d, _ in candidates
            ]
            raise ValueError(
                "More than one Bluetooth LE cutter matched; select one by its exact "
                f"advertised name or local identifier: {', '.join(descriptions)}"
            )

        return candidates[0][0]

    @classmethod
    def discover(cls, timeout=8, name_filter=None):
        """Return sorted ``(identifier, advertised_name)`` BLE devices.

        Discovery runs on a temporary worker loop so callers remain synchronous.
        On macOS the identifier is a CoreBluetooth UUID, not a MAC address.
        """
        if not cls.is_available():
            raise RuntimeError(
                "Bluetooth LE support requires the optional 'bleak' package."
            )
        transport = cls()
        try:
            devices = transport._submit(
                transport._async_discover(timeout),
                timeout=max(float(timeout) + 5.0, 5.0),
            )
            results = []
            for device in devices:
                name = cls._device_name(device)
                if name_filter is None or name_filter(name):
                    results.append((cls._device_identifier(device), name))
            return sorted(results, key=lambda item: (item[1] or "", item[0] or ""))
        finally:
            transport.close()

    @classmethod
    def connect(cls, name=None, identifier=None, timeout=20, name_filter=None):
        """Discover, connect, subscribe, and initialize a BLE cutter."""
        if not cls.is_available():
            raise RuntimeError(
                "Bluetooth LE support requires the optional 'bleak' package."
            )

        transport = cls()
        try:
            transport._submit(
                transport._async_connect(
                    name=name,
                    identifier=identifier,
                    timeout=timeout,
                    name_filter=name_filter,
                ),
                timeout=max(
                    float(timeout) * 2.0 + cls.HANDSHAKE_SETTLE_SECONDS + 5.0, 10.0
                ),
            )
            return transport
        except Exception:
            transport.close()
            raise

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop_ready.set()
        self._loop.run_forever()

        pending = asyncio.all_tasks(self._loop)
        for task in pending:
            task.cancel()
        if pending:
            self._loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )
        self._loop.close()

    def _submit(self, coroutine, timeout=None):
        if self._closed:
            coroutine.close()
            raise BLEDisconnectedError("Bluetooth LE transport is closed")
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise BLETimeoutError("Bluetooth LE operation timed out")

    async def _async_discover(self, timeout, return_adv=False):
        from bleak import BleakScanner

        if return_adv:
            try:
                return await BleakScanner.discover(timeout=timeout, return_adv=True)
            except TypeError:
                # Compatibility with older Bleak scanners.
                pass
        return await BleakScanner.discover(timeout=timeout)

    async def _async_connect(self, name, identifier, timeout, name_filter):
        from bleak import BleakClient

        devices = await self._async_discover(timeout, return_adv=True)
        device = self._select_device(
            devices, name=name, identifier=identifier, name_filter=name_filter
        )

        try:
            client = BleakClient(
                device, timeout=timeout, disconnected_callback=self._on_disconnected
            )
        except TypeError:
            # Compatibility with older bleak clients that do not accept the callback
            # in the constructor.
            client = BleakClient(device, timeout=timeout)
            setter = getattr(client, "set_disconnected_callback", None)
            if setter is not None:
                setter(self._on_disconnected)

        await client.connect()
        self.client = client
        if not self._client_has_vendor_service(client):
            raise ValueError(
                f"Bluetooth LE device does not expose vendor service {self.SERVICE_UUID}"
            )
        self.name = self._device_name(device)
        self.identifier = self._device_identifier(device)
        self.location = "bluetooth-le {} ({})".format(
            self.name or "unnamed", self.identifier or "no identifier"
        )

        await client.start_notify(self.CONTROL_UUID, self._on_notification)
        await client.start_notify(self.READ_UUID, self._on_notification)

        for characteristic in (self.CONTROL_UUID, self.READ_UUID, self.WRITE_UUID):
            await client.write_gatt_char(characteristic, self.INIT, response=True)

        if self.HANDSHAKE_SETTLE_SECONDS:
            await asyncio.sleep(self.HANDSHAKE_SETTLE_SECONDS)
        with self._incoming_condition:
            self._incoming.clear()

    def _on_notification(self, sender, data):
        del sender
        with self._incoming_condition:
            self._incoming.extend(bytes(data))
            self._incoming_condition.notify_all()

    def _on_disconnected(self, client):
        del client
        with self._incoming_condition:
            self._disconnected = True
            self._disconnect_reason = "Bluetooth LE cutter disconnected"
            self._incoming_condition.notify_all()

    async def _async_write_chunk(self, chunk):
        if self.client is None or not getattr(self.client, "is_connected", False):
            raise BLEDisconnectedError("Bluetooth LE cutter is not connected")
        for attempt in range(self.WRITE_BACKPRESSURE_RETRIES + 1):
            try:
                await self.client.write_gatt_char(self.WRITE_UUID, chunk, response=True)
                return
            except Exception as error:
                if (
                    not self._is_backpressure_error(error)
                    or attempt == self.WRITE_BACKPRESSURE_RETRIES
                ):
                    raise
                await asyncio.sleep(
                    self.WRITE_BACKPRESSURE_DELAY_SECONDS * (2**attempt)
                )

    @staticmethod
    def _is_backpressure_error(error):
        """Recognize the cutter's transient ATT buffer-busy response."""
        details = getattr(error, "dbus_error_details", None)
        message = " ".join(str(part) for part in (error, details) if part).casefold()
        return "att error: 0x0e" in message or "unlikely error" in message

    def write_bytes(self, data, timeout):
        """Write all bytes as acknowledged 20-byte ATT payloads."""
        raw = bytes(data)
        timeout_seconds = self._timeout_seconds(timeout)
        with self._write_lock:
            for offset in range(0, len(raw), self.CHUNK_SIZE):
                chunk = raw[offset : offset + self.CHUNK_SIZE]
                self._submit(self._async_write_chunk(chunk), timeout=timeout_seconds)
        return len(raw)

    def read_bytes(self, size, timeout):
        """Read one ETX-terminated reply, or up to ``size`` buffered bytes."""
        timeout_seconds = self._timeout_seconds(timeout)
        deadline = (
            None if timeout_seconds is None else time.monotonic() + timeout_seconds
        )

        with self._incoming_condition:
            while True:
                if self._incoming:
                    etx = self._incoming.find(b"\x03")
                    if etx >= 0:
                        count = min(size, etx + 1)
                        result = bytes(self._incoming[:count])
                        del self._incoming[:count]
                        return result
                    if len(self._incoming) >= size:
                        result = bytes(self._incoming[:size])
                        del self._incoming[:size]
                        return result

                if self._disconnected:
                    raise BLEDisconnectedError(
                        self._disconnect_reason or "Bluetooth LE cutter disconnected"
                    )

                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    if self._incoming:
                        count = min(size, len(self._incoming))
                        result = bytes(self._incoming[:count])
                        del self._incoming[:count]
                        return result
                    raise BLETimeoutError("Bluetooth LE read timed out")
                self._incoming_condition.wait(remaining)

    async def _async_disconnect(self):
        if self.client is not None and getattr(self.client, "is_connected", False):
            await self.client.disconnect()

    def close(self):
        """Disconnect and stop the worker loop. Safe to call more than once."""
        if self._closed:
            return

        try:
            if self._loop.is_running():
                try:
                    self._submit(self._async_disconnect(), timeout=5.0)
                except Exception:  # noqa: BLE001, S110 - shutdown is best-effort
                    pass
        finally:
            self._closed = True
            with self._incoming_condition:
                self._disconnected = True
                self._incoming_condition.notify_all()
            if self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
            if (
                self._thread.is_alive()
                and threading.current_thread() is not self._thread
            ):
                self._thread.join(timeout=5.0)
