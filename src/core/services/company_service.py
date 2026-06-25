"""
core/services/company_service.py
==================================
The ONLY place in the codebase that talks to company data.
No widget or screen should ever call CompaniesManager directly.

Think of it as: the specialist mechanic who knows everything
about the stock portfolio. Receptionists (UI) ask him,
they never go to the storeroom (DB) themselves.

All methods return plain dicts or lists — never SQLAlchemy objects.
This keeps the UI layer completely decoupled from the DB layer.
"""

from __future__ import annotations

import os
from typing import Optional
from config import LIBRARY_ROOT


# ── Lazy singleton pattern ────────────────────────────────────────────────────
# We keep ONE CompaniesManager alive for the whole app lifecycle,
# instead of creating a new instance per widget (the old bug).
_manager = None


def _get_manager():
    global _manager
    if _manager is None:
        from core.companies_manager import CompaniesManager
        _manager = CompaniesManager(str(LIBRARY_ROOT))
    return _manager


# ── Public API ────────────────────────────────────────────────────────────────

class CompanyService:
    """
    Service layer for company data.

    All methods are pure — they receive inputs, return outputs,
    and have no side effects beyond the database.

    Usage:
        svc = CompanyService()
        portfolio = svc.get_portfolio()
        svc.update_price("MSFT", 415.20)
    """

    def __init__(self):
        self._mgr = _get_manager()

    # ── Read ─────────────────────────────────────────────────────────────────

    def get_all(self) -> list[dict]:
        """Return all companies from the library."""
        return self._mgr.get_companies()

    def get_portfolio(self) -> list[dict]:
        """Return Portfolio companies only."""
        return self._mgr.get_companies(category="Portfolio")

    def get_watchlist(self) -> list[dict]:
        """Return Watchlist companies only."""
        return self._mgr.get_companies(category="Watchlist")

    def get_by_ticker(self, ticker: str) -> Optional[dict]:
        """Return a single company by ticker, or None if not found."""
        all_companies = self._mgr.get_companies()
        for c in all_companies:
            if c.get("ticker") == ticker:
                return c
        return None

    def get_tickers_for_price_fetch(self) -> list[dict]:
        """
        Return the minimal data needed to fetch live prices:
        [{ticker, primary_exchange, yahoo_ticker, currency}]
        """
        companies = self._mgr.get_companies()
        return [
            {
                "ticker":           c.get("ticker", ""),
                "primary_exchange": c.get("primary_exchange", ""),
                "yahoo_ticker":     c.get("yahoo_ticker", ""),
                "currency":         c.get("currency", "USD"),
            }
            for c in companies
            if c.get("ticker")
        ]

    # ── Write ────────────────────────────────────────────────────────────────

    def update_price(self, ticker: str, price: float) -> bool:
        """Update the last known price for a company."""
        try:
            self._mgr.update_company(ticker, last_price=price)
            return True
        except Exception as e:
            print(f"[CompanyService] Error updating price for {ticker}: {e}")
            return False

    def update_prices_bulk(self, prices: dict) -> int:
        """
        Update prices for multiple companies at once.
        prices: {ticker: float_price}
        Returns number of successful updates.
        """
        success = 0
        for ticker, price in prices.items():
            if self.update_price(ticker, price):
                success += 1
        return success

    def update_company(self, ticker: str, **kwargs) -> bool:
        """Update company fields. kwargs are field=value pairs."""
        try:
            self._mgr.update_company(ticker, **kwargs)
            return True
        except Exception as e:
            print(f"[CompanyService] Error updating {ticker}: {e}")
            return False

    def delete_company(self, ticker: str) -> bool:
        """Delete a company from the library."""
        try:
            return self._mgr.delete_company(ticker)
        except Exception as e:
            print(f"[CompanyService] Error deleting {ticker}: {e}")
            return False

    # ── Sync ─────────────────────────────────────────────────────────────────

    def sync_filesystem(self) -> bool:
        """
        Sync the library DB with the filesystem.
        SLOW — should only be called from a SyncWorker, never from the UI thread.
        """
        try:
            self._mgr.sync_with_library()
            return True
        except Exception as e:
            print(f"[CompanyService] Sync error: {e}")
            return False

    # ── Rename ───────────────────────────────────────────────────────────────

    def rename_company(self, old_ticker: str, new_ticker: str) -> tuple[bool, str]:
        """
        Rename a company's ticker across database and filesystem.
        Returns (success, message).
        """
        try:
            return self._mgr.rename_company(old_ticker, new_ticker)
        except Exception as e:
            print(f"[CompanyService] Rename error from {old_ticker} to {new_ticker}: {e}")
            return False, str(e)

    # ── Compatibility Expositions ───────────────────────────────────────────

    def add_company(self, ticker: str, name: str, category: str, currency: str, 
                    primary_exchange: str, yahoo_ticker: str, aliases: str, 
                    notes: str, status: str, last_update: str) -> bool:
        """Create or update a company."""
        try:
            self._mgr.add_company(ticker, name, category, currency, primary_exchange, 
                                  yahoo_ticker, aliases, notes, status, last_update)
            return True
        except Exception as e:
            print(f"[CompanyService] Error adding company {ticker}: {e}")
            return False

    def calculate_last_update(self, ticker: str) -> Optional[str]:
        """Return the latest date of activity for a ticker."""
        try:
            return self._mgr.calculate_last_update(ticker)
        except Exception as e:
            print(f"[CompanyService] Error calculating last update for {ticker}: {e}")
            return None

    def sync_with_library(self) -> bool:
        """Alias for sync_filesystem for backward compatibility."""
        return self.sync_filesystem()

    def get_companies(self, category: Optional[str] = None) -> list[dict]:
        """Alias for get_all with optional category filter for compatibility."""
        if category == "Portfolio":
            return self.get_portfolio()
        elif category == "Watchlist":
            return self.get_watchlist()
        elif category:
            return self._mgr.get_companies(category=category)
        return self.get_all()



