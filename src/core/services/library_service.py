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


# ── Lazy singleton ────────────────────────────────────────────────────────────
_manager = None


def _get_manager():
    global _manager
    if _manager is None:
        from core.library_manager import LibraryManager
        _manager = LibraryManager(str(LIBRARY_ROOT))
    return _manager


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

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_progress(self, ticker: str) -> tuple[int, dict]:
        """
        Return (progress_pct, stats_dict) for a company.

        Like a due diligence checklist completion score:
        - 15% from having enough documents (5 ARs + 5 Transcripts)
        - 35% from reading them
        - 30% from time invested (target: 30h)
        - 20% from deliverables (Excel model + Thesis)
        """
        try:
            return self._mgr.get_company_progress(ticker)
        except Exception:
            return 0, {}

    def get_hours(self, ticker: str) -> float:
        """Return total hours invested in researching a company."""
        try:
            return self._mgr.get_company_hours(ticker)
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

