# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Eron Greco
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Experimental CAMEO 4 transport using the stock Windows USBPRINT driver.

No commands, registration geometry, or tool settings belong in this module.
The pending native read survives the caller's short diagnostic-read timeouts.
Win32 libraries are loaded only by connect(), so importing is portable.
"""

import ctypes
from ctypes import wintypes
import queue
import re
import subprocess
import sys
import threading
import time

from silhouette.Transport import Transport

USBPRINT_GUID = "{28d78fad-5a12-11d1-ae5b-0000f803a8c2}"
CAMEO4_ID = "VID_0B4D&PID_1137"
IO_PENDING = 997
INFINITE = 0xFFFFFFFF


class USBPrintError(OSError):
    """Fatal transport error. Deliberately does not request write retries."""


def _device_path():
    result = subprocess.run(
        ["pnputil", "/enum-interfaces", "/class", USBPRINT_GUID, "/enabled"],
        capture_output=True, text=True, errors="replace", timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise USBPrintError("Cannot enumerate connected USBPRINT interfaces with pnputil")
    # Match the VID/PID as path components, not as a substring of another PID.
    paths = set()
    for line in result.stdout.splitlines():
        start = line.find("\\\\?\\")
        if start >= 0:
            path = line[start:].strip()
            if re.search(r"[\\#]" + CAMEO4_ID + r"[&#]", path, re.I):
                paths.add(path)
    if len(paths) != 1:
        raise USBPrintError("Expected one connected CAMEO 4 USBPRINT interface; found %d. "
                            "Keep the Windows printer driver and connect one cutter." % len(paths))
    return paths.pop()


class _Overlapped(ctypes.Structure):
    _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t),
                ("Offset", wintypes.DWORD), ("OffsetHigh", wintypes.DWORD),
                ("hEvent", wintypes.HANDLE)]


def _kernel32():
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CreateFileW": ([wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                         wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                         wintypes.HANDLE], wintypes.HANDLE),
        "CreateEventW": ([wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL,
                          wintypes.LPCWSTR], wintypes.HANDLE),
        "ReadFile": ([wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                      ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(_Overlapped)], wintypes.BOOL),
        "WriteFile": ([wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD,
                       ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(_Overlapped)], wintypes.BOOL),
        "GetOverlappedResult": ([wintypes.HANDLE, ctypes.POINTER(_Overlapped),
                                 ctypes.POINTER(wintypes.DWORD), wintypes.BOOL], wintypes.BOOL),
        "WaitForSingleObject": ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
        "CancelIoEx": ([wintypes.HANDLE, ctypes.POINTER(_Overlapped)], wintypes.BOOL),
        "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
    }
    for name, (args, result) in signatures.items():
        getattr(api, name).argtypes = args
        getattr(api, name).restype = result
    return api


class _NativeIO:
    """Own native handles until every overlapped operation has completed."""

    def __init__(self, path):
        self.api = _kernel32()
        self.lock = threading.Lock()
        self.pending = {}
        self.closing = False
        self.handle = self.api.CreateFileW(path, 0xC0000000, 0, None, 3, 0x40000000, None)
        if self.handle in (None, ctypes.c_void_p(-1).value):
            raise USBPrintError("Cannot open CAMEO 4 USBPRINT exclusively (Windows error %d). "
                                "Close Silhouette Studio and other cutter clients."
                                % ctypes.get_last_error())

    def _transfer(self, data=None, armed=None, timeout=0):
        buf = ctypes.create_string_buffer(64 if data is None else data)
        count = 64 if data is None else len(data)
        ov = _Overlapped()
        immediate = wintypes.DWORD()
        # Register and submit under the same lock: close() cannot miss a newly
        # issued request by cancelling it before ReadFile/WriteFile is called.
        with self.lock:
            if self.closing:
                raise USBPrintError("USBPRINT connection is closed")
            ov.hEvent = self.api.CreateEventW(None, True, False, None)
            if not ov.hEvent:
                raise USBPrintError("Cannot create USBPRINT I/O event")
            self.pending[id(ov)] = (ov, buf)
            fn = self.api.ReadFile if data is None else self.api.WriteFile
            ok = fn(self.handle, buf, count, ctypes.byref(immediate), ctypes.byref(ov))
            error = 0 if ok else ctypes.get_last_error()
            if not ok and error == IO_PENDING and armed is not None:
                armed.set()
        try:
            if not ok:
                if error != IO_PENDING:
                    raise USBPrintError("USBPRINT I/O failed (Windows error %d)" % error)
                rc = self.api.WaitForSingleObject(ov.hEvent, timeout or INFINITE)
                if rc != 0:
                    self.api.CancelIoEx(self.handle, ctypes.byref(ov))
                    # Cancellation is only a request. Drain completion before
                    # releasing the buffer, OVERLAPPED, event or file handle.
                    self.api.GetOverlappedResult(self.handle, ctypes.byref(ov),
                                                 ctypes.byref(immediate), True)
                    raise USBPrintError("USBPRINT I/O timed out or wait failed; "
                                        "delivery is uncertain, do not resend the cut automatically")
                if not self.api.GetOverlappedResult(self.handle, ctypes.byref(ov),
                                                    ctypes.byref(immediate), False):
                    raise USBPrintError("USBPRINT completion failed (Windows error %d)"
                                        % ctypes.get_last_error())
            if data is not None and immediate.value != count:
                raise USBPrintError("Incomplete USBPRINT write (%d/%d); delivery is uncertain"
                                    % (immediate.value, count))
            return bytes(buf.raw[:immediate.value]) if data is None else immediate.value
        finally:
            if armed is not None:
                armed.clear()
            with self.lock:
                self.pending.pop(id(ov))
                self.api.CloseHandle(ov.hEvent)
                self._close_if_idle()

    def read(self, armed):
        return self._transfer(armed=armed)

    def write(self, data, timeout):
        return self._transfer(data=data, timeout=timeout)

    def _close_if_idle(self):
        if self.closing and not self.pending and self.handle is not None:
            self.api.CloseHandle(self.handle)
            self.handle = None

    def close(self):
        with self.lock:
            self.closing = True
            for ov, _buf in self.pending.values():
                self.api.CancelIoEx(self.handle, ctypes.byref(ov))
            self._close_if_idle()


class USBPrintTransport(Transport):
    """Opt-in, CAMEO 4 only. Constructor accepts an I/O object for unit tests."""

    location = "Windows USBPRINT (CAMEO 4)"
    bus = "usbprint"
    address = -1
    timeout_exceptions = (OSError,)

    @classmethod
    def connect(cls):
        if sys.platform != "win32":
            raise USBPrintError("Native USBPRINT is available only on Windows")
        io = _NativeIO(_device_path())
        try:
            return cls(io)
        except Exception:
            io.close()
            raise

    def __init__(self, io):
        self._io = io
        self._messages = queue.Queue()
        self._armed = threading.Event()
        self._closed = threading.Event()
        self._write_lock = threading.Lock()
        self._fault = None
        self._buffer = b""
        self._thread = threading.Thread(target=self._reader, name="USBPRINT input", daemon=True)
        self._thread.start()
        if not self._armed.wait(2):
            self.close()
            raise USBPrintError("Cannot arm USBPRINT input")
        if self._fault is not None:
            self.close()
            raise self._fault

    def _reader(self):
        try:
            while not self._closed.is_set():
                data = self._io.read(self._armed)
                if not data:
                    raise USBPrintError("USBPRINT input ended unexpectedly")
                self._messages.put(data)
        except Exception as error:
            if not self._closed.is_set():
                self._fault = USBPrintError(str(error))
                self._messages.put(self._fault)
        finally:
            self._armed.set()  # Wake a writer/startup waiter on failure, too.

    def _check(self):
        if self._closed.is_set():
            raise USBPrintError("USBPRINT connection is closed")
        if self._fault is not None:
            raise self._fault

    def write_bytes(self, data, timeout=5000):
        with self._write_lock:
            self._check()
            if not self._armed.wait(2):
                raise USBPrintError("USBPRINT input is not pending")
            self._check()
            try:
                return self._io.write(bytes(data), timeout)
            except Exception as error:
                self._fault = USBPrintError(str(error))
                self._messages.put(self._fault)
                raise self._fault from error

    def read_bytes(self, size=64, timeout=5000):
        if size <= 0:
            raise ValueError("read size must be positive")
        deadline = time.monotonic() + timeout / 1000 if timeout else None
        while True:
            self._check()
            end = self._buffer.find(b"\x03")
            if end >= 0 or len(self._buffer) >= size:
                take = min(size, end + 1 if end >= 0 else size)
                data, self._buffer = self._buffer[:take], self._buffer[take:]
                return data
            remaining = None if deadline is None else max(0, deadline - time.monotonic())
            try:
                data = self._messages.get(timeout=remaining)
            except queue.Empty:
                # Keep the partial frame and the native read alive.
                raise TimeoutError("USBPRINT response timeout") from None
            if isinstance(data, Exception):
                raise data
            self._buffer += data

    def close(self):
        if not self._closed.is_set():
            self._closed.set()
            self._io.close()
            self._messages.put(USBPrintError("USBPRINT connection is closed"))
            self._armed.set()
            if self._thread is not threading.current_thread():
                self._thread.join(2)
