"""A13 negative containment control; Windows-only, offline, no operational I/O.

The inner Job is deliberately created without KILL_ON_JOB_CLOSE in a *test
supervisor process only*. The outer safety Job remains unchanged.
"""
import ctypes
import os
import sys


def _negative_supervisor():
    if os.name != 'nt':
        raise RuntimeError('Windows required')
    from a11_native.tools import f3_int115_process_control as control
    from a11_native.tools.f3_int115_process_identity import JobTracker
    from f3_int121_a12_boundaries import _supervisor

    def without_kill_on_close(self):
        # Keep the A11 implementation intact on disk; change only this test
        # supervisor's inner Job initialization.
        self.handle = control.wincheck(control.K.CreateJobObjectW(None, None))
        limits = control.ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0
        try:
            control.wincheck(control.K.SetInformationJobObject(
                self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
            import threading
            self.lock = threading.Lock()
            self.tracker = JobTracker(self.handle)
        except BaseException:
            control.K.CloseHandle(self.handle)
            self.handle = None
            raise

    control.Job.__init__ = without_kill_on_close
    _supervisor()


if __name__ == '__main__':
    if sys.argv[1:] == ['--negative-supervisor']:
        _negative_supervisor()
    else:
        raise SystemExit('A13 negative supervisor only')
