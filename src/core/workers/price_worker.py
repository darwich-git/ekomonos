"""
core/workers/price_worker.py
==============================
Fetches live prices in a background thread.
Replaces the blocking price_fetcher.fetch_prices() calls in the UI thread.

Usage:
    worker = PriceWorker(fetch_list, companies_manager)
    worker.success.connect(on_prices_ready)   # receives dict {ticker: price}
    worker.start()
"""

from .base_worker import BaseWorker


def _fetch_prices(fetch_list, companies_manager, save_to_db=True, progress_fn=None):
    """
    Fetches prices for all tickers in fetch_list.
    Optionally saves to companies_manager DB.
    Returns dict {ticker: price}.
    """
    from core.price_fetcher import price_fetcher

    if progress_fn:
        progress_fn(10, f"Fetching {len(fetch_list)} prices...")

    prices = price_fetcher.fetch_prices(fetch_list)

    if progress_fn:
        progress_fn(70, "Saving prices...")

    if save_to_db and companies_manager:
        for ticker, price in prices.items():
            companies_manager.update_company(ticker, last_price=price)

    if progress_fn:
        progress_fn(100, "Prices updated.")

    return prices


class PriceWorker(BaseWorker):
    """
    Background worker for fetching live market prices.

    Args:
        fetch_list:        List of dicts [{ticker, primary_exchange, yahoo_ticker}]
        companies_manager: CompaniesManager instance (optional, for DB save)
        save_to_db:        Whether to persist prices after fetch (default: True)

    Emits:
        success(dict)  → {ticker: float_price}
        error(str)     → Error message
        progress(int, str)

    Example:
        self._price_worker = PriceWorker(fetch_list, self.manager)
        self._price_worker.success.connect(self._on_prices_fetched)
        self._price_worker.start()
    """

    def __init__(self, fetch_list: list, companies_manager=None, save_to_db: bool = True):
        super().__init__(_fetch_prices, fetch_list, companies_manager, save_to_db)
