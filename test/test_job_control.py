"""Tests for pausing / cancelling a running cut job."""

import io
import re
import threading
import unittest
from unittest import mock

from silhouette.Graphtec import SilhouetteCameo
from silhouette.JobControl import JobCancelled, JobControl
from sendto_silhouette import SendtoSilhouette


class FakeTransport:
    """Records everything sent, and reports 'ready' to status requests."""

    def __init__(self):
        self.sent = b""
        self.pending = None

    def write_bytes(self, data, timeout):
        self.sent += data
        if data == b"\x1b\x05":
            self.pending = b"0\x03"
        return len(data)

    def read_bytes(self, size, timeout):
        resp, self.pending = self.pending, None
        if resp is None:
            raise OSError("timeout")
        return resp

    def close(self):
        pass


class BusyTransport(FakeTransport):
    """Reports 'moving' for a few status polls after each chunk of data,
       and calls on_status(n) for the n-th status poll."""

    def __init__(self, on_status):
        FakeTransport.__init__(self)
        self.on_status = on_status
        self.polls = 0
        self.busy = 0

    def write_bytes(self, data, timeout):
        n = FakeTransport.write_bytes(self, data, timeout)
        if data == b"\x1b\x05":
            self.polls += 1
            self.on_status(self.polls)
            if self.busy:
                self.busy -= 1
                self.pending = b"1\x03"
        elif not data.startswith(b"\x1b"):
            self.busy = 3
        return n


def make_cameo(job_control=None, chunk_mm=None, hardware="Silhouette_Cameo5_Alpha"):
    def no_usb_device(self):
        self.hardware = {}
        return None

    with mock.patch.object(SilhouetteCameo, "_find_usb_device",
                           no_usb_device):
        dev = SilhouetteCameo(log=io.StringIO(), job_control=job_control,
                              force_hardware=hardware)
    dev.transport = FakeTransport()
    dev.job_chunk_mm = chunk_mm
    return dev


def long_job():
    """Enough paths to need several 1k chunks in safe_write()."""
    return [[(10 + i % 50, 10 + i // 50), (11 + i % 50, 10 + i // 50),
             (11 + i % 50, 11 + i // 50)] for i in range(300)]


def plot(dev):
    return dev.plot(pathlist=long_job(), mediawidth=300, mediaheight=300,
                    endposition="below")


def cut_data(sent):
    """Only the M/D commands, i.e. without escapes (status, interrupts)."""
    sent = re.sub(rb"\x1b.", b"", sent, flags=re.S)
    return [c for c in sent.split(b"\x03")
            if c[:1] in (b"M", b"D")]


class ScriptedControl(JobControl):
    """Pauses or cancels at the n-th checkpoint."""

    def __init__(self, action, at=2):
        JobControl.__init__(self)
        self.action, self.at = action, at
        self.checkpoints = 0
        self.waits = 0

    def progress(self, done, total):
        self.checkpoints += 1
        if self.checkpoints == self.at:
            getattr(self, self.action)()

    def wait_while_paused(self, timeout=None):
        self.waits += 1
        self.resume()
        return True


class JobControlFlagsTest(unittest.TestCase):
    def test_pause_resume_cancel(self):
        ctl = JobControl()
        self.assertFalse(ctl.is_paused())
        ctl.pause()
        self.assertTrue(ctl.is_paused())
        self.assertFalse(ctl.wait_while_paused(timeout=0.01))
        ctl.resume()
        self.assertTrue(ctl.wait_while_paused(timeout=0.01))
        ctl.pause()
        ctl.cancel()
        self.assertTrue(ctl.is_cancelled())
        # cancel must release a paused driver
        self.assertTrue(ctl.wait_while_paused(timeout=0.01))

    def test_lift_cmd(self):
        lift = SilhouetteCameo._lift_cmd
        self.assertEqual(lift(b"M1,2\x03D3,4\x03D5,6\x03"), b"M5,6")
        self.assertIsNone(lift(b"D3,4\x03M5,6\x03"))
        self.assertIsNone(lift(b"FX10\x03"))


class DriverJobControlTest(unittest.TestCase):
    def test_distance_chunks_keep_geometry(self):
        data = b"FX10\x03M0,0\x03D0,1000\x03D300,1000\x03M5,5\x03"
        chunks = list(SilhouetteCameo._distance_chunks(data, 1024, 100))
        self.assertTrue(all(travel <= 100 for _, travel in chunks))
        cmds = b"".join(c for c, _ in chunks).split(b"\x03")[:-1]
        self.assertEqual(cmds[:2], [b"FX10", b"M0,0"])
        self.assertEqual(cmds[2:12], [b"D0,%d" % (100 * k) for k in range(1, 11)])
        self.assertEqual(cmds[12:15], [b"D100,1000", b"D200,1000", b"D300,1000"])
        # moves are split as well (1038 SU -> 11 pieces), ending on target
        self.assertEqual(len(cmds[15:]), 11)
        self.assertTrue(all(c[:1] == b"M" for c in cmds[15:]))
        self.assertEqual(cmds[-1], b"M5,5")

    def test_distance_chunks_without_limit_match_byte_chunks(self):
        data = b"".join(b"D%d,%d\x03" % (i, i) for i in range(500))
        chunks = [c for c, _ in SilhouetteCameo._distance_chunks(data, 1024, None)]
        self.assertTrue(all(len(c) <= 1024 for c in chunks))
        self.assertEqual(b"".join(chunks), data)

    def test_short_chunks_cut_the_same_path(self):
        reference = make_cameo()
        plot(reference)
        dev = make_cameo(job_control=JobControl(), chunk_mm=1)
        plot(dev)
        ref, got = cut_data(reference.transport.sent), cut_data(dev.transport.sent)
        self.assertGreater(len(got), len(ref))
        # every original vertex is still reached, in the same order
        it = iter(got)
        self.assertTrue(all(any(g == r for g in it) for r in ref))

    def test_without_control_output_is_unchanged(self):
        plain = make_cameo()
        plot(plain)
        idle = make_cameo(job_control=JobControl())
        plot(idle)
        self.assertEqual(plain.transport.sent, idle.transport.sent)

    def test_pause_lifts_tool_and_completes_job(self):
        reference = make_cameo()
        plot(reference)
        # the first chunk of long_job() ends with a D: the tool is down
        ctl = ScriptedControl("pause", at=1)
        dev = make_cameo(job_control=ctl)
        plot(dev)

        self.assertGreater(ctl.checkpoints, 2)
        self.assertEqual(ctl.waits, 1)
        expected = cut_data(reference.transport.sent)
        got = cut_data(dev.transport.sent)
        # exactly one extra command: the lift, an M at the last D position
        self.assertEqual(len(got), len(expected) + 1)
        extra = next(i for i, (a, b) in enumerate(zip(got, expected)) if a != b)
        self.assertEqual(got[extra], b"M" + got[extra - 1][1:])
        self.assertEqual(got[:extra] + got[extra + 1:], expected)

    def test_pause_after_move_sends_nothing_extra(self):
        reference = make_cameo()
        plot(reference)
        # the second chunk of long_job() ends with an M: the tool is up
        ctl = ScriptedControl("pause", at=2)
        dev = make_cameo(job_control=ctl)
        plot(dev)
        self.assertEqual(ctl.waits, 1)
        self.assertEqual(cut_data(dev.transport.sent),
                         cut_data(reference.transport.sent))

    def test_cancel_stops_lifts_and_parks(self):
        reference = make_cameo()
        plot(reference)
        ctl = ScriptedControl("cancel", at=1)
        dev = make_cameo(job_control=ctl)
        with self.assertRaises(JobCancelled):
            plot(dev)

        expected = cut_data(reference.transport.sent)
        got = cut_data(dev.transport.sent)
        self.assertLess(len(got), len(expected) / 2)
        # lift where the tool stopped, then the regular end position
        self.assertEqual(got[-2], b"M" + got[-3][1:])
        self.assertTrue(dev.transport.sent.endswith(b"SO0\x03"))
        # the head is parked below the job, as at the end of a normal cut
        self.assertEqual(got[-1], expected[-1])

    def test_cancel_with_skip_reset_only_lifts(self):
        ctl = ScriptedControl("cancel", at=1)
        dev = make_cameo(job_control=ctl)
        with self.assertRaises(JobCancelled):
            dev.plot(pathlist=long_job(), mediawidth=300, mediaheight=300,
                     skip_reset=True)
        self.assertFalse(dev.transport.sent.endswith(b"SO0\x03"))
        got = cut_data(dev.transport.sent)
        self.assertEqual(got[-1], b"M" + got[-2][1:])


class InterruptTest(unittest.TestCase):
    """Pause / resume / cancel while the device is still busy with a chunk."""

    def busy_cameo(self, ctl, actions, hardware="Silhouette_Cameo5_Alpha"):
        dev = make_cameo(job_control=ctl, hardware=hardware)
        dev.transport = BusyTransport(lambda n: actions.get(n, lambda: None)())
        return dev

    def test_pause_and_resume_send_interrupts(self):
        reference = make_cameo()
        plot(reference)
        ctl = JobControl()
        dev = self.busy_cameo(ctl, {2: ctl.pause})
        timer = threading.Timer(0.2, ctl.resume)
        timer.start()
        plot(dev)
        timer.join()
        sent = dev.transport.sent
        self.assertEqual(sent.count(b"\x1b\x07"), 1)
        self.assertEqual(sent.count(b"\x1b\x08"), 1)
        self.assertLess(sent.index(b"\x1b\x07"), sent.index(b"\x1b\x08"))
        self.assertNotIn(b"\x1b\x09", sent)
        self.assertEqual(cut_data(sent), cut_data(reference.transport.sent))

    def test_cancel_sends_pause_then_cancel_and_stops(self):
        ctl = JobControl()
        dev = self.busy_cameo(ctl, {2: ctl.cancel})
        with self.assertRaises(JobCancelled):
            plot(dev)
        sent = dev.transport.sent
        self.assertIn(b"\x1b\x07\x1b\x09", sent)
        after = sent[sent.index(b"\x1b\x09") + 2:]
        # nothing but status requests after the cancel: the device aborts itself
        self.assertEqual(after.replace(b"\x1b\x05", b""), b"")

    def test_older_models_get_no_interrupts(self):
        ctl = JobControl()
        dev = self.busy_cameo(ctl, {2: ctl.cancel}, hardware="Silhouette_Cameo3")
        with self.assertRaises(JobCancelled):
            plot(dev)
        sent = dev.transport.sent
        for code in (b"\x1b\x07", b"\x1b\x08", b"\x1b\x09"):
            self.assertNotIn(code, sent)
        self.assertTrue(sent.endswith(b"SO0\x03"))  # parked by software


class ExtensionJobControlTest(unittest.TestCase):
    def setUp(self):
        self.e = SendtoSilhouette()

    @mock.patch("sendto_silhouette.JobControlWindow")
    def test_window_only_for_real_device(self, window):
        dev = mock.Mock()
        self.e.parse_arguments(["--dry_run=true"])
        self.assertIsNone(self.e.start_job_control(dev))
        self.e.parse_arguments(["--pause_cancel=false"])
        self.assertIsNone(self.e.start_job_control(dev))
        self.e.parse_arguments([])
        self.assertIsNone(self.e.start_job_control(mock.Mock(transport=None)))
        window.assert_not_called()

        self.assertIs(self.e.start_job_control(dev), window.return_value)
        self.e.stop_job_control()
        window.return_value.close.assert_called_once_with()
        self.assertIsNone(self.e.job_control)

    @mock.patch("sendto_silhouette.JobControlWindow",
                side_effect=OSError("no display"))
    def test_window_failure_does_not_abort(self, window):
        self.e.parse_arguments([])
        self.e.report = mock.Mock()
        self.assertIsNone(self.e.start_job_control(mock.Mock()))
        self.assertEqual(self.e.report.call_args.args[1], "log")

    def test_effect_closes_window_when_cutting_fails(self):
        control = mock.Mock()
        self.e.job_control = control
        with mock.patch.object(self.e, "_effect",
                               side_effect=RuntimeError("cut failed")):
            with self.assertRaisesRegex(RuntimeError, "cut failed"):
                self.e.effect()
        control.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
