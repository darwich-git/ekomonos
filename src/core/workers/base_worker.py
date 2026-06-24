"""
core/workers/base_worker.py
============================
A reusable, cancellable QThread worker.

Usage:
    def my_heavy_function(arg1, arg2):
        return result

    worker = BaseWorker(my_heavy_function, arg1, arg2)
    worker.success.connect(on_result)
    worker.error.connect(on_error)
    worker.progress.connect(on_progress)   # optional
    worker.start()

    # To cancel a running worker:
    worker.cancel()
"""

import traceback
from PyQt6.QtCore import QThread, pyqtSignal, QObject


class WorkerSignals(QObject):
    """Signals for BaseWorker (must be on a QObject, not QThread directly)."""
    success  = pyqtSignal(object)       # Emitted with the return value of fn
    error    = pyqtSignal(str)          # Emitted with a formatted error string
    progress = pyqtSignal(int, str)     # (percent 0-100, message)
    finished = pyqtSignal()             # Always emitted when thread ends


class BaseWorker(QThread):
    """
    Generic background worker that runs any callable in a QThread.

    Features:
    - Cancellable: call cancel() to stop after the current step.
    - Safe: exceptions are caught and emitted as error signals.
    - Progress reporting: the callable can receive a progress_fn kwarg.
    """

    success  = pyqtSignal(object)
    error    = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn       = fn
        self._args     = args
        self._kwargs   = kwargs
        self._cancelled = False

        # Inject a progress callback into the function if it accepts one
        # Functions can optionally accept progress_fn=None and call it
        self._kwargs.setdefault("progress_fn", self._emit_progress)

    # ── Public API ──────────────────────────────────────────────────────────

    def cancel(self):
        """Request cancellation. The worker checks this flag between steps."""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    # ── QThread entry point ─────────────────────────────────────────────────

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            if not self._cancelled:
                self.success.emit(result if result is not None else True)
        except Exception as e:
            if not self._cancelled:
                msg = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
                self.error.emit(msg)
        finally:
            self.finished.emit()

    # ── Private ─────────────────────────────────────────────────────────────

    def _emit_progress(self, percent: int, message: str = ""):
        if not self._cancelled:
            self.progress.emit(percent, message)
