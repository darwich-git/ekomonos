"""
core/services/library_service.py
==================================
Service layer for the document library (PDFs, Annual Reports, Transcripts...).

Think of it as the research document archive department.
The analyst (UI) asks for documents — never digs through
the filing room (DB) themselves.
"""

from __future__ import annotations
from typing import Optional
from config import LIBRARY_ROOT
from PyQt6.QtCore import QThread, pyqtSignal

# ── Lazy singleton ────────────────────────────────────────────────────────────
_manager = None


def _get_manager():
    global _manager
    if _manager is None:
        from core.library_manager import LibraryManager
        _manager = LibraryManager(str(LIBRARY_ROOT))
    return _manager


# ── Global In-Memory Cache ───────────────────────────────────────────────────
_progress_cache = {}  # {ticker: (progress_pct, stats_dict)}
_hours_cache = {}     # {ticker: hours}


class LibraryPreScanWorker(QThread):
    finished_signal = pyqtSignal(dict, dict)  # Emits (progress_cache, hours_cache)

    def __init__(self, tickers: list[str]):
        super().__init__()
        self.tickers = tickers

    def run(self):
        try:
            from core.library_manager import LibraryManager
            from config import LIBRARY_ROOT
            # Create a dedicated manager instance for thread safety
            mgr = LibraryManager(str(LIBRARY_ROOT))
            
            local_progress = {}
            local_hours = {}
            for t in self.tickers:
                try:
                    pct, stats = mgr.get_company_progress(t)
                    local_progress[t] = (pct, stats)
                except Exception:
                    local_progress[t] = (0, {})
                try:
                    hrs = mgr.get_company_hours(t)
                    local_hours[t] = hrs
                except Exception:
                    local_hours[t] = 0.0
            self.finished_signal.emit(local_progress, local_hours)
        except Exception as e:
            print(f"[LibraryPreScanWorker] Error: {e}")
            self.finished_signal.emit({}, {})


# ── Service ───────────────────────────────────────────────────────────────────

class LibraryService:
    """
    Service layer for managing the document library.

    Usage:
        svc = LibraryService()
        progress, stats = svc.get_progress("MSFT")
        best_doc = svc.get_smart_resume_doc("MSFT")
    """

    def __init__(self):
        self._mgr = _get_manager()

    # ── Cache Management ──────────────────────────────────────────────────────

    def invalidate_cache(self, ticker: Optional[str] = None):
        """Invalidate the cache for a specific ticker, or clear everything if None."""
        global _progress_cache, _hours_cache
        if ticker:
            _progress_cache.pop(ticker, None)
            _hours_cache.pop(ticker, None)
        else:
            _progress_cache.clear()
            _hours_cache.clear()

    def pre_scan_all(self, tickers: list[str], on_complete_callback=None) -> LibraryPreScanWorker:
        """
        Starts a background thread to scan progress and hours for all tickers.
        Updates the global cache when done and triggers the callback.
        """
        worker = LibraryPreScanWorker(tickers)

        def handle_done(prog, hrs):
            global _progress_cache, _hours_cache
            _progress_cache.update(prog)
            _hours_cache.update(hrs)
            if on_complete_callback:
                try:
                    on_complete_callback()
                except Exception as e:
                    print(f"[LibraryService] Error in pre-scan callback: {e}")

        worker.finished_signal.connect(handle_done)
        worker.start()
        return worker

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_progress(self, ticker: str) -> tuple[int, dict]:
        """
        Return (progress_pct, stats_dict) for a company.
        Reads from cache if available.
        """
        if ticker in _progress_cache:
            return _progress_cache[ticker]

        try:
            val = self._mgr.get_company_progress(ticker)
            _progress_cache[ticker] = val
            return val
        except Exception:
            return 0, {}

    def get_hours(self, ticker: str) -> float:
        """
        Return total hours invested in researching a company.
        Reads from cache if available.
        """
        if ticker in _hours_cache:
            return _hours_cache[ticker]

        try:
            val = self._mgr.get_company_hours(ticker)
            _hours_cache[ticker] = val
            return val
        except Exception:
            return 0.0

    def get_smart_resume_doc(self, ticker: str) -> Optional[str]:
        """
        Return the best document to read next for this company.
        Priority: In Progress > Unread Tier 1 (ARs, Transcripts) > Excel
        Like a Bloomberg 'next recommended research' algorithm.
        """
        try:
            return self._mgr.get_smart_resume_doc(ticker)
        except Exception:
            return None

    def get_file_metadata(self, file_path: str) -> Optional[dict]:
        """Return metadata for a specific document."""
        try:
            return self._mgr.get_file_metadata(file_path)
        except Exception:
            return None

    # ── Write ─────────────────────────────────────────────────────────────────

    def update_file_metadata(self, file_path: str, ticker: str, **kwargs) -> bool:
        """Update or insert metadata for a file."""
        try:
            self._mgr.update_file_metadata(file_path, ticker, **kwargs)
            self.invalidate_cache(ticker)
            return True
        except Exception as e:
            print(f"[LibraryService] Error updating metadata for {file_path}: {e}")
            return False

    def mark_file_status(self, file_path: str, ticker: str, status: int) -> bool:
        """
        Set reading status for a document.
        0 = Unread, 1 = In Progress, 2 = Reviewed (Read)
        """
        return self.update_file_metadata(file_path, ticker, status=status)

    # ── Compatibility Expositions ───────────────────────────────────────────

    def get_company_progress(self, ticker: str) -> tuple[int, dict]:
        """Alias for get_progress for backward compatibility."""
        return self.get_progress(ticker)

    def get_company_hours(self, ticker: str) -> float:
        """Alias for get_hours for backward compatibility."""
        return self.get_hours(ticker)

    def get_company_links(self, ticker: str) -> list:
        """Return custom links for a company (default empty list)."""
        return []
