from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, 
                             QTableWidgetItem, QLabel, QPushButton, QHeaderView, QFrame,
                             QMessageBox, QInputDialog, QComboBox, QMenu, QProgressBar, 
                             QStyledItemDelegate, QStyle, QStyleOptionViewItem)
from PyQt6 import sip
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QColor, QFont, QAction, QBrush, QPen
import json
import os
from ui.styles import COLORS
from core.services import CompanyService, SpecialService
from core.services.price_service import PriceService
from core.workers.base_worker import BaseWorker
from ui.app_state import AppState
from config import LIBRARY_ROOT, DEBUG_MODE, UI_STATE_PATH, ROOT
from core.special_definitions import calculate_global_core
from ui.widgets.special_components.situation_components import calculate_special_progress
from datetime import datetime
import datetime

def debug_log(msg):
    """Only writes to disk when DEBUG_MODE is True. Silent in production."""
    if not DEBUG_MODE:
        return
    try:
        with open("debug_move.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now()} - {msg}\n")
    except: pass


class NumericTableWidgetItem(QTableWidgetItem):
    """QTableWidgetItem that sorts by its stored numeric UserRole value."""
    def __lt__(self, other):
        my_val    = self.data(Qt.ItemDataRole.UserRole)
        other_val = other.data(Qt.ItemDataRole.UserRole)
        # If both have numeric sort values, compare them
        if my_val is not None and other_val is not None:
            try:
                return float(my_val) < float(other_val)
            except (TypeError, ValueError):
                pass
        # Fallback: text comparison
        return self.text().lower() < other.text().lower()

class CompaniesView(QWidget):
    request_open_company = pyqtSignal(str)
    request_open_special_situation = pyqtSignal(str)
    request_edit_company = pyqtSignal(str)
    request_edit_special_situation = pyqtSignal(str)

    # Tickers excluded from price fetching (cash, internal accounts, etc.)
    _EXCLUDE_FROM_PRICES = {"CASH", "LTG", "TITC", "EUR"}
    
    def __init__(self, root_path):
        super().__init__()

        # ── Services (singletons — shared across the whole app) ────────────────
        self._company_svc  = CompanyService()
        self._special_svc  = SpecialService()
        self._price_svc    = PriceService()

        # Keep old managers for backward-compat (populate_table still uses them directly)
        # Will be removed in Phase 3 when we finish the migration
        from core.companies_manager import CompaniesManager
        from core.special_manager import SpecialManager
        self.manager         = self._company_svc._mgr   # alias — same object, no duplicate
        self.special_manager = self._special_svc._mgr

        # Pre-instantiate LibraryManager ONCE (used in populate_table per row)
        from core.library_manager import LibraryManager
        self._lib_mgr = LibraryManager(root_path)

        self.setup_ui()
        self.prices = {}
        self._price_worker = None  # Active price fetch worker

        # Column widths persistence
        self._ui_state_path = str(UI_STATE_PATH)
        self._restoring = False

        # Debounce timer for column width saving
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save_all_widths)

        for tab_info in [self.tab_portfolio, self.tab_watchlist, self.tab_special]:
            h = tab_info["table"].horizontalHeader()
            h.sectionResized.connect(self._schedule_save)

        # Connect to AppState — react to global events
        AppState.get().prices_updated.connect(self._on_global_prices_updated)
        AppState.get().company_deleted.connect(lambda _: self.load_data(fetch_prices=False))
        AppState.get().company_created.connect(lambda _: self.load_data(fetch_prices=False))

        # Initial paint (no price fetch — prices already fetched during splash)
        self.load_data(fetch_prices=False)

    def showEvent(self, event):
        # Refresh view when switching to this tab.
        # No sync or price fetch — just repaint from the current DB state. Fast.
        self.load_data(fetch_prices=False)
        super().showEvent(event)

    def _on_global_prices_updated(self, prices: dict):
        """
        Called when AppState broadcasts fresh prices (e.g. from PriceWorker).
        Just repopulates the tables with the new prices — no heavy reload.
        """
        if sip.isdeleted(self): return
        self.prices.update(prices)
        self._repopulate_tables()


    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        lbl_title = QLabel("COMPANIES COMMAND CENTER")
        lbl_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['text_main']};")
        header.addWidget(lbl_title)
        
        header.addStretch()

        # Status label — shows 'Fetching prices...' / 'Prices updated — 22 tickers'
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(f"color: {COLORS.get('text_dim', '#888')}; font-size: 12px; font-style: italic;")
        header.addWidget(self.lbl_status)
        
        # Refresh Button
        self.btn_refresh = QPushButton("\u21BB SYNC & REFRESH")
        self.btn_refresh.setFixedSize(160, 40)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['primary']};
                border: 2px solid {COLORS['primary']};
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary']};
                color: black;
            }}
            QPushButton:disabled {{
                color: #888;
                border-color: #888;
            }}
        """)
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        header.addWidget(self.btn_refresh)
        
        layout.addLayout(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLORS['border']}; }}
            QTabBar::tab {{
                background: {COLORS['surface']};
                color: {COLORS['text_dim']};
                padding: 12px 25px;
                margin-right: 5px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background: {COLORS['primary']};
                color: black;
            }}
        """)
        
        self.tab_portfolio = self.create_table_tab("Portfolio")
        self.tab_watchlist = self.create_table_tab("Watchlist")
        
        special_cols = ["Situation", "Ticker", "Status", "Strategy", "Price", "Entry Price", "Allocated", "Curr Value", "Gain", "Spread", "IRR", "Target Date", "Progress"]
        self.tab_special = self.create_table_tab("Special", custom_cols=special_cols)
        
        self.tabs.addTab(self.tab_portfolio["widget"], "PORTFOLIO") 
        self.tabs.addTab(self.tab_watchlist["widget"], "WATCHLIST")
        self.tabs.addTab(self.tab_special["widget"], "SPECIAL SITUATIONS")
        
        layout.addWidget(self.tabs)

    def _on_refresh_clicked(self):
        """User clicked Refresh: disable button, run SyncWorker in background, then fetch prices."""
        if hasattr(self, 'btn_refresh'):
            self.btn_refresh.setEnabled(False)
            self.btn_refresh.setText("⏳ Syncing...")
        self._set_status_label("Syncing library...")

        def _do_sync(progress_fn=None):
            self._company_svc.sync_filesystem()
            return True

        from core.workers.base_worker import BaseWorker
        self._sync_worker = BaseWorker(_do_sync)
        self._sync_worker.success.connect(self._on_sync_done)
        self._sync_worker.error.connect(self._on_sync_error)
        self._sync_worker.start()

    def _on_sync_done(self, _):
        """Sync finished — now kick off async price fetch."""
        if hasattr(self, 'btn_refresh') and not sip.isdeleted(self.btn_refresh):
            self.btn_refresh.setText("\u21BB SYNC & REFRESH")
            self.btn_refresh.setEnabled(True)
        self._set_status_label("Sync complete — fetching prices...")
        self._start_async_price_fetch()

    def _on_sync_error(self, error_msg: str):
        """Sync failed — re-enable button and show error."""
        if hasattr(self, 'btn_refresh') and not sip.isdeleted(self.btn_refresh):
            self.btn_refresh.setText("\u21BB SYNC & REFRESH")
            self.btn_refresh.setEnabled(True)
        self._set_status_label(f"Sync error: {error_msg[:60]}")

    
    class EditableHoverDelegate(QStyledItemDelegate):
        def paint(self, painter, option, index):
            # Create a copy of the style option to modify
            opt = QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)
            
            # Check if cell is effectively editable
            # (We used setFlags to remove ItemIsEditable for read-only cells)
            is_editable = (index.flags() & Qt.ItemFlag.ItemIsEditable)
            
            if not is_editable:
                # READ-ONLY CELLS: STATIC VISUAL
                # Strip all interactive states so it looks 100% static
                opt.state &= ~QStyle.StateFlag.State_Selected
                opt.state &= ~QStyle.StateFlag.State_MouseOver
                opt.state &= ~QStyle.StateFlag.State_HasFocus
                
                # Draw standard (looks like a normal static cell)
                super().paint(painter, opt, index)
                
            else:
                # EDITABLE CELLS: WHITE BG + ORANGE BORDER
                
                # 1. Determine interaction state BEFORE we strip it
                is_selected = (opt.state & QStyle.StateFlag.State_Selected)
                is_hover = (opt.state & QStyle.StateFlag.State_MouseOver)
                has_focus = (opt.state & QStyle.StateFlag.State_HasFocus)
                
                # 2. Strip Selection State for Background Painting
                # We want the background to STAY the item's color (White), not standard blue/gray selection
                opt.state &= ~QStyle.StateFlag.State_Selected
                opt.state &= ~QStyle.StateFlag.State_HasFocus 
                opt.state &= ~QStyle.StateFlag.State_MouseOver # Strip hover for BG paint
                
                # 3. Draw Base (Background + Text)
                super().paint(painter, opt, index)
                
                # Only draw Orange Border on Hover/Focus (NOT Selection if we want "nothing on click")
                # But user said "when I pass the mouse the frame turns orange". 
                # "if I click nothing happens". 
                # So only is_hover draws border. 
                # is_selected should draw nothing extra.
                
                if is_hover: # Only Hover!
                    painter.save()
                    # Orange Border #FF9800
                    pen = QPen(QColor("#FF9800"), 2)
                    painter.setPen(pen)
                    painter.drawRect(opt.rect.adjusted(1, 1, -1, -1))
                    painter.restore()

                    # Draw inside the rect so it doesn't overlap excessively
                    painter.setPen(pen)
                    painter.drawRect(opt.rect.adjusted(1, 1, -1, -1))
                    painter.restore()
    def create_table_tab(self, category_name, custom_cols=None):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        table = QTableWidget()
        # Cols: Ticker, Quote, Ccy, Shares, Avg Price, Money In, Mkt Value, Fair, Diff, Reinforce, Reduce, Pot 5y, CAGR, Progress, Last Upd, Metric
        if custom_cols:
            self.cols = custom_cols
        else:
            self.cols = ["Ticker", "Quote", "Ccy", "Shares", "Avg Price", "Money In", "Mkt Value", 
                    "Fair Value", "Fair 5y", "Diff %", "Reinforce", "Reduce", 
                    "CAGR %", "Progress %", "Last Upd", "Metric"]
        
        table.setColumnCount(len(self.cols))
        table.setHorizontalHeaderLabels(self.cols)
        
        # Header Style
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive) 
        header.setDefaultSectionSize(70) # Compact columns to prevent massive window width
        header.setStretchLastSection(True) 
        header.setStyleSheet(f"QHeaderView::section {{ background-color: {COLORS['primary']}; color: black; font-weight: bold; border: 1px solid #555; padding: 2px; font-size: 11px; }}")
        
        table.verticalHeader().setVisible(False) # Hide Row Numbers
        
        # TABLE STYLESHEET (Remove default hover/selection background to fix "Red" issue)
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['surface']}; 
                color: {COLORS['text_main']}; 
                gridline-color: {COLORS['border']}; 
                font-size: 11px;
            }}
            QTableWidget::item:selected {{
                background-color: #FF9800; /* FORCE ORANGE */
                color: black; 
                gridline-color: {COLORS['border']}; 
                font-size: 11px;
                selection-background-color: #FF9800; /* DOUBLE FORCE */
                selection-color: black;
            }}
            QTableWidget::item:hover {{
                /* background-color: transparent; REMOVED to fix Black Cell issue */
                border: 1px solid #777; /* Subtle border instead */
            }}
        """)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # FIX ERR-06 & NAVIGATION ISSUES:
        # Reverting to Standard Triggers (V5.1 Style)
        # We rely on Item Flags to prevent editing in Col 0, not global triggers.
        table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.AnyKeyPressed)
        
        # Context Menu
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos, t=table: self.open_context_menu(pos, t))
        
        table.verticalHeader().setDefaultSectionSize(28) # Compact rows
        
        # Sorting
        # table.setSortingEnabled(True) # DISABLED FOR STABILITY
        
        # Manual Double Click Handler via Event Filter (The "Nuclear-Nuclear" Option)
        # REVERTED due to CRASH (Step 995)
        # table.installEventFilter(self)
        
        # Connect Double Click for Navigation
        # Use UNIQUE connection to avoid duplicates
        try: table.cellDoubleClicked.disconnect()
        except: pass
        
        table.cellDoubleClicked.connect(
            lambda r, c: self.on_table_double_click(r, c, table, category_name)
        )
        # Edit Connect
        table.itemChanged.connect(self.on_item_changed)
        
        layout.addWidget(table)
        
        # Apply Custom Delegate
        # FIX ERR-08: Ensure Delegate is used!
        delegate = self.EditableHoverDelegate(table)
        table.setItemDelegate(delegate)
        table.setMouseTracking(True) # REQUIRED for hover events
        
        return {"widget": widget, "table": table, "category": category_name}

    def _load_ui_state(self):
        """Loads the ui_state.json file or returns an empty dict."""
        try:
            path = os.path.normpath(self._ui_state_path)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[ColWidths] Load error: {e}")
        return {}

    def _save_ui_state(self, state):
        """Saves the full ui_state dict to disk."""
        try:
            path = os.path.normpath(self._ui_state_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[ColWidths] Save error: {e}")

    def _schedule_save(self, *args):
        """Called on sectionResized. Skips if restoring; otherwise debounces save."""
        if self._restoring:
            return
        # Restart the debounce timer (400ms after last resize event)
        self._save_timer.start(400)

    def _do_save_all_widths(self):
        """Actually saves column widths for all tables to disk."""
        try:
            state = self._load_ui_state()
            for tab_info in [self.tab_portfolio, self.tab_watchlist, self.tab_special]:
                table = tab_info["table"]
                header = table.horizontalHeader()
                cat = tab_info["category"]
                widths = [header.sectionSize(i) for i in range(header.count())]
                state[f"col_widths_{cat}"] = widths
            self._save_ui_state(state)
            print(f"[ColWidths] Saved column widths to disk.")
        except Exception as e:
            print(f"[ColWidths] Error in _do_save_all_widths: {e}")

    def _restore_col_widths(self, table, category_name):
        """Restores saved column widths to a table after it has been populated."""
        try:
            state = self._load_ui_state()
            widths = state.get(f"col_widths_{category_name}")
            if not widths:
                return
            header = table.horizontalHeader()
            self._restoring = True
            for i, w in enumerate(widths):
                if i < header.count() and isinstance(w, int) and w > 0:
                    header.resizeSection(i, w)
            # Delay resetting the flag to catch Qt's deferred stretch events
            QTimer.singleShot(150, self._clear_restoring)
        except Exception as e:
            self._restoring = False
            print(f"[ColWidths] Restore error for {category_name}: {e}")

    def _clear_restoring(self):
        """Clears the _restoring flag after Qt has finished its internal layout."""
        self._restoring = False

    def load_data(self, fetch_prices=True):
        """Load and display all company data.

        fetch_prices=False  -> Fast path: repaint from DB/cache only. Used by showEvent.
        fetch_prices=True   -> Full path: sync filesystem + async price fetch. Used by Refresh btn.
        """
        if sip.isdeleted(self) or sip.isdeleted(self.tabs):
            return
        try:
            if not self.isVisible():
                pass
        except RuntimeError:
            return

        try:
            if fetch_prices:
                # ── Full Refresh path: sync filesystem first (still needed once per session) ──
                # Then kick off an async price fetch— UI stays responsive.
                self._company_svc.sync_filesystem()
                self._start_async_price_fetch()

            # Paint tables immediately with cached/DB prices (fast)
            self._repopulate_tables()

        except RuntimeError:
            return
        except Exception as e:
            debug_log(f"Error in load_data: {e}")
            import traceback
            traceback.print_exc()

    def _build_fetch_list(self) -> list[dict]:
        """Build the list of tickers + metadata needed for price fetching."""
        all_companies = self._company_svc.get_all()
        seen = set()
        fetch_list = []

        for c in all_companies:
            t = c.get('ticker', '')
            if t and t not in seen and t.upper() not in self._EXCLUDE_FROM_PRICES:
                fetch_list.append({
                    'ticker':           t,
                    'primary_exchange': c.get('primary_exchange', ''),
                    'yahoo_ticker':     c.get('yahoo_ticker', ''),
                })
                seen.add(t)

        for s in self._special_svc.get_all():
            tickers_dict = s.get('tickers', {})
            specific     = s.get('specific_data', {})
            yahoo_ovr    = specific.get('yahoo_tickers', {}) if isinstance(specific, dict) else {}

            for role in ('target', 'acquirer'):
                base  = tickers_dict.get(role) if isinstance(tickers_dict, dict) else None
                final = yahoo_ovr.get(role, base)
                if final and final not in seen:
                    fetch_list.append({'ticker': final, 'primary_exchange': ''})
                    seen.add(final)

        return fetch_list

    def _start_async_price_fetch(self):
        """Launch a background worker to fetch prices. UI stays completely responsive."""
        # Cancel previous worker if still running
        if self._price_worker and self._price_worker.isRunning():
            self._price_worker.cancel()
            self._price_worker.wait(100)

        fetch_list = self._build_fetch_list()
        if not fetch_list:
            return

        self._set_status_label(f"Fetching prices for {len(fetch_list)} tickers...")

        def _do_fetch(fetch_list, progress_fn=None):
            """Runs in background thread."""
            from core.price_fetcher import price_fetcher
            prices = price_fetcher.fetch_prices(fetch_list)

            # Currency conversion for GBP pence tickers
            all_co = self._company_svc.get_all()
            curr_map = {c['ticker']: c.get('currency', '') for c in all_co}
            result = {}
            for tick, p in prices.items():
                ccy = curr_map.get(tick, '')
                if 'GBP.X' in ccy or 'British Pence' in ccy:
                    p = p / 100.0
                result[tick] = p
            return result

        self._price_worker = BaseWorker(_do_fetch, fetch_list)
        self._price_worker.success.connect(self._on_prices_fetched)
        self._price_worker.error.connect(lambda e: self._set_status_label(f"Price fetch error: {e[:60]}"))
        self._price_worker.start()

    def _on_prices_fetched(self, prices: dict):
        """Called in UI thread when PriceWorker finishes."""
        if sip.isdeleted(self): return

        self.prices.update(prices)

        # Save to DB
        self._company_svc.update_prices_bulk(prices)

        # Broadcast to all other widgets via AppState
        AppState.get().set_prices(prices)

        self._set_status_label(f"Prices updated — {len(prices)} tickers")
        self._repopulate_tables()

    def _set_status_label(self, msg: str):
        """Update the status label in the header (if it exists)."""
        try:
            if hasattr(self, 'lbl_status') and not sip.isdeleted(self.lbl_status):
                self.lbl_status.setText(msg)
        except Exception:
            pass

    def _repopulate_tables(self):
        """Repopulate all three tabs from DB + cached prices. Fast — no network calls."""
        if sip.isdeleted(self) or sip.isdeleted(self.tabs):
            return

        tabs = [self.tab_portfolio, self.tab_watchlist, self.tab_special]

        for i, tab_info in enumerate(tabs):
            cat = tab_info["category"]
            try:
                if cat == "Special":
                    rows = self._special_svc.get_all()
                    self.tabs.setTabText(i, f"SPECIAL ({len(rows)})")
                    self.populate_special_table(tab_info["table"], rows)
                    continue

                rows = self._company_svc.get_all() if cat != "Portfolio" and cat != "Watchlist" \
                    else self._company_svc.get_portfolio() if cat == "Portfolio" \
                    else self._company_svc.get_watchlist()

                if cat == "Watchlist":
                    special_tickers = {
                        s.get('tickers', {}).get('target')
                        for s in self._special_svc.get_all()
                        if isinstance(s.get('tickers'), dict)
                    } - {None}
                    rows = [r for r in rows if r.get('ticker') not in special_tickers]

                self.tabs.setTabText(i, f"{cat.upper()} ({len(rows)})")

                try: tab_info["table"].itemChanged.disconnect(self.on_item_changed)
                except Exception: pass

                self.populate_table(tab_info["table"], rows)
                tab_info["table"].itemChanged.connect(self.on_item_changed)

            except RuntimeError:
                return
            except Exception as e:
                debug_log(f"Error repopulating tab {cat}: {e}")
                import traceback
                traceback.print_exc()
    def format_number(self, value, is_currency=True):
        """
        Smart Formatter:
        - Commas for thousands (1,000)
        - If value > 500: No decimals (526)
        - If value < 500: 2 decimals (65.23)
        """
        try:
            val = float(value)
        except: return str(value)
        
        if val == 0: return "-" # Clean 0
        
        if val > 500:
            return f"{val:,.0f}"
        else:
            return f"{val:,.2f}"

    def populate_table(self, table, data):
        debug_log(f"Entering populate_table with {len(data)} rows")
        table.setRowCount(0)
        table.setSortingEnabled(False)
        
        # Colors
        col_read_only = QColor("#D3D3D3")
        col_editable = QColor("white")
        col_text_ro = QColor("black")
        col_text_edit = QColor("black") # Restored
        col_first_col = QColor("#555555") # Lighter Gray for first column
        col_text_white = QColor("white")
        
        # Use the pre-created LibraryManager instance (instantiated once in __init__).
        # Previously this block created a NEW LibraryManager on EVERY table render — very expensive.
        lib_mgr = self._lib_mgr
        debug_log(f"Populating table with {len(data)} rows.")
        
        for row_data in data:
            try:
                # --- SAFETY: Pre-Check Critical Data ---
                ticker = row_data.get('ticker')
                debug_log(f"Populating row for {ticker}")
                if not ticker: 
                     print("Skipping row with no ticker")
                     continue
                
                # --- END SAFETY ---
                
                row = table.rowCount()
                table.insertRow(row)
                
                # Safer Get with Defaults
                price = float(row_data.get('last_price') or 0.0)
                shares = int(row_data.get('shares_count') or 0)
                cost = float(row_data.get('cost_basis') or 0.0)
                fv = float(row_data.get('fair_value') or 0.0)
                pot5y = float(row_data.get('potential_5y') or 0.0)
                metric = row_data.get('metric_type') or "P/E"
                
                # --- FEAT-05: GBP.X Logic ---
                # check currency
                ccy = str(row_data.get('currency', '')).upper()
                if "GBP.X" in ccy:
                    price = price / 100.0
                    # cost basis usually is also in pence? assume yes for consistency
                    # cost = cost / 100.0 # user didn't specify cost, but let's assume price mainly
                
                # Last Update Logic
                last_upd = self.manager.calculate_last_update(ticker)
                
                # Calculations with zero checks
                mkt_val = price * shares
                avg_price = (cost / shares) if shares > 0 else 0.0
                
                reinforce = fv * 0.8
                reduce_val = fv * 1.1
                diff_pct = ((price - fv) / fv * 100) if fv != 0 else 0.0
                    
                # CAGR
                cagr = 0.0
                if price > 0 and pot5y > 0:
                    try:
                        cagr = ((pot5y / price) ** (1/5)) - 1
                    except: cagr = 0.0
                
                # Thesis Progress
                pct_prog = 0
                try:
                    pct_prog, _ = lib_mgr.get_company_progress(ticker)
                except: pass
                
                # --- Items Helper ---
                def create_item(val_str, editable=False, bg=col_read_only, align_right=True, sort_val=None):
                    item = NumericTableWidgetItem(val_str)
                    if align_right: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    else: item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    if sort_val is not None:
                        item.setData(Qt.ItemDataRole.UserRole, sort_val)
                    if not editable:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        item.setBackground(bg)
                        item.setForeground(col_text_ro)
                    else:
                        item.setBackground(col_editable)
                        item.setForeground(col_text_edit)
                    return item

                # 0 Ticker (text sort — no UserRole needed)
                item_ticker = NumericTableWidgetItem(ticker)
                item_ticker.setData(Qt.ItemDataRole.UserRole, ticker)
                item_ticker.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item_ticker.setFlags(item_ticker.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item_ticker.setBackground(col_first_col)
                item_ticker.setForeground(col_text_white)
                item_ticker.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                table.setItem(row, 0, item_ticker)
                
                # 1 Quote — colour: green if price < reinforce, red if price > reduce
                item_quote = create_item(self.format_number(price), sort_val=price)
                if reinforce > 0 and price <= reinforce:
                    item_quote.setForeground(QColor("#27ae60"))   # green
                elif reduce_val > 0 and price >= reduce_val:
                    item_quote.setForeground(QColor("#e74c3c"))   # red
                else:
                    item_quote.setForeground(col_text_ro)
                table.setItem(row, 1, item_quote)
                
                # 2 Ccy (text)
                ccy_full = row_data.get('currency') or ""
                ccy_code = ccy_full.split(" - ")[0].split(" ")[0]
                table.setItem(row, 2, create_item(ccy_code, False, col_read_only, False, sort_val=ccy_code))
                
                # 3 Shares
                table.setItem(row, 3, create_item(f"{shares}", True, sort_val=shares))
                
                # 4 Avg Price
                table.setItem(row, 4, create_item(self.format_number(avg_price), sort_val=avg_price))
                
                # 5 Money In
                table.setItem(row, 5, create_item(self.format_number(cost), True, sort_val=cost))
                
                # 6 Mkt Value
                table.setItem(row, 6, create_item(self.format_number(mkt_val), sort_val=mkt_val))
                
                # 7 Fair Value
                table.setItem(row, 7, create_item(f"{fv:.2f}", True, sort_val=fv))
                
                # 8 Fair 5y
                table.setItem(row, 8, create_item(f"{pot5y:.2f}", True, sort_val=pot5y))
                
                # 9 Diff %
                item_diff = create_item(f"{diff_pct:.1f}%", sort_val=diff_pct)
                if diff_pct < 0: item_diff.setForeground(QColor("green"))
                else: item_diff.setForeground(QColor("red"))
                table.setItem(row, 9, item_diff)
                
                # 10 Reinforce
                table.setItem(row, 10, create_item(self.format_number(reinforce), sort_val=reinforce))
                
                # 11 Reduce
                table.setItem(row, 11, create_item(self.format_number(reduce_val), sort_val=reduce_val))
                
                # 12 CAGR
                item_cagr = create_item(f"{cagr*100:.1f}%", sort_val=cagr)
                if cagr < 0.15: item_cagr.setBackground(QColor("#FFCDD2"))
                else: item_cagr.setBackground(QColor("#C8E6C9"))
                table.setItem(row, 12, item_cagr)
                
                # 13 Progress (Progress Bar)
                pbar = QProgressBar()
                pbar.setValue(pct_prog)
                pbar.setAlignment(Qt.AlignmentFlag.AlignCenter) 
                pbar.setFormat("%p%") 
                pbar.setStyleSheet(f"""
                    QProgressBar {{
                        border: 0px;
                        border-radius: 4px;
                        text-align: center;
                        background-color: #E0E0E0;
                        color: black; 
                        font-weight: bold;
                        margin: 2px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {COLORS['primary']};
                        border-radius: 4px;
                    }}
                """)
                table.setCellWidget(row, 13, pbar)
                # Hidden sort item for Progress column (enables sorting on widget column)
                item_prog = NumericTableWidgetItem(f"{pct_prog}")
                item_prog.setData(Qt.ItemDataRole.UserRole, pct_prog)
                item_prog.setFlags(item_prog.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 13, item_prog)
                table.setCellWidget(row, 13, pbar)  # overlay widget on top
                
                # 14 Last Upd
                table.setItem(row, 14, create_item(str(last_upd), False, col_read_only, False, sort_val=str(last_upd)))
                
                # 15 Metric
                table.setItem(row, 15, create_item(metric, False, col_read_only, False, sort_val=metric)) 

            except Exception as e:
                print(f"CRITICAL ERROR processing row {row_data.get('ticker')}: {e}")
                import traceback
                traceback.print_exc()
                # Do not re-raise. Skip row.

        # Restore saved column widths AFTER populating (survives any Qt internal resets)
        try:
            category = next(
                (t["category"] for t in [self.tab_portfolio, self.tab_watchlist, self.tab_special]
                 if t["table"] is table), None
            )
            if category:
                self._restore_col_widths(table, category)
        except Exception:
            pass

        # Enable user sorting AFTER population (must come last)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSortIndicatorShown(True)

    def populate_special_table(self, table, data):
        try:
            with open(os.path.join(ROOT, "debug_view_v3.txt"), "w") as f:
                f.write(f"VERSION 4 START. Rows: {len(data)}\n")
        except: pass
        
        debug_log(f"Entering populate_special_table with {len(data)} rows")
        table.blockSignals(True) # PREVENT RECURSIVE UPDATES DURING POPULATION
        try:
            table.setSortingEnabled(False) # Disable during populate
            table.setRowCount(0)
            col_read_only = QColor("#D3D3D3")
            col_editable = QColor("white") 
            col_first_col = QColor("#555555") # Lighter Gray for first column
            col_text_white = QColor("white")
            
            # Formatting: Single line, No Wrap
            table.setWordWrap(False)
            
            def create_num_item(val, fmt="{:.2f}", color=None, editable=False):
                if val is None: val = 0.0
                # FORCE STRING DISPLAY
                text_val = fmt.format(val)
                item = QTableWidgetItem(text_val)
                item.setData(Qt.ItemDataRole.DisplayRole, text_val) 
                
                # Store sort value in UserRole for potential custom sorting later
                item.setData(Qt.ItemDataRole.UserRole + 1, val) 
                
                if color: item.setForeground(color)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
                if not editable:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setBackground(col_read_only) 
                    item.setForeground(QColor("black"))
                else: 
                     item.setBackground(col_editable)
                     item.setForeground(QColor("black"))
                    
                return item

            for s in data:
                try:
                    row = table.rowCount()
                    table.insertRow(row)
                    
                    # --- 0. Situation (Title) ---
                    title = s.get('title', 'Unknown')
                    item_title = QTableWidgetItem(title)
                    item_title.setData(Qt.ItemDataRole.UserRole, s.get('id')) # Store ID for later
                    item_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    item_title.setBackground(col_first_col)
                    item_title.setForeground(col_text_white)
                    table.setItem(row, 0, item_title)

                    # --- 1. Ticker ---
                    tickers = s.get('tickers', {})
                    if isinstance(tickers, str):
                        try: tickers = json.loads(tickers)
                        except: tickers = {}
                    
                    t_tick = tickers.get('target', '')
                    a_tick = tickers.get('acquirer', '')
                    display_tick = t_tick
                    if a_tick: display_tick += f" / {a_tick}"
                    if not display_tick and not t_tick and not a_tick:
                            display_tick = "(No Ticker)"
                    
                    item_tick = QTableWidgetItem(display_tick)
                    item_tick.setBackground(col_read_only)
                    item_tick.setForeground(QColor("black"))
                    table.setItem(row, 1, item_tick)

                    # --- 2. Status ---
                    status = s.get('status', 'Pipeline')
                    item_status = QTableWidgetItem(status)
                    item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item_status.setBackground(col_read_only)
                    s_lower = status.lower()
                    if "active" in s_lower: item_status.setForeground(QColor("#4CAF50"))
                    elif "pipeline" in s_lower: item_status.setForeground(QColor("#FFC107"))
                    elif "closed" in s_lower: item_status.setForeground(QColor("#F44336"))
                    elif "basic" in s_lower: item_status.setForeground(QColor("#9B59B6"))
                    table.setItem(row, 2, item_status)

                    # --- 3. Strategy ---
                    item_cat = QTableWidgetItem(s.get('strategy_type', 'Generic'))
                    item_cat.setBackground(col_read_only)
                    item_cat.setForeground(QColor("black"))
                    table.setItem(row, 3, item_cat)
                    
                    # --- 4. Price ---
                    price = 0.0
                    spec_data = s.get('specific_data', {})
                    yahoo_tickers = spec_data.get('yahoo_tickers', {})
                    p_ticker = yahoo_tickers.get('target', t_tick)
                    
                    if p_ticker:
                        if p_ticker in self.prices: price = self.prices[p_ticker]
                        elif p_ticker.upper() in self.prices: price = self.prices[p_ticker.upper()]
                        
                        if price == 0:
                            try: 
                                from core.price_fetcher import price_fetcher
                                price = price_fetcher.get_price(p_ticker)
                            except: pass
                    
                    # GBP.X / Pence Logic
                    # Updated to match AddSituationWizard saving structure
                    currencies = spec_data.get('currencies', {})
                    curr_str = currencies.get('target', '')
                    if not curr_str:
                         curr_str = spec_data.get('target_currency', '') # Backward compat
                    
                    if not curr_str and p_ticker and p_ticker.upper().endswith('.L'):
                         if price > 500: price = price / 100.0
                    elif "GBP.X" in curr_str or "Pence" in curr_str:
                         price = price / 100.0

                    if price > 0:
                         table.setItem(row, 4, create_num_item(price, "{:,.2f}"))
                    else:
                         item_dash = create_num_item(0.0, "-")
                         item_dash.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                         table.setItem(row, 4, item_dash)
                    
                    # --- 5. Entry Price ---
                    entry = float(s.get('entry_price') or 0.0)
                    table.setItem(row, 5, create_num_item(entry, editable=False))

                    # --- 6. Allocated ---
                    alloc = float(s.get('capital_allocated') or 0.0)
                    table.setItem(row, 6, create_num_item(alloc, "{:,.0f}", editable=False))

                    # --- 7. Curr Value ---
                    diff = 0.0
                    if entry > 0 and price > 0: diff = (price - entry) / entry
                    curr = alloc * (1 + diff)
                    table.setItem(row, 7, create_num_item(curr, "{:,.0f}"))

                    # --- 8. Gain ---
                    gain = curr - alloc
                    c_gain = QColor("green") if gain > 0 else QColor("red")
                    table.setItem(row, 8, create_num_item(gain, "{:,.2f}", c_gain))

                    # --- 9. Spread & 10. IRR (Driven by Global Core to match details tab) ---
                    stype = s.get('strategy_type', 'Generic')
                    close_prob = float(spec_data.get('close_probability', 90)) / 100.0
                    deal_val = float(spec_data.get('deal_value') or 0.0)
                    
                    if deal_val <= 0.0:
                        # Fallback for Generic
                        deal_val = float(spec_data.get('target_price') or 0.0)
                        
                    core = calculate_global_core(
                        current_price=price,
                        target_price=deal_val,
                        downside_price=float(spec_data.get('downside_price', 0.0)),
                        target_date=s.get('target_date'),
                        close_probability=close_prob,
                        break_fee_pct=float(spec_data.get('break_fee_pct', 0.0)),
                        entry_price=entry,
                        strategy_type=stype,
                        scenarios={
                            'bear': spec_data.get('scenario_bear', {}),
                            'base': spec_data.get('scenario_base', {}),
                            'bull': spec_data.get('scenario_bull', {})
                        }
                    )
                    
                    spread = core.get('spread', 0.0)
                    irr = core.get('irr_market', 0.0)
                    
                    c_spread = QColor("green") if spread > 0.05 else QColor("red") if spread < 0 else None
                    table.setItem(row, 9, create_num_item(spread*100, "{:.2f}%", c_spread))

                    c_irr = QColor("green") if irr > 0 else QColor("red")
                    table.setItem(row, 10, create_num_item(irr, "{:.2f}%", c_irr))

                    # --- 11. Date ---
                    t_date = s.get('target_date')
                    if hasattr(t_date, 'strftime'): t_str = t_date.strftime("%Y-%m-%d")
                    else: t_str = str(t_date or "-")
                    item_date = QTableWidgetItem(t_str)
                    item_date.setBackground(col_read_only)
                    item_date.setForeground(QColor("black"))
                    table.setItem(row, 11, item_date)

                    # --- 12. Progress ---
                    pct, _ = calculate_special_progress(s)
                    pbar = QProgressBar()
                    pbar.setValue(pct)
                    pbar.setFormat("%p%")
                    pbar.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    pbar.setStyleSheet(f"QProgressBar {{ border: 0px; border-radius: 4px; background-color: #E0E0E0; color: black; font-weight: bold; }} QProgressBar::chunk {{ background-color: {COLORS['primary']}; border-radius: 4px; }}")
                    table.setCellWidget(row, 12, pbar)
                    d_item = QTableWidgetItem(str(pct))
                    d_item.setData(Qt.ItemDataRole.UserRole, pct)
                    table.setItem(row, 12, d_item)

                except Exception as e:
                    print(f"[CompaniesView] Error populating row {row} (ID: {s.get('id')}): {e}")
                    import traceback
                    traceback.print_exc()

            table.setSortingEnabled(True)
            # Resize logic
            self._restoring = True  # prevent saving during these programmatic resizes
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            table.horizontalHeader().setStretchLastSection(True)
            table.setColumnWidth(0, 200)
            self._restoring = False
            
            # Restore saved column widths AFTER populate
            self._restore_col_widths(table, "Special")
        finally:
             table.blockSignals(False)



    def on_table_double_click(self, row, col, table, category):
        # V5.1 Logic Restoration - DIRECT EXECUTION (No Timer)
        
        # DEBUG LOG
        print(f"[DEBUG] Double Click: Row {row}, Col {col}, Cat {category}")
        
        # NAVIGATION (Col 0 Only)
        if col == 0:
            try:
                if category == "Special":
                    # Get ID from Col 0 UserRole
                    item_name = table.item(row, 0)
                    if item_name:
                        sit_id = item_name.data(Qt.ItemDataRole.UserRole)
                        print(f"[DEBUG] Found Special ID: {sit_id}")
                        if sit_id:
                             self.request_open_special_situation.emit(str(sit_id))
                else:
                    # Assume Company Link (Portfolio, Watchlist, etc.)
                    ticker_item = table.item(row, 0)
                    if ticker_item:
                        tk = ticker_item.text()
                        print(f"[DEBUG] DoubleClick TICKER: {tk}")
                        if tk:
                            self.request_open_company.emit(tk)
                            
            except Exception as e:
                print(f"[CRITICAL] Error in Direct Navigation: {e}")
                import traceback
                traceback.print_exc()

        # No need for "CASE 2: EDITING" because standard triggers handle it for other cols.

    def on_item_changed(self, item):
        row = item.row()
        col = item.column()
        table = item.tableWidget()
        
        # Block signals to prevent recursive loops
        table.blockSignals(True)
        try:
            val_str = item.text().replace(",", "").replace("$", "").replace("%", "") # Robust Clean
            
            # --- SPECIAL SITUATIONS TABLE LOGIC ---
            if hasattr(self, "tab_special") and self.tab_special and table is self.tab_special.get("table"):
                # Get Situation ID (Col 0)
                title_item = table.item(row, 0)
                if not title_item: 
                    table.blockSignals(False)
                    return
                sit_id = title_item.data(Qt.ItemDataRole.UserRole)
                if not sit_id: 
                    table.blockSignals(False)
                    return
                
                # Get Context Data
                try: price = float(table.item(row, 4).text().replace("$", "").replace(",", ""))
                except: price = 0.0
                
                try: entry = float(table.item(row, 5).text().replace(",", ""))
                except: entry = 0.0
                
                try: alloc = float(table.item(row, 8).text().replace(",", ""))
                except: alloc = 0.0

                # UPDATE LOGIC
                if col == 5: # Entry Price
                    entry = float(val_str)
                    self.special_manager.update_situation(sit_id, entry_price=entry)
                    item.setText(f"{entry:.2f}")
                    
                elif col == 8: # Allocated
                    alloc = float(val_str)
                    self.special_manager.update_situation(sit_id, capital_allocated=alloc)
                    item.setText(f"{alloc:,.0f}")
                
                # RECALCULATE DEPENDENTS
                # 7 Diff % = (Price - Entry) / Entry
                diff = 0.0
                if entry > 0 and price > 0:
                    diff = (price - entry) / entry
                
                diff_item = table.item(row, 7)
                if diff_item:
                    diff_item.setText(f"{diff*100:.2f}%")
                    if diff > 0: diff_item.setForeground(QColor("green"))
                    else: diff_item.setForeground(QColor("red"))
                
                # 9 Curr Value = Alloc * (1 + diff)
                curr = alloc * (1 + diff)
                curr_item = table.item(row, 9)
                if curr_item:
                    curr_item.setText(f"{curr:,.0f}")
                
                # 10 Gain = Curr - Alloc
                gain = curr - alloc
                gain_item = table.item(row, 10)
                if gain_item:
                    gain_item.setText(f"{gain:,.2f}")
                    if gain > 0: gain_item.setForeground(QColor("green"))
                    else: gain_item.setForeground(QColor("red"))

                table.blockSignals(False)
                return 

            # --- PORTFOLIO TABLE LOGIC (Existing) ---
            ticker_item = table.item(row, 0)
            if not ticker_item: 
                table.blockSignals(False)
                return
            ticker = ticker_item.text()
            
            # Get current values from table for calculation context
            try:
                price = float(table.item(row, 1).text().replace(",", ""))
            except: price = 0.0
            
            try:
                shares_str = table.item(row, 3).text().replace(",", "")
                shares = int(float(shares_str))
            except: shares = 0
            
            try:
                cost_str = table.item(row, 5).text().replace(",", "")
                cost = float(cost_str)
            except: cost = 0.0
            
            try:
                fv_str = table.item(row, 7).text().replace(",", "")
                fv = float(fv_str)
            except: fv = 0.0
            
            try:
                pot_str = table.item(row, 8).text().replace(",", "")
                pot = float(pot_str)
            except: pot = 0.0
            
            # UPDATE LOGIC
            if col == 3: # Shares
                shares = int(float(val_str))
                self.manager.update_company(ticker, shares_count=shares)
                item.setText(f"{shares:,}")
                
            elif col == 5: # Money In (Cost Basis)
                cost = float(val_str)
                self.manager.update_company(ticker, cost_basis=cost)
                item.setText(self.format_number(cost))
                
            elif col == 7: # Fair Value
                fv = float(val_str)
                self.manager.update_company(ticker, fair_value=fv)
                item.setText(self.format_number(fv))
                
            elif col == 8: # Fair 5y (Formerly Pot 5y)
                pot = float(val_str)
                self.manager.update_company(ticker, potential_5y=pot)
                item.setText(self.format_number(pot))
                
            elif col == 15: # Metric
                self.manager.update_company(ticker, metric_type=val_str)
            
            # RECALCULATE DEPENDENTS
            # 4 Avg Price = Cost / Shares
            avg_price = (cost / shares) if shares > 0 else 0.0
            
            # Only update if cells exist
            avg_price_item = table.item(row, 4)
            if avg_price_item:
                avg_price_item.setText(self.format_number(avg_price))
            
            # 6 Mkt Value = Price * Shares
            mkt_val = price * shares
            market_val_item = table.item(row, 6) # Corrected column from 5 to 6
            if market_val_item:
                market_val_item.setText(self.format_number(mkt_val))
            
            # 9 Diff % = (Price - FV) / FV
            diff_pct = ((price - fv) / fv * 100) if fv else 0
            item_diff = table.item(row, 9)
            if item_diff:  # Add null check
                item_diff.setText(f"{diff_pct:.1f}%")
                if diff_pct < 0: item_diff.setForeground(QColor("green")) 
                else: item_diff.setForeground(QColor("red"))
            
            # 10 Reinforce = FV * 0.8
            reinforce = fv * 0.8
            reinforce_item = table.item(row, 10)
            if reinforce_item:  # Add null check
                reinforce_item.setText(self.format_number(reinforce))
            
            # 11 Sell = FV * 1.2
            sell = fv * 1.2
            sell_item = table.item(row, 11)
            if sell_item:  # Add null check
                sell_item.setText(self.format_number(sell))
            
            # 12 Potential %
            pot_pct = ((pot - price) / price * 100) if price else 0
            pot_item = table.item(row, 12)
            if pot_item:  # Add null check
                pot_item.setText(f"{pot_pct:.1f}%")
                if pot_pct > 0: pot_item.setForeground(QColor("green"))
                else: pot_item.setForeground(QColor("red"))
                
        except ValueError:
            pass # Invalid input
        finally:
            table.blockSignals(False)

    def open_context_menu(self, pos, table):
        index = table.indexAt(pos)
        if not index.isValid(): return
        
        row = index.row()
        ticker_item = table.item(row, 0)
        ticker = ticker_item.text()
        
        menu = QMenu()
        move_menu = menu.addMenu("Move to...")
        
        # SANITIZE TICKER (Handle "Microsoft (MSFT)" case)
        if "(" in ticker and ")" in ticker:
            try:
                clean_ticker = ticker.split("(")[-1].strip(")")
                ticker = clean_ticker
            except: pass
            
        for cat in ["Portfolio", "Watchlist", "Special"]:
            a = QAction(cat, self)
            # Use clean ticker
            a.triggered.connect(lambda checked, c=cat, t=ticker: self.move_category(t, c))
            move_menu.addAction(a)
        
        debug_log(f"Opening Context Menu for {ticker}")
        print(f"DEBUG: Opening Context Menu for {ticker}")
        menu.addSeparator()
        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(lambda: self.trigger_edit(table, row))

        menu.exec(table.viewport().mapToGlobal(pos))
        print("DEBUG: Context Menu Closed")
        debug_log("Context Menu Closed")

    def trigger_edit(self, table, row):
        # Determine valid ID/Ticker
        
        # Is this special?
        is_special = False
        sit_id = None
        
        # Check if table is special table
        if hasattr(self, 'tab_special') and table is self.tab_special.get("table"):
            is_special = True
            # In Special Table, ID is now in Column 0 (Situation)
            item = table.item(row, 0)
            if item:
                sit_id = item.data(Qt.ItemDataRole.UserRole)
                if sit_id and is_special:
                    self.request_edit_special_situation.emit(str(sit_id))
                    
        else:
            # Portfolio/Watchlist
            ticker_item = table.item(row, 0)
            if ticker_item:
                self.request_edit_company.emit(ticker_item.text())

    # --- FIX ID Retrieval helper ---
    # I'll enable ID saving in populate logic


    def move_category(self, ticker, category):
        debug_log(f"move_category called for {ticker} -> {category}")
        print(f"DEBUG: move_category called for {ticker} -> {category}")
        try:
            print(f"DEBUG: Calling manager.update_company...")
            self.manager.update_company(ticker, category=category)
            print(f"DEBUG: DB update finished. Scheduling reload...")
            debug_log("DB update finished. Scheduling reload...")
            
            # Helper to refresh safely
            # OPTIMIZATION: Do NOT fetch prices again immediately after move.
            # This makes reload instant and reduces race condition window.
            QTimer.singleShot(200, lambda: self.load_data(fetch_prices=False)) 
        except Exception as e:
            debug_log(f"CRITICAL ERROR Moving Category: {e}")
            from traceback import print_exc
            print_exc()
            QMessageBox.critical(self, "Move Failed", f"Could not move company: {e}")
            QTimer.singleShot(100, self.load_data) 
        except Exception as e:
            print(f"CRITICAL ERROR Moving Category: {e}")
            from traceback import print_exc
            print_exc()
            QMessageBox.critical(self, "Move Failed", f"Could not move company: {e}")

