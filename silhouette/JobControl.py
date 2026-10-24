# (c) 2026 inkscape-silhouette contributors
# Distribute under GPLv2 or ask.
#
# Pause / cancel support for a running cut job.
#
# The cutter driver (Graphtec.SilhouetteCameo.safe_write) sends the job in
# small chunks and waits for the device to become ready after each one.
# Between two chunks it consults a JobControl object: if the job is paused it
# lifts the tool and waits, if it is cancelled it raises JobCancelled.
#
# JobControlWindow shows "Pause"/"Cancel" buttons in a separate Tk process,
# so that a GUI problem can never disturb the communication with the cutter.
# When this file is executed as a script, it *is* that window process.

import os
import queue
import subprocess
import sys
import threading


class JobCancelled(Exception):
  """Raised by the driver when the user cancelled the running job."""


class JobControl:
  """Thread safe pause / cancel flags, consulted by the driver between chunks."""

  def __init__(self):
    self._resumed = threading.Event()
    self._resumed.set()
    self._cancelled = threading.Event()

  def pause(self):
    self._resumed.clear()

  def resume(self):
    self._resumed.set()

  def cancel(self):
    self._cancelled.set()
    self._resumed.set()   # wake up a paused driver so it can abort

  def is_paused(self):
    return not self._resumed.is_set()

  def is_cancelled(self):
    return self._cancelled.is_set()

  def wait_while_paused(self, timeout=None):
    """Block until resumed or cancelled. Returns True if no longer paused."""
    return self._resumed.wait(timeout)

  def progress(self, done, total):
    """Called by the driver after each chunk. Override to display it."""
    pass

  def notify_paused(self):
    """Called by the driver once the device has actually stopped."""
    pass

  def close(self):
    pass


class JobControlWindow(JobControl):
  """JobControl driven by a small Tk window running in a child process.

     Protocol, one command per line:
       parent -> child (stdin):  "progress <done> <total>", "paused"
       child -> parent (stdout): "pause", "resume", "cancel"
     Closing stdin makes the child exit.
  """

  def __init__(self, title="Silhouette", log=None):
    JobControl.__init__(self)
    self.log = log
    self.proc = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), title],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, bufsize=1)
    self._reader = threading.Thread(target=self._read_commands, daemon=True)
    self._reader.start()

  def _read_commands(self):
    for line in self.proc.stdout:
      cmd = line.strip()
      if cmd == "pause":
        self.pause()
      elif cmd == "resume":
        self.resume()
      elif cmd == "cancel":
        self.cancel()

  def _send(self, line):
    try:
      self.proc.stdin.write(line + "\n")
      self.proc.stdin.flush()
    except (OSError, ValueError):
      pass  # window gone: keep cutting, just without controls

  def progress(self, done, total):
    self._send("progress %d %d" % (done, total))

  def notify_paused(self):
    self._send("paused")

  def close(self):
    try:
      self.proc.stdin.close()
    except (OSError, ValueError):
      pass
    try:
      self.proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
      self.proc.kill()
      self.proc.wait(timeout=2)


def _window_main(title):
  """Child process: show the control window, report button presses."""
  import tkinter as tk
  from tkinter import ttk

  root = tk.Tk()
  root.title(title)
  root.resizable(False, False)
  root.attributes("-topmost", True)

  frame = ttk.Frame(root, padding=12)
  frame.pack(fill="both", expand=True)
  status = tk.StringVar(value="Cutting...")
  ttk.Label(frame, textvariable=status, width=36).pack(anchor="w")
  bar = ttk.Progressbar(frame, length=280, maximum=100)
  bar.pack(fill="x", pady=8)
  buttons = ttk.Frame(frame)
  buttons.pack(fill="x")

  def emit(cmd):
    sys.stdout.write(cmd + "\n")
    sys.stdout.flush()

  def toggle_pause():
    if pause_btn["text"] == "Pause":
      emit("pause")
      status.set("Pausing...")
      pause_btn.config(text="Resume")
    else:
      emit("resume")
      status.set("Cutting...")
      pause_btn.config(text="Pause")

  def cancel():
    emit("cancel")
    status.set("Cancelling...")
    pause_btn.config(state="disabled")
    cancel_btn.config(state="disabled")

  pause_btn = ttk.Button(buttons, text="Pause", command=toggle_pause)
  pause_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))
  cancel_btn = ttk.Button(buttons, text="Cancel", command=cancel)
  cancel_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))
  root.protocol("WM_DELETE_WINDOW", lambda: None)  # use the buttons

  def handle(line):
    if not line:  # stdin closed: the job is over
      root.destroy()
      return
    parts = line.split()
    if parts[0] == "progress" and len(parts) == 3 and int(parts[2]) > 0:
      bar["value"] = 100.0 * int(parts[1]) / int(parts[2])
    elif parts[0] == "paused" and cancel_btn["state"] != "disabled":
      status.set("Paused.")

  # Tk must only be touched from this thread: the stdin reader hands the
  # lines over through a queue that is polled here.
  lines = queue.Queue()

  def read_stdin():
    for line in sys.stdin:
      if line.strip():
        lines.put(line.strip())
    lines.put("")

  def poll():
    while not lines.empty():
      line = lines.get()
      handle(line)
      if not line:
        return
    root.after(100, poll)

  threading.Thread(target=read_stdin, daemon=True).start()
  poll()
  root.mainloop()


if __name__ == "__main__":
  _window_main(sys.argv[1] if len(sys.argv) > 1 else "Silhouette")
