import os
import platform
import ctypes
import subprocess

class PreventSleep:
    def __init__(self):
        self.system = platform.system()
        self.prevent_sleep_process = None

    def start(self):
        if self.system == "Windows":
            # Prevent sleep using SetThreadExecutionState
            ctypes.windll.kernel32.SetThreadExecutionState(
                0x80000000 | 0x00000001 | 0x00000002
            )  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        elif self.system == "Darwin":
            # Prevent sleep using caffeinate command on macOS
            self.prevent_sleep_process = subprocess.Popen(["caffeinate"])
        elif self.system == "Linux":
            # Prevent sleep using DBus (Linux)
            subprocess.Popen(
                "dbus-send --session --print-reply --dest=org.freedesktop.ScreenSaver "
                "/org/freedesktop/ScreenSaver org.freedesktop.ScreenSaver.Inhibit "
                'string:"python_script" string:"Prevent sleep"',
                shell=True,
            )

    def stop(self):
        if self.system == "Windows":
            # Reset sleep settings
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)  # ES_CONTINUOUS
        elif self.system == "Darwin" and self.prevent_sleep_process:
            # Terminate the caffeinate process
            self.prevent_sleep_process.terminate()
        elif self.system == "Linux":
            # Release sleep inhibition on Linux
            subprocess.Popen(
                "dbus-send --session --print-reply --dest=org.freedesktop.ScreenSaver "
                "/org/freedesktop/ScreenSaver org.freedesktop.ScreenSaver.UnInhibit",
                shell=True,
            )

