"""
core/workers/sync_worker.py
============================
Runs library sync (filesystem + DB) in a background thread.
Replaces the blocking sync_with_library() call that was running on the UI thread.

Usage:
    worker = SyncWorker(companies_manager)
    worker.success.connect(lambda _: companies_view.repopulate())
    worker.start()
"""

from .base_worker import BaseWorker


def _run_sync(companies_manager, progress_fn=None):
    """
    The actual sync logic — executed off the UI thread.
    Returns True on success.
    """
    if progress_fn:
        progress_fn(10, "Scanning library folders...")

    companies_manager.sync_with_library()

    if progress_fn:
        progress_fn(100, "Sync complete.")

    return True


class SyncWorker(BaseWorker):
    """
    Background worker for syncing the company library with the filesystem.

    Example:
        self._sync_worker = SyncWorker(self.companies_manager)
        self._sync_worker.success.connect(self._on_sync_done)
        self._sync_worker.error.connect(lambda e: print("Sync error:", e))
        self._sync_worker.start()
    """

    def __init__(self, companies_manager):
        super().__init__(_run_sync, companies_manager)
