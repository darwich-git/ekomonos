"""
core/services/price_service.py
================================
Service layer for fetching and caching live market prices.

Think of it as the market data terminal. Any screen that
needs a price asks here — never calls Yahoo Finance directly.

This service also maintains an in-memory price cache so that
multiple widgets don't all trigger separate network requests
for the same ticker.
"""

from __future__ import annotations
from typing import Optional
from datetime import datetime, timedelta


class PriceService:
    """
    Manages market price fetching with an in-memory cache.

    Cache TTL: 5 minutes by default. Like a Bloomberg snapshot —
    you don't re-request a quote that's less than 5 minutes old.

    Usage:
        svc = PriceService()

        # Fetch many at once (efficient — one HTTP session):
        prices = svc.fetch_prices(fetch_list)

        # Get a cached price without network call:
        price = svc.get_cached_price("MSFT")
    """

    # Cache TTL — how long a price is considered fresh
    CACHE_TTL_MINUTES = 5

    def __init__(self):
        self._cache: dict[str, tuple[float, datetime]] = {}  # {ticker: (price, timestamp)}

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_cached_price(self, ticker: str) -> Optional[float]:
        """
        Return the cached price for a ticker if it's still fresh.
        Returns None if no cached price or if stale.
        """
        if ticker not in self._cache:
            return None
        price, timestamp = self._cache[ticker]
        age = datetime.now() - timestamp
        if age > timedelta(minutes=self.CACHE_TTL_MINUTES):
            return None  # Stale — like a quote older than 5 minutes
        return price

    def get_all_cached_prices(self) -> dict[str, float]:
        """Return all currently cached (fresh) prices as {ticker: price}."""
        now = datetime.now()
        ttl = timedelta(minutes=self.CACHE_TTL_MINUTES)
        return {
            ticker: price
            for ticker, (price, ts) in self._cache.items()
            if now - ts <= ttl
        }

    # ── Fetch ─────────────────────────────────────────────────────────────────

    def fetch_prices(self, fetch_list: list[dict]) -> dict[str, float]:
        """
        Fetch live prices for a list of companies.
        fetch_list: [{ticker, primary_exchange, yahoo_ticker, currency}, ...]
        Returns: {ticker: float_price}

        Results are stored in the in-memory cache automatically.
        SLOW — should be called from a PriceWorker, not the UI thread.
        """
        try:
            from core.price_fetcher import price_fetcher
            prices = price_fetcher.fetch_prices(fetch_list)

            # Store in cache with timestamp
            now = datetime.now()
            for ticker, price in prices.items():
                self._cache[ticker] = (price, now)

            return prices

        except Exception as e:
            print(f"[PriceService] Error fetching prices: {e}")
            return {}

    def fetch_single(self, ticker: str, exchange: str = "", yahoo_ticker: str = "") -> Optional[float]:
        """
        Fetch price for a single ticker.
        Checks cache first — only makes a network call if stale.
        """
        cached = self.get_cached_price(ticker)
        if cached is not None:
            return cached

        fetch_list = [{"ticker": ticker, "primary_exchange": exchange, "yahoo_ticker": yahoo_ticker}]
        prices = self.fetch_prices(fetch_list)
        return prices.get(ticker)

    # ── Write ─────────────────────────────────────────────────────────────────

    def update_cache(self, prices: dict[str, float]):
        """
        Manually insert prices into the cache (e.g., after loading from DB).
        Useful on startup when we already have recent prices stored.
        """
        now = datetime.now()
        for ticker, price in prices.items():
            self._cache[ticker] = (price, now)

    def invalidate(self, ticker: str | None = None):
        """
        Invalidate the cache for a specific ticker, or clear everything.
        Like forcing a Bloomberg refresh.
        """
        if ticker:
            self._cache.pop(ticker, None)
        else:
            self._cache.clear()
