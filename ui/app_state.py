"""
ui/app_state.py
================
Global application state singleton.

Any widget can:
  - READ the current state:  AppState.get().active_company
  - CHANGE the state:        AppState.get().set_active_company("MSFT")
  - LISTEN for changes:      AppState.get().company_changed.connect(my_slot)

This replaces the fragile pattern of passing data between widgets via
QTimer.singleShot() or direct method calls across MainWindow.

Example usage in a widget:
    from ui.app_state import AppState

    # Listen for company changes from anywhere in the app
    AppState.get().company_changed.connect(self.on_company_changed)

    # Set the active company (all listeners will be notified automatically)
    AppState.get().set_active_company("AAPL")
"""

from PyQt6.QtCore import QObject, pyqtSignal


class AppState(QObject):
    """
    Singleton that holds the current state of the application
    and broadcasts changes via Qt signals.
    """

    # ── Signals ─────────────────────────────────────────────────────────────
    company_changed         = pyqtSignal(str)    # ticker of newly selected company
    situation_changed       = pyqtSignal(str)    # id of newly selected special situation
    prices_updated          = pyqtSignal(dict)   # {ticker: price} — fresh prices arrived
    library_synced          = pyqtSignal()       # library sync completed
    company_deleted         = pyqtSignal(str)    # ticker of deleted company
    company_created         = pyqtSignal(str)    # ticker of newly created company
    request_create_company  = pyqtSignal(str, str) # ticker, name of newly requested company


    # ── Singleton ────────────────────────────────────────────────────────────
    _instance: "AppState | None" = None

    @classmethod
    def get(cls) -> "AppState":
        """Return the global AppState instance (creates it on first call)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Init ─────────────────────────────────────────────────────────────────
    def __init__(self):
        super().__init__()
        self._active_company:   str  = ""
        self._active_situation: str  = ""
        self._latest_prices:   dict = {}

    # ── Company ──────────────────────────────────────────────────────────────
    @property
    def active_company(self) -> str:
        return self._active_company

    def set_active_company(self, ticker: str):
        """Set the currently focused company and notify all listeners."""
        if ticker == self._active_company:
            return  # No change — don't emit noise
        self._active_company = ticker
        self.company_changed.emit(ticker)

    # ── Special Situation ────────────────────────────────────────────────────
    @property
    def active_situation(self) -> str:
        return self._active_situation

    def set_active_situation(self, situation_id: str):
        """Set the currently focused special situation and notify all listeners."""
        if situation_id == self._active_situation:
            return
        self._active_situation = situation_id
        self.situation_changed.emit(situation_id)

    # ── Prices ───────────────────────────────────────────────────────────────
    @property
    def latest_prices(self) -> dict:
        return self._latest_prices

    def set_prices(self, prices: dict):
        """Store fresh prices and notify all listeners."""
        self._latest_prices.update(prices)
        self.prices_updated.emit(self._latest_prices)

    def get_price(self, ticker: str) -> float:
        """Get the latest known price for a ticker (0.0 if unknown)."""
        return self._latest_prices.get(ticker, 0.0)

    # ── Events ───────────────────────────────────────────────────────────────
    def notify_company_deleted(self, ticker: str):
        """Broadcast that a company was deleted so all views can refresh."""
        if self._active_company == ticker:
            self._active_company = ""
        self.company_deleted.emit(ticker)

    def notify_company_created(self, ticker: str):
        """Broadcast that a new company was created."""
        self.company_created.emit(ticker)

    def notify_library_synced(self):
        """Broadcast that a library sync has completed."""
        self.library_synced.emit()
