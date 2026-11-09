"""USBPRINT regression tests. Never open, query or move a physical cutter."""
import ctypes
import io
import queue
import subprocess
import threading
import unittest
from unittest import mock

from silhouette import USBPrintTransport as module
from silhouette.USBPrintTransport import USBPrintError, USBPrintTransport
from silhouette.Graphtec import SilhouetteCameo, PRODUCT_ID_SILHOUETTE_CAMEO4


class FakeIO:
    def __init__(self):
        self.input = queue.Queue()
        self.writes = []
        self.closed = False
        self.failure = None
        self.reading = threading.Event()

    def read(self, armed):
        armed.set()
        self.reading.set()
        try:
            data = self.input.get(timeout=3)
            if isinstance(data, Exception):
                raise data
            return data
        finally:
            armed.clear()

    def write(self, data, timeout):
        if self.failure:
            raise self.failure
        self.writes.append((data, timeout))
        if data == b"\x1b\x05":
            self.input.put(b"0\x03")
        elif data == b"FG\x03":
            self.input.put(b"CAMEO 4 V1.20\x03")  # synthetic, not a firmware claim
        return len(data)

    def close(self):
        self.closed = True
        self.input.put(USBPrintError("cancelled"))


class TransportTest(unittest.TestCase):
    def setUp(self):
        self.io = FakeIO()
        self.transport = USBPrintTransport(self.io)
        self.addCleanup(self.transport.close)

    def test_fragmented_registration_and_coalesced_status(self):
        self.io.input.put(b"  ")
        self.io.input.put(b"  0\x030\x03")
        self.assertEqual(self.transport.read_bytes(timeout=1000), b"    0\x03")
        self.assertEqual(self.transport.read_bytes(timeout=1000), b"0\x03")

    def test_timeout_keeps_partial_response_and_native_read(self):
        self.io.input.put(b"    ")
        with self.assertRaises(TimeoutError):
            self.transport.read_bytes(timeout=10)
        self.assertFalse(self.io.closed)
        self.io.input.put(b"0\x03")
        self.assertEqual(self.transport.read_bytes(timeout=1000), b"    0\x03")

    def test_read_size_does_not_discard_remaining_bytes(self):
        self.io.input.put(b"ABCDEF\x030\x03")
        self.assertEqual(self.transport.read_bytes(3, 1000), b"ABC")
        self.assertEqual(self.transport.read_bytes(64, 1000), b"DEF\x03")
        self.assertEqual(self.transport.read_bytes(64, 1000), b"0\x03")

    def test_write_preserves_bytes_and_timeout(self):
        self.assertEqual(self.transport.write_bytes(b"M10,20\x03", 321), 7)
        self.assertEqual(self.io.writes, [(b"M10,20\x03", 321)])

    def test_write_failure_prevents_resending(self):
        self.io.failure = TimeoutError("uncertain completion")
        with self.assertRaises(USBPrintError) as error:
            self.transport.write_bytes(b"D10,20\x03")
        self.assertIsNone(error.exception.errno)
        self.io.failure = None
        with self.assertRaises(USBPrintError):
            self.transport.write_bytes(b"D10,20\x03")
        self.assertEqual(self.io.writes, [])

    def test_close_unblocks_reader_and_is_idempotent(self):
        errors = []
        def read():
            try:
                self.transport.read_bytes(timeout=0)
            except USBPrintError as error:
                errors.append(error)
        worker = threading.Thread(target=read)
        worker.start()
        self.transport.close()
        self.transport.close()
        worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertFalse(self.transport._thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertTrue(self.io.closed)
        with self.assertRaises(USBPrintError):
            self.transport.write_bytes(b"D1,2\x03")

    def test_disconnect_propagates(self):
        self.io.input.put(USBPrintError("disconnected"))
        with self.assertRaisesRegex(USBPrintError, "disconnected"):
            self.transport.read_bytes(timeout=1000)


class DiscoveryTest(unittest.TestCase):
    def test_matches_interface_not_localized_labels_or_other_pid(self):
        path = r"\\?\usb#vid_0b4d&pid_1137#redacted#{guid}"
        output = "Nome localizado: " + path + "\n" + path + "\n" + path.replace("1137#", "11370#")
        with mock.patch.object(subprocess, "run", return_value=mock.Mock(returncode=0, stdout=output)) as run:
            self.assertEqual(module._device_path(), path)
        self.assertIn("/enabled", run.call_args.args[0])

    def test_multiple_devices_are_rejected(self):
        output = r"\\?\usb#vid_0b4d&pid_1137#one" + "\n" + r"\\?\usb#vid_0b4d&pid_1137#two"
        with mock.patch.object(subprocess, "run", return_value=mock.Mock(returncode=0, stdout=output)):
            with self.assertRaisesRegex(USBPrintError, "found 2"):
                module._device_path()

    def test_missing_or_failed_enumeration(self):
        for code in (0, 1):
            with mock.patch.object(subprocess, "run", return_value=mock.Mock(returncode=code, stdout="")):
                with self.assertRaises(USBPrintError):
                    module._device_path()

    def test_non_windows_fails_before_discovery(self):
        with mock.patch.object(module.sys, "platform", "linux"), mock.patch.object(module, "_device_path") as find:
            with self.assertRaisesRegex(USBPrintError, "only on Windows"):
                USBPrintTransport.connect()
            find.assert_not_called()


class DriverTest(unittest.TestCase):
    def test_native_selection_queries_and_no_libusb_probe(self):
        native = USBPrintTransport(FakeIO())
        self.addCleanup(native.close)
        with mock.patch.object(USBPrintTransport, "connect", return_value=native), \
             mock.patch.object(SilhouetteCameo, "_find_usb_device", side_effect=AssertionError("libusb probe")):
            cutter = SilhouetteCameo(log=io.StringIO(), usbprint=True)
            self.assertEqual(cutter.product_id(), PRODUCT_ID_SILHOUETTE_CAMEO4)
            self.assertEqual(cutter.status(), "ready")
            self.assertEqual(cutter.get_version(), "CAMEO 4 V1.20")

    def test_conflicting_bluetooth_and_model_selectors(self):
        for settings in ({"bluetooth_addr": "AA:BB"}, {"bluetooth_le": True},
                         {"bluetooth_name": "CAMEO"}, {"force_hardware": "Silhouette_Cameo3"}):
            with self.subTest(settings=settings), mock.patch.object(USBPrintTransport, "connect") as connect:
                with self.assertRaises(ValueError):
                    SilhouetteCameo(log=io.StringIO(), usbprint=True, **settings)
                connect.assert_not_called()

    def test_dry_run_without_device_does_not_send_cut(self):
        with mock.patch.object(USBPrintTransport, "connect", side_effect=USBPrintError("no device")):
            cutter = SilhouetteCameo(log=io.StringIO(), usbprint=True, dry_run=True)
            self.assertEqual(cutter.status(), "ready")
            self.assertIsNone(cutter.write(b"D1,2\x03"))

    def test_default_usb_still_uses_existing_probe(self):
        with mock.patch.object(SilhouetteCameo, "_find_usb_device", return_value=None) as probe, \
             mock.patch.object(USBPrintTransport, "connect") as connect:
            SilhouetteCameo(log=io.StringIO(), dry_run=True)
            probe.assert_called_once()
            connect.assert_not_called()


class FakeKernel:
    def __init__(self, immediate=False, transferred=7, wait_result=0):
        self.immediate = immediate
        self.transferred = transferred
        self.wait_result = wait_result
        self.calls = []

    def CreateFileW(self, *args):
        self.calls.append(("open", args))
        return 100

    def CreateEventW(self, *args):
        return 200

    def WriteFile(self, handle, buf, count, transferred, ov):
        self.calls.append(("write", bytes(buf.raw[:count])))
        transferred._obj.value = self.transferred
        return self.immediate

    def WaitForSingleObject(self, event, timeout):
        self.calls.append(("wait", timeout))
        return self.wait_result

    def GetOverlappedResult(self, handle, ov, transferred, wait):
        self.calls.append(("completion", wait))
        transferred._obj.value = self.transferred
        return True

    def CancelIoEx(self, handle, ov):
        self.calls.append(("cancel", handle))
        return True

    def CloseHandle(self, handle):
        self.calls.append(("close", handle))
        return True


class NativeIOTest(unittest.TestCase):
    def create(self, **kwargs):
        api = FakeKernel(**kwargs)
        with mock.patch.object(module, "_kernel32", return_value=api):
            native = module._NativeIO("redacted interface")
        self.addCleanup(native.close)
        return native, api

    def test_exclusive_overlapped_open(self):
        native, api = self.create()
        self.assertEqual(api.calls[0][1], ("redacted interface", 0xC0000000, 0, None, 3, 0x40000000, None))

    def test_immediate_write_and_completed_write(self):
        for immediate in (True, False):
            native, api = self.create(immediate=immediate)
            with mock.patch.object(ctypes, "get_last_error", return_value=module.IO_PENDING, create=True):
                self.assertEqual(native.write(b"M10,20\x03", 123), 7)
            self.assertEqual(native.pending, {})
            self.assertEqual(api.calls[-1], ("close", 200))
            if not immediate:
                self.assertIn(("wait", 123), api.calls)

    def test_write_timeout_drains_cancel_before_releasing_event(self):
        native, api = self.create(wait_result=258)
        with mock.patch.object(ctypes, "get_last_error", return_value=module.IO_PENDING, create=True):
            with self.assertRaisesRegex(USBPrintError, "delivery is uncertain"):
                native.write(b"M10,20\x03", 123)
        self.assertEqual(api.calls[-3:], [("cancel", 100), ("completion", True), ("close", 200)])

    def test_partial_write_is_fatal(self):
        native, api = self.create(immediate=True, transferred=2)
        with self.assertRaisesRegex(USBPrintError, "Incomplete"):
            native.write(b"M10,20\x03", 100)
        self.assertEqual(sum(call[0] == "write" for call in api.calls), 1)

    def test_close_defers_file_handle_release_until_io_completion(self):
        native, api = self.create()
        ov = module._Overlapped()
        native.pending[1] = (ov, ctypes.create_string_buffer(b"data"))
        native.close()
        self.assertIn(("cancel", 100), api.calls)
        self.assertNotIn(("close", 100), api.calls)
        native.pending.clear()  # Simulate the worker retiring its completed operation.
        with native.lock:
            native._close_if_idle()
        self.assertEqual(api.calls[-1], ("close", 100))
        native.close()
        self.assertEqual(api.calls.count(("close", 100)), 1)

    def test_immediate_native_failure_does_not_wait_or_retry(self):
        native, api = self.create()
        with mock.patch.object(ctypes, "get_last_error", return_value=5, create=True):
            with self.assertRaisesRegex(USBPrintError, "Windows error 5"):
                native.write(b"M10,20\x03", 123)
        self.assertEqual(native.pending, {})
        self.assertFalse(any(call[0] in ("wait", "cancel") for call in api.calls))

    def test_event_is_retained_through_cancelled_native_read(self):
        native, api = self.create()
        armed = threading.Event()
        release = threading.Event()
        errors = []
        api.ReadFile = lambda *args: False
        api.WaitForSingleObject = lambda *args: (release.wait(1) and 0)
        def cancel(handle, ov):
            api.calls.append(("cancel", handle))
            release.set()
            return True
        api.CancelIoEx = cancel
        def completed(handle, ov, transferred, wait):
            self.assertNotIn(("close", 200), api.calls)
            self.assertNotIn(("close", 100), api.calls)
            return False
        api.GetOverlappedResult = completed
        def read():
            try:
                native.read(armed)
            except USBPrintError as error:
                errors.append(error)
        with mock.patch.object(ctypes, "get_last_error", return_value=module.IO_PENDING, create=True):
            worker = threading.Thread(target=read)
            worker.start()
            self.assertTrue(armed.wait(1))
            self.assertEqual(len(native.pending), 1)
            native.close()
            worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertEqual(api.calls[-2:], [("close", 200), ("close", 100)])
