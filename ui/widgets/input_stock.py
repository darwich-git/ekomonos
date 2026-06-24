from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QDateEdit, 
                             QGridLayout, QScrollArea, QFrame, QMessageBox, QDialog, QProgressBar, QScrollArea, QSplitter, QDoubleSpinBox, QFileDialog, QCompleter, QAbstractSpinBox, QApplication)
from PyQt6.QtCore import Qt, QDate, QSize, QTimer, pyqtSignal
from PyQt6 import sip
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QColor
import os
import shutil
import datetime
import re
from ui.styles import COLORS
from core.sne_manager import generate_sne_filename, get_sne_destination_folder, SNE_TYPES, SNE_PERIODS
from core.companies_manager import CompaniesManager
from core.price_fetcher import price_fetcher, EXCHANGE_SUFFIXES
from core.database import init_db, get_session_factory, Company as DBCompany
from core.earnings_manager import EarningsManager

# --- Constants ---
from config import LIBRARY_ROOT as _LIBRARY_ROOT_PATH
LIBRARY_ROOT = str(_LIBRARY_ROOT_PATH)  # str() for os.path compatibility

class NoScrollComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        event.ignore()

class NoScrollDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        event.ignore()

class SmartDateEdit(QLineEdit):
    def __init__(self, parent=None, placeholder="DD-MM-YYYY"):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.textChanged.connect(self.format_date)
        
    def format_date(self, text):
        clean = re.sub(r'[^0-9]', '', text)
        formatted = ""
        if len(clean) > 0:
            formatted = clean[:2]
        if len(clean) > 2:
            formatted += "-" + clean[2:4]
        if len(clean) > 4:
            formatted += "-" + clean[4:8]
            
        if text != formatted:
            self.blockSignals(True)
            self.setText(formatted)
            self.setCursorPosition(len(formatted))
            self.blockSignals(False)

    def text_for_db(self):
        txt = self.text()
        if re.match(r"\d{2}-\d{2}-\d{4}", txt):
            parts = txt.split("-")
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return ""

    def set_from_db(self, db_date):
        if not db_date: 
            self.setText("")
            return
            
        # If it's already a date/datetime object
        if isinstance(db_date, (datetime.date, datetime.datetime)):
            self.setText(db_date.strftime("%d-%m-%Y"))
            return
            
        # If it's a string, try to match YYYY-MM-DD
        if isinstance(db_date, str) and re.match(r"\d{4}-\d{2}-\d{2}", db_date):
            parts = db_date.split("-")
            self.setText(f"{parts[2]}-{parts[1]}-{parts[0]}")
        else:
            self.setText("")

# from core.debug_logger import blackbox # REMOVED to fix startup crash

import os
import traceback
import datetime # Ensure module level access

class LocalBlackBox:
    def __init__(self):
        self.path = "blackbox_crash.log" 
        
    def log(self, msg):
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now()} - INFO - {msg}\n")
        except: pass
        
    def start(self, op):
        self.log(f"START {op}")
        
    def end(self, op, res=""):
        self.log(f"END {op} {res}")
        
    def error(self, msg, e=None):
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now()} - ERROR - {msg}: {e}\n")
        except: pass

blackbox = LocalBlackBox()

from PyQt6.QtCore import pyqtSignal

class NewCompanyDialog(QDialog):
    # Signal to notify parent of deletion (since we are detached)
    company_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        blackbox.log("NewCompanyDialog Initialized")
        blackbox.log("NewCompanyDialog Initialized")
        # ============================================================================
        # CRITICAL: companies_manager MUST NEVER BE None
        # ============================================================================
        # If set to None, delete_company() will crash with:
        # "AttributeError: 'NoneType' object has no attribute 'delete_company'"
        # 
        # This bug was fixed on 2026-02-08 after multiple regressions.
        # DO NOT change this logic without explicit user approval.
        # ============================================================================
        if parent and hasattr(parent, 'companies_manager'):
            self.companies_manager = parent.companies_manager
        else:
            # Fallback: Create local instance to prevent NoneType errors
            # LIBRARY_ROOT is already imported at module level (line 18)
            from core.companies_manager import CompaniesManager
            self.companies_manager = CompaniesManager(LIBRARY_ROOT)
        # ============================================================================
        self.setWindowTitle("Create New Company")
        self.resize(750, 850) # Standardized Size
        self.setMinimumHeight(800)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['surface']}; color: {COLORS['text_main']}; font-family: 'Segoe UI', sans-serif; }}
            QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit {{ 
                background-color: {COLORS['surface_light']}; 
                border: 1px solid {COLORS['border']}; 
                border-radius: 4px; 
                padding: 6px; 
                color: white; 
            }}
            QLabel {{ font-size: 13px; color: white; }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['surface_light']};
                color: white;
                selection-background-color: {COLORS['primary']};
                selection-color: black;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {COLORS['text_dim']};
                margin-right: 5px;
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Form Grid
        form_layout = QGridLayout()
        form_layout.setSpacing(10)
        
        self.txt_name = QLineEdit()
        self.txt_ticker = QLineEdit()
        self.txt_yahoo_ticker = QLineEdit() # New Yahoo Ticker Field
        self.txt_aliases = QLineEdit() # New Aliases Field
        
        # Smart Exchanges (Expanded List)
        self.combo_exchange = NoScrollComboBox()
        # self.combo_exchange = QComboBox() # STANDARD WIDGET ISOLATION
        self.combo_exchange.setEditable(True)
        # Use keys from PriceFetcher
        exchanges = sorted(list(EXCHANGE_SUFFIXES.keys()))
        self.combo_exchange.addItems(exchanges)
        
        # Searchable behavior
        self.combo_exchange.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo_exchange.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.combo_exchange.completer().setFilterMode(Qt.MatchFlag.MatchContains) # Enable "Poland" -> "WSE - Warsaw..."
        self.combo_exchange.setCurrentIndex(-1) # Default Empty

        # Smart Currencies (Expanded List)
        self.combo_currency = NoScrollComboBox()
        # self.combo_currency = QComboBox() # STANDARD WIDGET ISOLATION
        self.combo_currency.setEditable(True)
        currencies = [
            "USD - US Dollar", "EUR - Euro", "GBP - British Pound", "GBP.X - British Pence", "CAD - Canadian Dollar",
            "AUD - Australian Dollar", "JPY - Japanese Yen", "CHF - Swiss Franc",
            "CNY - Chinese Yuan", "HKD - HK Dollar", "SGD - Singapore Dollar",
            "INR - Indian Rupee", "BRL - Brazilian Real", "MXN - Mexican Peso",
            "PLN - Polish Zloty", "SEK - Swedish Krona", "NOK - Norwegian Krone",
            "DKK - Danish Krone", "ZAR - South African Rand", "TRY - Turkish Lira",
            "ILS - Israeli Shekel", "RUB - Russian Ruble", "KRW - South Korean Won",
            "TWD - New Taiwan Dollar", "SAR - Saudi Riyal", "AED - UAE Dirham"
        ]
        self.combo_currency.addItems(sorted(currencies))
        self.combo_currency.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo_currency.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.combo_currency.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.combo_currency.setCurrentIndex(-1) # Default Empty
        
        self.txt_idea = QLineEdit()
        self.txt_ir_web = QLineEdit()
        self.txt_pr_web = QLineEdit()
        
        # New Fields
        self.spin_price = NoScrollDoubleSpinBox()
        # self.spin_price = QDoubleSpinBox() # STANDARD WIDGET ISOLATION
        self.spin_price.setRange(0, 99999.99)
        self.spin_price.setDecimals(2)
        self.spin_price.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons) # No Buttons
        # self.spin_price.setPrefix("$ ") # Generic
        # Date
        self.date_edit = SmartDateEdit()
        self.date_edit.set_from_db(datetime.date.today().strftime("%Y-%m-%d"))
        self.date_edit.setStyleSheet(f"background-color: {COLORS['surface_light']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; padding: 5px; border-radius: 4px;")
        
        self.combo_kpi_type = NoScrollComboBox()
        # self.combo_kpi_type = QComboBox() # STANDARD WIDGET ISOLATION
        self.combo_kpi_type.addItems(["P/S", "EV/EBITDA", "EV/EBIT", "PER", "P/FCF", "FCF Yield %", "P/Book"])
        
        self.spin_kpi_value = NoScrollDoubleSpinBox()
        # self.spin_kpi_value = QDoubleSpinBox() # STANDARD WIDGET ISOLATION
        self.spin_kpi_value.setRange(-9999.0, 9999.0)
        self.spin_kpi_value.setDecimals(2)
        self.spin_kpi_value.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons) # No Buttons
        
        # Style inputs
        style_input = f"border: 1px solid {COLORS['border']}; padding: 5px; border-radius: 4px; background-color: {COLORS['surface_light']};"
        for w in [self.txt_name, self.txt_ticker, self.txt_yahoo_ticker, self.txt_aliases, self.combo_exchange, 
                  self.combo_currency, self.txt_idea, self.txt_ir_web, 
                  self.txt_pr_web, self.spin_price, self.combo_kpi_type, self.date_edit, self.spin_kpi_value]:
            w.setStyleSheet(style_input)

        row = 0
        form_layout.addWidget(QLabel("Company Name:"), row, 0)
        form_layout.addWidget(self.txt_name, row, 1)
        row += 1
        
        form_layout.addWidget(QLabel("Ticker Symbol:"), row, 0)
        form_layout.addWidget(self.txt_ticker, row, 1)
        row += 1

        form_layout.addWidget(QLabel("Yahoo Ticker (Optional):"), row, 0)
        self.txt_yahoo_ticker.setPlaceholderText("e.g. MSFT, NESN.SW (Overrides Exchange)")
        form_layout.addWidget(self.txt_yahoo_ticker, row, 1)
        row += 1

        # Aliases Removed as per user request
        # form_layout.addWidget(QLabel("Aliases:"), row, 0)
        # self.txt_aliases.setPlaceholderText("e.g. VBNK.TO, VBNK.NE (Comma separated)")
        # form_layout.addWidget(self.txt_aliases, row, 1)
        # row += 1
        
        # Category Dropdown (New)
        form_layout.addWidget(QLabel("Category:"), row, 0)
        self.combo_category = NoScrollComboBox()
        self.combo_category.addItems(["Watchlist", "Portfolio", "Special"])
        style_combo = f"border: 1px solid {COLORS['border']}; padding: 5px; border-radius: 4px; background-color: {COLORS['surface_light']}; color: white;"
        self.combo_category.setStyleSheet(style_combo)
        form_layout.addWidget(self.combo_category, row, 1)
        row += 1
        
        form_layout.addWidget(QLabel("Exchange:"), row, 0)
        form_layout.addWidget(self.combo_exchange, row, 1)
        row += 1
        
        form_layout.addWidget(QLabel("Currency:"), row, 0)
        form_layout.addWidget(self.combo_currency, row, 1)
        row += 1
        
        form_layout.addWidget(QLabel("Idea Source:"), row, 0)
        self.txt_idea.setPlaceholderText("e.g. ValueInvestorsClub, Screen, Friend")
        form_layout.addWidget(self.txt_idea, row, 1)
        row += 1

        # Price First Time
        form_layout.addWidget(QLabel("Price First Time:"), row, 0)
        form_layout.addWidget(self.spin_price, row, 1)
        row += 1
        
        # KPI First Time NTM
        form_layout.addWidget(QLabel("KPI First Time NTM:"), row, 0)
        kpi_container = QWidget()
        kpi_layout = QHBoxLayout(kpi_container)
        kpi_layout.setContentsMargins(0,0,0,0)
        kpi_layout.setSpacing(5)
        kpi_layout.addWidget(self.combo_kpi_type, 1)
        kpi_layout.addWidget(self.spin_kpi_value, 1)
        form_layout.addWidget(kpi_container, row, 1)
        row += 1
        
        # Hours (Hidden initially, shown for Edit)
        self.lbl_hours = QLabel("Hours Spent:")
        self.spin_hours = NoScrollDoubleSpinBox()
        self.spin_hours.setRange(0, 9999.0)
        self.spin_hours.setDecimals(1)
        self.spin_hours.setSuffix(" h")
        self.spin_hours.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons) # No Buttons
        self.spin_hours.setStyleSheet(style_input)
        
        self.lbl_hours.hide()
        self.spin_hours.hide()
        
        form_layout.addWidget(self.lbl_hours, row, 0)
        form_layout.addWidget(self.spin_hours, row, 1)
        row += 1

        self.layout.addLayout(form_layout)
        
        # Custom Links (Moved to bottom, no title)
        # self.layout.addWidget(QLabel("Custom Links & Analysis:")) # Removed label
        self.links_container = QWidget()
        self.links_layout = QVBoxLayout(self.links_container)
        self.links_layout.setContentsMargins(0,10,0,0) # Margin top
        self.layout.addWidget(self.links_container)
        
        self.link_inputs = [] 
        
        # Add Link Button
        self.btn_add_link = QPushButton("+ Add Link")
        self.btn_add_link.setStyleSheet(f"background-color: {COLORS['surface_light']}; border: 1px dashed {COLORS['primary']}; color: {COLORS['primary']}; padding: 5px;")
        self.btn_add_link.clicked.connect(lambda: self.add_link_field())
        self.layout.addWidget(self.btn_add_link)

        # Build Button
        self.btn_create = QPushButton("Create Company Folder")
        self.btn_create.setStyleSheet(f"background-color: {COLORS['primary']}; color: black; font-weight: bold; padding: 10px; border-radius: 5px; margin-top: 10px;")
        self.btn_create.clicked.connect(self.validate_and_accept)
        
        # Wrap up scroll area
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        main_layout.addWidget(self.btn_create)
        
        # DELETE Button (Initially Hidden)
        self.btn_delete = QPushButton("DELETE COMPANY")
        self.btn_delete.setStyleSheet(f"background-color: {COLORS['danger']}; color: white; font-weight: bold; padding: 10px; border-radius: 5px; margin-top: 5px;")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.clicked.connect(self.delete_company)
        self.btn_delete.hide()
        main_layout.addWidget(self.btn_delete)
        
        self.is_edit_mode = False
        self.original_ticker = None

    def add_link_field(self, title="", url="", color="#3498DB"):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0,0,0,0)
        row_layout.setSpacing(5)
        
        # Ordering Buttons (Text instead of Icons for visibility)
        btn_up = QPushButton("Up") 
        btn_up.setFixedSize(40, 24)
        btn_up.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_up.setStyleSheet(f"border: 1px solid {COLORS['border']}; background-color: {COLORS['surface']}; color: {COLORS['text_main']}; font-size: 11px; border-radius: 4px; font-weight: bold;")
        btn_up.clicked.connect(lambda: self.move_link(row_widget, -1))
        
        btn_down = QPushButton("Down")
        btn_down.setFixedSize(45, 24)
        btn_down.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_down.setStyleSheet(f"border: 1px solid {COLORS['border']}; background-color: {COLORS['surface']}; color: {COLORS['text_main']}; font-size: 11px; border-radius: 4px; font-weight: bold;")
        btn_down.clicked.connect(lambda: self.move_link(row_widget, 1))
        
        row_layout.addWidget(btn_up)
        row_layout.addWidget(btn_down)
        
        txt_title = QLineEdit(title)
        txt_title.setPlaceholderText("Title")
        txt_title.setFixedWidth(120)
        txt_title.setStyleSheet(f"border: 1px solid {COLORS['border']}; padding: 5px; border-radius: 4px; background-color: {COLORS['surface_light']};")
        
        txt_url = QLineEdit(url)
        txt_url.setPlaceholderText("URL")
        txt_url.setStyleSheet(f"border: 1px solid {COLORS['border']}; padding: 5px; border-radius: 4px; background-color: {COLORS['surface_light']};")
        
        # Color Picker Button
        btn_color = QPushButton()
        btn_color.setFixedSize(24, 24)
        btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_color.setStyleSheet(f"background-color: {color}; border: 2px solid {COLORS['border']}; border-radius: 12px;")
        btn_color.clicked.connect(lambda: self.pick_color(btn_color))
        # Store color in property
        btn_color.setProperty("selected_color", color)

        # Delete Button (Red X for visibility)
        btn_del = QPushButton("X")
        btn_del.setFixedSize(24, 24)
        # Red background, white text, bold
        btn_del.setStyleSheet(f"background-color: {COLORS['danger']}; color: white; font-weight: bold; border: none; font-size: 14px; border-radius: 12px;")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.clicked.connect(lambda: self.remove_link_field(row_widget))
        
        row_layout.addWidget(txt_title)
        row_layout.addWidget(txt_url)
        row_layout.addWidget(btn_color)
        row_layout.addWidget(btn_del)
        
        self.links_layout.addWidget(row_widget)
        # Store tuple with all controls to manage state
        self.link_inputs.append({"title": txt_title, "url": txt_url, "widget": row_widget, "color_btn": btn_color})

    # format_date_input REMOVED as using QDateEdit now
    def move_link(self, row_widget, direction):
        # Find index
        idx = -1
        for i, item in enumerate(self.link_inputs):
            if item["widget"] == row_widget:
                idx = i
                break
        
        if idx == -1: return
        
        new_idx = idx + direction
        if 0 <= new_idx < len(self.link_inputs):
            # Swap in list
            self.link_inputs[idx], self.link_inputs[new_idx] = self.link_inputs[new_idx], self.link_inputs[idx]
            
            # Refresh Layout
            # Remove all and re-add in order? Or assume list order is truth and rebuild
            # Easier to rebuild layout from list of widgets
            # Detach all
            for i in reversed(range(self.links_layout.count())):
                 self.links_layout.takeAt(i) # Does not delete widget, just removes from layout
            
            # Re-add in new order
            for item in self.link_inputs:
                self.links_layout.addWidget(item["widget"])

    def pick_color(self, btn):
        from PyQt6.QtWidgets import QColorDialog
        curr_color = QColor(btn.property("selected_color"))
        color = QColorDialog.getColor(curr_color, self, "Select Link Color")
        if color.isValid():
            hex_color = color.name()
            btn.setStyleSheet(f"background-color: {hex_color}; border: 2px solid {COLORS['border']}; border-radius: 12px;")
            btn.setProperty("selected_color", hex_color)

    def remove_link_field(self, row_widget):
        for i, item in enumerate(self.link_inputs):
            if item["widget"] == row_widget:
                self.link_inputs.pop(i)
                break
        row_widget.deleteLater()
        
    def validate_and_accept(self):
        blackbox.start("CREATE_COMPANY_ATTEMPT")
        
        # Global Safety Wrap
        try:
            # Dependencies (Hoisted to avoid UnboundLocalError)
            import os
            import json
            import shutil
            import sqlite3
            import datetime
            import traceback

            if self.is_edit_mode:
                 self.accept()
                 blackbox.end("EDIT_MODE_ACCEPT")
                 return

            # Safety guard
            self.btn_create.setEnabled(False)
            blackbox.log("Validation: Checking name")
            
            # 1. Validate Name
            if not self.txt_name.text().strip():
                QMessageBox.warning(self, "Error", "Company Name is required.")
                self.btn_create.setEnabled(True)
                blackbox.log("Validation Failed: Empty Name")
                return
            
            # 2. Duplicate Check
            data = self.get_data()
            ticker = data['ticker']
            
            # SANITIZATION: Extract Ticker from "Name (Ticker)" if present
            if "(" in ticker and ")" in ticker:
                try:
                    ticker = ticker.split("(")[-1].strip(")")
                except:
                    pass
            
            blackbox.log(f"Validation: Ticker={ticker}")
            # Check Ticker Conflict
            if self.companies_manager:
                companies = self.companies_manager.get_companies()
                existing_tickers = [c['ticker'] for c in companies]
                
                # Use self.txt_ticker.text() to get current ticker in dialog
                current_ticker = self.txt_ticker.text().strip().upper()
                
                # If we are in edit mode (implied by read-only ticker), we skip check unless name changed?
                # Actually, simplify:
                if not self.txt_ticker.isReadOnly():
                     if current_ticker in existing_tickers:
                         QMessageBox.warning(self, "Duplicate", f"Company {current_ticker} already exists.")
                         self.btn_create.setEnabled(True)
                         blackbox.log("Validation Failed: Duplicate Ticker")
                         return

            # Check Name Conflict (Fuzzy)
            name_conflict = None
            input_name = (data['name'] or "").lower()
            if input_name and self.companies_manager:
                for c in companies:
                    c_name = (c.get('name') or "").lower()
                    if c_name == input_name and c.get('ticker') != ticker:
                        name_conflict = c
                        break
            
            if "Create" in self.windowTitle() and name_conflict:
                 reply = QMessageBox.question(self, "Possible Duplicate", 
                                              f"A company with name '{data['name']}' already exists ({name_conflict['ticker']}).\nCreate anyway?",
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                 if reply == QMessageBox.StandardButton.No:
                     self.btn_create.setEnabled(True)
                     blackbox.log("Validation Cancelled: Duplicate Name")
                     return
    
            # 3. Yahoo Validation
            blackbox.log("Validation: Yahoo Check skipped (disabled)")
            # Validate Ticker Presence on Yahoo (can trigger network)
            # TEMPORARILY DISABLED: Suspected Cause of Crash (Network/SSL Segfault)
            # try:
            #     yahoo_ticker = price_fetcher.get_yahoo_ticker(ticker, exchange)
            #     isValid = price_fetcher.validate_ticker(yahoo_ticker)
            #     
            #     if not isValid:
            #         ret = QMessageBox.warning(self, "Validation Warning", 
            #                                   f"Ticker '{yahoo_ticker}' was NOT found on Yahoo Finance.\n\n"
            #                                   f"Price automation will not work.\n"
            #                                   f"Do you want to proceed regardless?",
            #                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            #         if ret == QMessageBox.StandardButton.No:
            #             self.btn_create.setEnabled(True)
            #             return
            # except Exception as e:
            #     print(f"Yahoo validation check skipped due to error: {e}")
            #     # Don't block creation if validation crashes (internet issue?)
    
            # 4. Confirmation
            msg = f"Adding: {data['name']} ({ticker})\nExchange: {data['exchange']}\nCategory: {data.get('category','Watchlist')}\n\nProceed?"
            if QMessageBox.question(self, "Confirm", msg) != QMessageBox.StandardButton.Yes:
                self.btn_create.setEnabled(True)
                blackbox.log("User Cancelled Confirmation")
                return
    
            # 5. Create Folders & Files
            blackbox.log("Creating System Artifacts...")
            
            # Create Directory
            stock_path = os.path.join(LIBRARY_ROOT, "STOCK", ticker)
            if not os.path.exists(stock_path):
                os.makedirs(stock_path, exist_ok=True)
            
            # Save company_info.json
            info_path = os.path.join(stock_path, "company_info.json")
            with open(info_path, 'w') as f:
                json.dump(data, f, indent=4)
                
            # Create Subfolders
            for sub in ["1 REPORTS", "2 TRANSCRIPTS", "3 EXCEL", "4 VARIOS"]:
                os.makedirs(os.path.join(stock_path, f"{sub} {ticker}"), exist_ok=True)
                
            # Copy Dropped File if any
            if hasattr(self, 'drop_area') and self.drop_area.file_path:
                 src = self.drop_area.file_path
                 fname = os.path.basename(src)
                 dest = os.path.join(stock_path, f"4 VARIOS {ticker}", fname)
                 try:
                     shutil.copy2(src, dest)
                 except: pass

            # Insert into DB (Logic Restored)
            db_path = getattr(self.companies_manager, 'db_path', None)
            if not db_path:
                 db_path = os.path.join(LIBRARY_ROOT, "library.db")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Upsert
            cursor.execute("""
                INSERT OR REPLACE INTO companies (
                    ticker, name, category, currency, primary_exchange, 
                    yahoo_ticker, aliases, notes, status, last_update
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker, data['name'], data['category'], data['currency'], 
                data['exchange'], data['yahoo_ticker'], data['aliases'], 
                f"Idea: {data.get('idea_source','')}", 'To Research',
                datetime.datetime.now().strftime("%Y-%m-%d")
            ))
            conn.commit()
            conn.close()
            
            # Update Manager Cache
            # self.companies_manager.sync_with_library() 
            
            blackbox.log("Company Created. Showing Success Message.")
            QMessageBox.information(self, "Success", f"Company {ticker} created successfully!")
            
            blackbox.log("Calling self.accept() from creation.")
            self.accept()
        
        except Exception as e:
            # GLOBAL CATCH
            blackbox.error("CRASH CAUGHT IN CREATION", e)
            import traceback
            import traceback
            err_msg = traceback.format_exc()
            print(f"CRASH CAUGHT: {e}")
            QMessageBox.critical(self, "Application Error", f"An unexpected error occurred:\n{e}\n\n{err_msg}")
            
            # Re-enable buttons so user isn't stuck
            self.btn_create.setEnabled(True)
        
    def get_data(self):
        links = []
        for item in self.link_inputs:
            t = item["title"].text().strip()
            u = item["url"].text().strip()
            c = item["color_btn"].property("selected_color")
            if t and u:
                links.append({"title": t, "url": u, "color": c})
        
        return {
            'name': self.txt_name.text().strip(),
            'category': self.combo_category.currentText(),
            'ticker': self.txt_ticker.text().strip().upper(),
            'exchange': self.combo_exchange.currentText(),
            'currency': self.combo_currency.currentText(),
            'yahoo_ticker': self.txt_yahoo_ticker.text().strip(),
            'idea_source': self.txt_idea.text().strip(),
            'aliases': self.txt_aliases.text().strip(),
            'custom_links': links,
            "price_first_time": self.spin_price.value(),
            "date_first_time": self.date_edit.text_for_db(),
            "kpi_first_time_type": self.combo_kpi_type.currentText(),
            "kpi_first_time_value": self.spin_kpi_value.value(),
            "total_hours": self.spin_hours.value() # Save hours if edited
        }

    def enable_delete_mode(self, ticker):
        self.is_edit_mode = True
        self.original_ticker = ticker
        self.setWindowTitle(f"Edit Company: {ticker}")
        self.btn_delete.show()
        self.btn_create.setText("Save Changes")
        
    def delete_company(self):
        blackbox.start(f"REQ_DELETE: {self.original_ticker}")
        
        confirm = QMessageBox.question(self, "Risk of Data Loss", 
             f"Are you sure you want to PERMANENTLY DELETE '{self.original_ticker}'?\n\nThis will remove:\n- The entire folder and all files\n- Database entry\n- History and logs\n\nThis action cannot be undone.",
             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
             
        if confirm == QMessageBox.StandardButton.Yes:
            blackbox.log("User confirmed delete request.")
            
            # DIRECT DELETION (Do not close dialog)
            try:
                # 1. Delete via Manager
                success = self.companies_manager.delete_company(self.original_ticker)
                
                if success:
                    blackbox.log("Manager delete success (Direct)")
                    QMessageBox.information(self, "Deleted", f"Company {self.original_ticker} deleted successfully.")
                    
                    # Notify Parent via Signal
                    self.company_deleted.emit(self.original_ticker)

                    # CLOSE DIALOG (Safe now that it is detached?)
                    # User requested popup to close with DELAY (1s) to prevent crash
                    blackbox.log("Scheduling close in 1000ms...")
                    # self.accept() 
                    from PyQt6.QtCore import QTimer
                    
                    # --- [GOLD PLATED LOGIC] DO NOT MODIFY WITHOUT REQUEST ---
                    # CRITICAL: Use reject() so open_edit_dialog receives False and skips saving!
                    # Changing this back to accept() or removing delay WILL CAUSE CRASH.
                    # This ensures the dialog closes WITHOUT triggering the "Save" block in parent.
                    QTimer.singleShot(500, lambda: self.reject())
                    # ---------------------------------------------------------
                         
                         
                else:
                    QMessageBox.critical(self, "Error", "Could not delete company (Manager failed).")
                    
            except Exception as e:
                blackbox.error("Crash during direct delete", e)
                QMessageBox.critical(self, "Error", f"Crash during delete: {e}")


    # format_date_input REMOVED as using SmartDateEdit now
    def get_date(self):
        """Helper to get python date object from the text input"""
        txt = self.date_edit.text_for_db()
        if txt:
             return datetime.datetime.strptime(txt, "%Y-%m-%d").date()
        return datetime.datetime.now().date()

class FileDropArea(QLabel):
    def __init__(self, parent=None, placeholder="Drop File"):
        super().__init__(parent)
        self.placeholder_text = f"<html><body style='text-align:center;'><h2 style='color:#FF9800; font-size:22px; font-weight:bold; margin-bottom:5px;'>Drop File</h2><p style='color:#A0A0A0; font-size:12px; margin-top:0px;'>Drop Single File Here to Organize</p></body></html>"
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText(self.placeholder_text)
        self.update_style()
        self.setAcceptDrops(True)
        self.current_files = [] 
        self.parent_widget = parent
        
        # Remove Button (Hidden by default)
        self.btn_remove = QPushButton("X", self)
        self.btn_remove.setFixedSize(24, 24)
        self.btn_remove.setStyleSheet(f"background-color: {COLORS['danger']}; color: white; border-radius: 12px; font-weight: bold; border: none;")
        self.btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_remove.clicked.connect(self.clear_files)
        self.btn_remove.hide()

    def resizeEvent(self, event):
        self.btn_remove.move(self.width() - 30, 5)
        super().resizeEvent(event)

    def enterEvent(self, event):
        if self.current_files:
            self.btn_remove.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.btn_remove.hide()
        super().leaveEvent(event)

    def clear_files(self):
        self.current_files = []
        self.setText(self.placeholder_text)
        self.update_style()
        self.btn_remove.hide() 
        # Notify parent to reset preview
        if self.parent_widget and hasattr(self.parent_widget, 'on_file_dropped'):
             self.parent_widget.on_file_dropped()

    def update_style(self, active=False):
        if active:
             self.setStyleSheet(f"""
                QLabel {{
                    border: 2px dashed {COLORS['primary']};
                    border-radius: 10px;
                    background-color: {COLORS['surface_light']}; 
                    color: {COLORS['primary']};
                    font-size: 14px;
                    font-weight: bold;
                }}
            """)
        else:
             self.setStyleSheet(f"""
                QLabel {{
                    border: 2px dashed {COLORS['text_dim']};
                    border-radius: 10px;
                    background-color: {COLORS['surface']}; 
                }}
            """)
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Open File Dialog
            f_path, _ = QFileDialog.getOpenFileName(self, "Select File to Organize", "", "All Files (*.*)")
            if f_path:
                self.current_files = [f_path]
                self.setText("File Selected:\n" + os.path.basename(f_path))
                self.update_style(True)
                self.btn_remove.show()
                if self.parent_widget and hasattr(self.parent_widget, 'on_file_dropped'):
                    self.parent_widget.on_file_dropped()
        super().mousePressEvent(event)

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.current_files = files
            text = "File Selected:\n" + os.path.basename(files[0])
            if len(files) > 1: text += f"\nAnd {len(files)-1} more..."
            self.setText(text)
            self.update_style(True)
            self.btn_remove.show() # Show immediately on drop
            
            if self.parent_widget and hasattr(self.parent_widget, 'on_file_dropped'):
                self.parent_widget.on_file_dropped()

class CompanyStatusWidget(QFrame):
    def __init__(self):
        super().__init__()
        # Remove red border logic user hated, keep subtle border
        self.setStyleSheet(f"background-color: {COLORS['surface_light']}; border-radius: 8px; border: 1px solid {COLORS['border']};")
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        self.lbl_title = QLabel("Milestone")
        # Make title bigger, ensure visible color, transparent bg
        self.lbl_title.setStyleSheet(f"font-weight: bold; color: {COLORS['primary']}; font-size: 14px; border: none; background: transparent; margin-top: 10px;")
        self.layout.addWidget(self.lbl_title)
        
        # Grid for status
        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(15)
        self.grid.setHorizontalSpacing(20)
        self.layout.addLayout(self.grid)
        
    def clear_layout(self, layout):
        if not layout: return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
                item.layout().deleteLater() # Delete the layout object itself

    def update_status(self, ticker):
        # Clear grid properly (recursive for sub-layouts)
        self.clear_layout(self.grid)
            
        if not ticker:
            self.lbl_title.setText("Milestone - Select a company")
            return
            
        self.lbl_title.setText(f"Milestone - {ticker}")
        
        base_path = os.path.join(LIBRARY_ROOT, "STOCK", ticker)
        
        current_year = datetime.date.today().year
        # Find Max Year logic
        max_year = current_year
        reports_path = os.path.join(base_path, f"1 REPORTS {ticker}")
        
        if os.path.exists(reports_path):
             # Scan for years
             for d in os.listdir(reports_path):
                 if d.isdigit() and len(d) == 4:
                     y = int(d)
                     if y > max_year:
                         max_year = y

        years = [max_year - i for i in range(5)] # 5 years starting from max (e.g. 2025, 2024, 2023...)
        
        # ROW 0: Annual Reports (Moved to top since Valuation is gone)
        lbl_ar = QLabel("Annual Reports")
        lbl_ar.setStyleSheet("font-weight: bold; color: #888; border: none; background: transparent;")
        self.grid.addWidget(lbl_ar, 0, 0)
        
        reports_sublayout = QHBoxLayout()
        reports_sublayout.setSpacing(5)
        for y in years:
            found = False
            year_path = os.path.join(base_path, f"1 REPORTS {ticker}", str(y))
            if os.path.exists(year_path):
                if len(os.listdir(year_path)) > 0:
                     found = True
            
            lbl_y = QLabel(str(y))
            lbl_y.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Simpler pill style
            if found:
                lbl_y.setStyleSheet(f"background-color: {COLORS['success']}; color: white; border-radius: 4px; padding: 4px; font-weight: bold;")
            else:
                lbl_y.setStyleSheet(f"background-color: transparent; color: {COLORS['text_dim']}; border: 1px dashed {COLORS['border']}; border-radius: 4px; padding: 4px;")
            
            lbl_y.setFixedSize(50, 25)
            reports_sublayout.addWidget(lbl_y)
        
        reports_sublayout.addStretch()
        self.grid.addLayout(reports_sublayout, 0, 1)

        # ROW 1: Transcripts
        lbl_tr = QLabel("Transcripts")
        lbl_tr.setStyleSheet("font-weight: bold; color: #888; border: none; background: transparent;")
        self.grid.addWidget(lbl_tr, 1, 0)
        
        trans_sublayout = QHBoxLayout()
        trans_sublayout.setSpacing(5)
        for y in years:
            found = False
            year_path = os.path.join(base_path, f"2 TRANSCRIPTS {ticker}", str(y))
            if os.path.exists(year_path):
                if len(os.listdir(year_path)) > 0:
                    found = True
            
            lbl_y = QLabel(str(y))
            lbl_y.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if found:
                lbl_y.setStyleSheet(f"background-color: {COLORS['success']}; color: white; border-radius: 4px; padding: 4px; font-weight: bold;")
            else:
                lbl_y.setStyleSheet(f"background-color: transparent; color: {COLORS['text_dim']}; border: 1px dashed {COLORS['border']}; border-radius: 4px; padding: 4px;")
            
            lbl_y.setFixedSize(50, 25)
            trans_sublayout.addWidget(lbl_y)
            
        trans_sublayout.addStretch()
        self.grid.addLayout(trans_sublayout, 1, 1)

class InputStockWidget(QWidget):
    company_deleted = pyqtSignal(str) # Signal to notify MainWindow
    company_updated = pyqtSignal(str) # Signal for updates (e.g. currency change)
    
    def __init__(self, portfolio_manager=None):
        super().__init__()
        self.portfolio_manager = portfolio_manager
        self.companies_manager = CompaniesManager(LIBRARY_ROOT)
        
        # Init Fortress DB Connection
        self.engine = init_db()
        self.Session = get_session_factory(self.engine)

        # ── Debounce timer for company switching (fixes F4 rapid-switch bug) ──
        # When the user changes company quickly, we wait 200ms before loading.
        # If another change arrives within that window, the timer resets.
        self._company_debounce = QTimer()
        self._company_debounce.setSingleShot(True)
        self._company_debounce.setInterval(200)  # 200ms window
        self._company_debounce.timeout.connect(self._load_company_debounced)
        self._pending_company_text = ""            # Stores the last requested ticker
        
        self.setup_ui()
        from ui.app_state import AppState
        AppState.get().library_synced.connect(self.on_library_synced)


    def setup_ui(self):
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- TOP SECTION (Split 50/50) ---
        top_split = QSplitter(Qt.Orientation.Horizontal)
        top_split.setHandleWidth(1)
        top_split.setStyleSheet(f"QSplitter::handle {{ background-color: {COLORS['border']}; }}")
        
        # -- LEFT: INPUT & ACTIONS --
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(20,0,0,0)
        left_layout.setSpacing(20) # Match Right Layout Spacing
        # (Removed AlignTop to allow Stretch to work)

        # 1. TOP GROUP
        # TITLE: Feeder (Moved to Top)
        lbl_feeder = QLabel("Feeder")
        # Removed margin-top to align with Status (which has 0)
        lbl_feeder.setStyleSheet(f"font-weight: bold; color: {COLORS['primary']}; margin-top: 0px; font-size: 18px;") 
        left_layout.addWidget(lbl_feeder)

        # 1. New Company Button (Moved Below Title)
        self.btn_new_company = QPushButton("+ Add Company")
        self.btn_new_company.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_company.setStyleSheet(f"""
            QPushButton {{
                background-color: #FF6D00; /* Orange */
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px;
                border: none;
                margin-top: 34px; /* Alignment Fix: Adjusted to 34px - Sweet spot between 24px (high) and 42px (low) */
            }}
            QPushButton:hover {{ background-color: #EF6C00; }}
        """)
        self.btn_new_company.clicked.connect(self.open_new_company_dialog)
        left_layout.addWidget(self.btn_new_company)
        
        # --- MIDDLE STRETCH ---
        # This creates the variable gap user requested so bottom aligns with bottom
        left_layout.addStretch(1)
        
        # --- BOTTOM GROUP ---
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0,0,0,0)
        bottom_layout.setSpacing(15)
        
        # 4. SNE Form (Compact)
        form_grid = QGridLayout()
        form_grid.setSpacing(10)
        
        # Date (Manual Entry requested)
        form_grid.addWidget(QLabel("Date:"), 0, 0)
        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("YYYY-MM-DD")
        self.date_edit.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; padding: 5px; border-radius: 4px;")
        self.date_edit.textChanged.connect(self.format_date_input)
        self.date_edit.setText("") # Default Empty
        form_grid.addWidget(self.date_edit, 0, 1)
        
        # Period & Type
        form_grid.addWidget(QLabel("Period:"), 1, 0)
        self.combo_period = QComboBox()
        for key, desc in SNE_PERIODS.items():
            self.combo_period.addItem(key, key) 
        self.combo_period.setCurrentText("NA")
        form_grid.addWidget(self.combo_period, 1, 1)
        
        form_grid.addWidget(QLabel("Type:"), 1, 2)
        self.combo_type = QComboBox()
        for key, desc in SNE_TYPES.items():
            self.combo_type.addItem(key, key)
        self.combo_type.setCurrentText("REP") 
        form_grid.addWidget(self.combo_type, 1, 3)
        
        # Extra Label
        form_grid.addWidget(QLabel("Extra:"), 2, 0)
        self.txt_extra = QLineEdit()
        self.txt_extra.setPlaceholderText("Optional tag")
        self.txt_extra.textChanged.connect(self.update_preview)
        form_grid.addWidget(self.txt_extra, 2, 1, 1, 3) # Span
        
        bottom_layout.addLayout(form_grid)
        
        # 3. Drop Zone
        self.drop_area = FileDropArea(self, "Drop File")
        self.drop_area.setFixedHeight(100)
        bottom_layout.addWidget(self.drop_area)
        
        # 5. Process Button
        self.btn_process = QPushButton("Process & Add to Library")
        self.btn_process.setStyleSheet(f"background-color: {COLORS['success']}; color: white; font-weight: bold; padding: 10px;")
        self.btn_process.clicked.connect(self.process_file)
        bottom_layout.addWidget(self.btn_process)
        
        left_layout.addWidget(bottom_widget)
        
        # -- RIGHT: COMPANY HEADER INFO --
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0,0,20,0)
        right_layout.setSpacing(0)

        # TITLE: Status
        lbl_status = QLabel("Status")
        lbl_status.setStyleSheet(f"font-weight: bold; color: {COLORS['primary']}; margin-top: 0px; font-size: 18px;")
        right_layout.addWidget(lbl_status)
        right_layout.addSpacing(20) # Add space between Title and Logo
        
        from ui.widgets.pdf_manager import CompanyHeaderWidget, PdfManagerWidget 
        from ui.widgets.status_panel import StatusPanel 
        
        self.header_widget = CompanyHeaderWidget()
        # The header widget has a layout, use it.
        # It displays Logo, Progress, Hours, AND NOW Combo/New Button
        
        # Connect Header Signals
        # self.header_widget.btn_new_company.clicked.connect... (Removed, local button used instead)
        self.header_widget.combo_companies.currentTextChanged.connect(self.on_company_changed)
        
        # FIX: When on_company_changed finishes loading, we might want to signal MainWindow to refresh 
        # CompaniesView if specific data changed? 
        # For now, let's keep it simple. The user complaint was about GBP.X not updating.
        # That's in CompaniesView. If user edits in F4, F2 is not auto-refreshed?
        # We need a 'saved' signal.
        # InputStockWidget.process_edit_save calls self.safe_refresh(ticker)
        # We should check safe_refresh.
        
        right_layout.addWidget(self.header_widget)
        
        # Milestones
        right_layout.addSpacing(20) # Push down
        self.status_widget = StatusPanel()
        self.status_widget.request_open_document.connect(self.open_smart_resume_document)
        right_layout.addWidget(self.status_widget) 
        
        right_layout.addStretch() # Push header up
        
        top_split.addWidget(right_container)
        top_split.addWidget(left_container)
        
        main_layout.addWidget(top_split)
        
        # --- BOTTOM SECTION ---
        
        # 1. Milestones (Moved to Left Panel)
        # self.status_widget = CompanyStatusWidget()
        # main_layout.addWidget(self.status_widget)
        
        # 2. Full Library Manager (Embedded)


        # --- Files in Library ---
        label_lib = QLabel("Files in Library")
        label_lib.setStyleSheet(f"font-weight: bold; color: {COLORS['primary']}; margin-top: 10px; font-size: 18px;")
        main_layout.addWidget(label_lib)
        
        self.library_manager_widget = PdfManagerWidget(os.path.join(LIBRARY_ROOT, "STOCK"), embedded=True)
        main_layout.addWidget(self.library_manager_widget, 1) # Stretch to fill rest
        
        # Connect Signals
        # self.date_edit.textChanged.connect(self.update_preview) # Handled by format_date_input
        self.combo_period.currentIndexChanged.connect(self.update_preview)
        self.combo_type.currentIndexChanged.connect(self.update_preview)
        
        # Connect library file_data_changed to refresh the progress bar in the header
        self.library_manager_widget.file_data_changed.connect(self._refresh_progress_bar)

        # Init
        self.refresh_company_list()
    
    # ... (Keep existing methods: open_new_company_dialog, create_company_folder, etc.) ...
    def on_company_deleted_from_dialog(self, ticker):
        """Handle signal from detached dialog."""
        blackbox.log(f"Signal received: Company deleted {ticker}")
        try:
            self.refresh_company_list()
            # Also try to update Header if possible
            if hasattr(self, 'header_widget') and hasattr(self.header_widget, 'refresh_companies'):
                self.header_widget.refresh_companies()
            # Or at least notify manager
            if hasattr(self.companies_manager, 'notify_update'):
                 self.companies_manager.notify_update()
        except Exception as e:
            blackbox.error("Error handling delete signal", e)
            
        # Notify Global
        self.company_deleted.emit(ticker)

    def open_new_company_dialog(self):
        try:
            blackbox.log("Opening NewCompanyDialog (Detached Parent)")
            # CRITICAL FIX: Pass None as parent to prevent "Double Destruction" or
            # child-cleanup crashes when the dialog closes.
            dial = NewCompanyDialog(None) 
            dial.setWindowModality(Qt.WindowModality.ApplicationModal)
            
            # Connect Deletion Signal to Refresh
            dial.company_deleted.connect(lambda t: self.on_company_deleted_from_dialog(t))
            
            # Manually pass dependencies that were previously inherited
            if hasattr(self, 'companies_manager'):
                dial.companies_manager = self.companies_manager
                
            result = dial.exec()
            blackbox.log(f"Dialog closed. Result: {result}")
            
            if result == QDialog.DialogCode.Accepted:
                try:
                    # Check if it was a deletion request
                    if getattr(dial, 'was_deleted', False):
                        ticker_to_delete = getattr(dial, 'ticker_to_delete', None)
                        blackbox.log(f"Processing Deletion Request for: {ticker_to_delete}")
                        
                        if ticker_to_delete:
                            manager = CompaniesManager(LIBRARY_ROOT)
                            success = manager.delete_company(ticker_to_delete)
                            
                            if success:
                                blackbox.log("Manager delete success (Parent)")
                                QMessageBox.information(self, "Deleted", f"Company {ticker_to_delete} deleted successfully.")
                                # Refresh List in Header
                                if hasattr(self.companies_manager, 'notify_update'):
                                     try:
                                         self.companies_manager.notify_update()
                                     except: pass
                                
                                try:
                                    blackbox.log("Refreshing list after delete")
                                    self.refresh_company_list()
                                except Exception as e:
                                     blackbox.error("Refresh error", e)
                            else:
                                QMessageBox.critical(self, "Error", "Could not delete company (Manager failed).")
                        
                        return # Stop processing (don't update header for deleted company)

                    # Update Header Selection if it was a new creation (not deletion)
                    # For creation, the dialog already did the work (maybe we should defer that too? logic for another day)
                    # For now, creation seems stable.
                    
                    data = dial.get_data()
                    if hasattr(self, 'header_widget') and data.get('ticker'):
                         try:
                             self.header_widget.combo_companies.setCurrentText(data['ticker'])
                         except Exception as e:
                             print(f"Error updating header combo: {e}")

                    # Refresh List (Creation)
                    try:
                        self.refresh_company_list()
                    except: pass
                             
                except Exception as inner_e:
                     print(f"CRITICAL ERROR POST-DIALOG: {inner_e}")
                     import traceback
                     traceback.print_exc()
                     QMessageBox.critical(self, "Post-Creation Error", f"Company created, but UI update failed: {inner_e}")
        except Exception as e:
            print(f"CRITICAL ERROR OPENING DIALOG: {e}")
            QMessageBox.critical(self, "Dialog Error", f"Could not open dialog: {e}")

    def open_new_company_dialog_with_ticker(self, ticker, name=""):
        try:
            blackbox.log(f"Opening NewCompanyDialog with ticker {ticker} (Detached Parent)")
            dial = NewCompanyDialog(None) 
            dial.setWindowModality(Qt.WindowModality.ApplicationModal)
            dial.txt_ticker.setText(ticker)
            if name:
                dial.txt_name.setText(name)
            
            # Connect Deletion Signal to Refresh
            dial.company_deleted.connect(lambda t: self.on_company_deleted_from_dialog(t))
            
            if hasattr(self, 'companies_manager'):
                dial.companies_manager = self.companies_manager
                
            result = dial.exec()
            blackbox.log(f"Dialog closed. Result: {result}")
            
            if result == QDialog.DialogCode.Accepted:
                try:
                    data = dial.get_data()
                    if hasattr(self, 'header_widget') and data.get('ticker'):
                         try:
                             self.header_widget.combo_companies.setCurrentText(data['ticker'])
                         except Exception as e:
                             print(f"Error updating header combo: {e}")
                    
                    # Refresh List (Creation)
                    try:
                        self.refresh_company_list()
                    except: pass
                    
                    # Global Broadcast
                    from ui.app_state import AppState
                    AppState.get().notify_company_created(ticker)
                    
                    # Load the company immediately
                    self.load_company_from_link(ticker)
                    
                except Exception as inner_e:
                     print(f"Error post-dialog: {inner_e}")
        except Exception as e:
            print(f"CRITICAL ERROR OPENING DIALOG: {e}")

    def on_library_synced(self):
        # Reload current company if any
        current_ticker = ""
        if hasattr(self, 'header_widget') and not sip.isdeleted(self.header_widget):
            try:
                current_ticker = self.header_widget.combo_companies.currentText()
            except RuntimeError:
                pass
        if current_ticker and current_ticker != " Company ":
            print(f"[InputStock] Library synced! Reloading library for {current_ticker}")
            self._do_load_company(current_ticker)

            
    def create_company_folder(self, data):
        ticker = data['ticker']
        # Create base folders and junctions matching the 4-layer taxonomy
        base_path = os.path.join(LIBRARY_ROOT, "STOCK", ticker)
        
        try:
            # Create local physical directories
            local_base = os.path.join(r"D:\00_LOCAL_ARCHIVE_NO_SYNC\Ekomonos_Library\STOCK", ticker, "02_Fuentes_Inmutables")
            for f in ["02.01_Reportes", "02.02_Transcripciones", "02.03_Articulos_y_Prensa"]:
                os.makedirs(os.path.join(local_base, f), exist_ok=True)
            
            # Create cloud directories
            os.makedirs(os.path.join(base_path, "01_Directrices_y_Cerebro"), exist_ok=True)
            os.makedirs(os.path.join(base_path, "03_Modelos_y_Datos", "_Historico"), exist_ok=True)
            os.makedirs(os.path.join(base_path, "04_Sintesis_y_Analisis"), exist_ok=True)
            
            # Create Junction for 02_Fuentes_Inmutables
            junction_path = os.path.join(base_path, "02_Fuentes_Inmutables")
            if not os.path.exists(junction_path):
                import subprocess
                subprocess.run(f'cmd /c mklink /J "{junction_path}" "{local_base}"', shell=True)
            
            # Save metadata
            info_path = os.path.join(base_path, "01_Directrices_y_Cerebro", "company_info.json")
            import json
            with open(info_path, 'w') as f:
                json.dump(data, f, indent=4)
                
            # Create default rules file
            rules_path = os.path.join(base_path, "01_Directrices_y_Cerebro", f"rules_{ticker}.json")
            if not os.path.exists(rules_path):
                with open(rules_path, 'w') as f:
                    json.dump({}, f, indent=4)
                
            QMessageBox.information(self, "Success", f"Company {ticker} created successfully!")
            self.refresh_company_list()
            if hasattr(self, 'header_widget'):
                self.header_widget.combo_companies.setCurrentText(ticker) 
            
            # Update DB Category & Exchange
            # Update DB Category & Exchange & Currency
            self.companies_manager.sync_with_library() # Ensure it's in DB
            self.companies_manager.update_company(ticker, 
                                                  category=data.get('category', 'Watchlist'),
                                                  primary_exchange=data.get('exchange', ''),
                                                  currency=data.get('currency', 'USD'),
                                                  yahoo_ticker=data.get('yahoo_ticker', ''),
                                                  aliases=data.get('aliases', ''),
                                                  metric_type=data.get('kpi_first_time_type', 'P/E'))
            
            # --- SYNC WITH FORTRESS_VAULT.DB (Calendar System) ---
            try:
                session = self.Session()
                # Check if exists
                db_comp = session.query(DBCompany).filter_by(ticker=ticker).first()
                if not db_comp:
                    db_comp = DBCompany(ticker=ticker)
                    session.add(db_comp)
                
                db_comp.name = data.get('name', ticker)
                db_comp.yahoo_ticker = data.get('yahoo_ticker') or None
                db_comp.primary_exchange = data.get('exchange')
                db_comp.aliases = data.get('aliases') or None
                # Map Category to Sector or similar if needed, or just skip
                
                session.commit()
                
                # Trigger Auto-Fetch Earnings
                em = EarningsManager(self.Session)
                success = em.update_company(ticker, session)
                if success:
                    print(f"Earnings fetched for {ticker}")
                else:
                    print(f"Could not fetch earnings for {ticker} immediately.")
                    
                session.close()
            except Exception as e:
                print(f"Error syncing with Fortress DB: {e}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create folders: {e}")

    def refresh_company_list(self):
        # Access Combo from Header
        if not hasattr(self, 'header_widget'): return
        combo = self.header_widget.combo_companies
        
        current = combo.currentText()
        if current == " Company ":
            current = ""
            
        combo.blockSignals(True)
        combo.clear()
        
        # Blank Option
        combo.addItem(" Company ")
        
        stock_path = os.path.join(LIBRARY_ROOT, "STOCK")
        folder_tickers = []
        if os.path.exists(stock_path):
            folder_tickers = sorted([d for d in os.listdir(stock_path) if os.path.isdir(os.path.join(stock_path, d))])
            
        # Get Aliases from DB
        db_companies = self.companies_manager.get_companies()
        db_map = {c['ticker']: c for c in db_companies}
        # Refresh Combo
        if not hasattr(self, 'header_widget'): return
        
        current = self.header_widget.combo_companies.currentText()
        if current == " Company ": current = ""
        
        self.header_widget.combo_companies.blockSignals(True)
        self.header_widget.combo_companies.clear()
        
        companies = self.companies_manager.get_companies() # Get List
        
        # Add Defaults
        self.header_widget.combo_companies.addItem(" Company ", "")
        
        # Sort by Name (Safe)
        companies.sort(key=lambda x: (x.get('name') or "").lower())
        
        seen_items = set() # Avoid duplicates in display
        
        for c in companies:
             t = c['ticker']
             n = c['name'] or t # Fallback to Ticker if Name is None
             if t not in seen_items:
                 # SHOW ONLY TICKER as requested
                 display_text = t 
                 self.header_widget.combo_companies.addItem(display_text, t)
                 seen_items.add(t)
                 
             # Add aliases if useful for search?
             # Maybe too cluttered.
             # Logic for aliases...
             als = c.get('aliases', '')
             if als:
                 for a in als.split(','):
                     a = a.strip()
                     if a and a not in seen_items:
                        # self.header_widget.combo_companies.addItem(f"{a} ({t})", t)
                        # seen_items.add(a)
                        pass

        self.header_widget.combo_companies.blockSignals(False)
        
        # Restore selection if still exists
        # We need to check if 'current' (Ticker) is still in the new list
        # Extract ticker from current entry? No, we rely on 'currentText' usually being "Name (Ticker)" 
        # or we stored Ticker in data.
        
        # Better: store previous ItemData
        # But we only have currentText easily here or we'd need to have grabbed data before clear.
        # Assuming current was Ticker or Name...
        
        exists = False
        for c in companies:
            if c['ticker'] == current:
                exists = True
                break
        
        if exists:
             # Find the item with this data
             idx = self.header_widget.combo_companies.findData(current)
             if idx >= 0:
                 self.header_widget.combo_companies.setCurrentIndex(idx)
        else:
             self.header_widget.combo_companies.setCurrentIndex(0)
             if current != "":
                 self.on_company_changed("")
        
        # Old code referencing curr removed
 
            
    def on_company_changed(self, text):
        """Called when the company combobox text changes.
        Uses a debounce timer so rapid switching (F4 bug) doesn't trigger
        multiple concurrent loads. Only the last selection gets processed.
        """
        if sip.isdeleted(self): return
        # Store the latest requested text and restart the debounce timer.
        # If the user changes company again within 200ms, the previous load is discarded.
        self._pending_company_text = text
        self._company_debounce.start()  # restart() = reset the 200ms window

    def _load_company_debounced(self):
        """Actually load the company — called 200ms after the last combo change."""
        if sip.isdeleted(self): return
        text = self._pending_company_text
        self._do_load_company(text)

    def _do_load_company(self, text):
        """The real company loading logic (was on_company_changed body)."""
        if sip.isdeleted(self): return

        try:
            # Resolve real ticker using Data if possible
            real_ticker = text
            if hasattr(self, 'header_widget') and not sip.isdeleted(self.header_widget):
                try:
                    data = self.header_widget.combo_companies.currentData()
                    if data:
                        real_ticker = data
                except RuntimeError:
                    pass # Widget deleted
            
            if not real_ticker or real_ticker == " Company " or text == " Company ":
                real_ticker = "" # Treat as empty
                
            self.update_preview()
            
            # Load Company Meta
            excel_path = None
            custom_links = []
            hours = 0.0
            
            if real_ticker:
                base_path = os.path.join(LIBRARY_ROOT, "STOCK", real_ticker)
                
                # 1. Info JSON
                info_path = os.path.join(base_path, "company_info.json")
                if os.path.exists(info_path):
                    try:
                        import json
                        with open(info_path, 'r') as f:
                            data = json.load(f)
                            # Migration Logic (On Read)
                            custom_links = data.get('custom_links', [])
                            if not custom_links:
                                 ir = data.get('ir_website', '')
                                 pr = data.get('pr_website', '')
                                 news = data.get('news_urls', [])
                                 if ir: custom_links.append({"title": "IR Web", "url": ir})
                                 if pr: custom_links.append({"title": "PR Web", "url": pr})
                                 for n in news: custom_links.append({"title": "News", "url": n})
                                 
                            hours = data.get('total_hours', 0.0)
                    except:
                        pass
                
                # 2. Excel Check
                excel_dir = os.path.join(base_path, f"3 EXCEL {real_ticker}")
                if os.path.exists(excel_dir):
                    files = [f for f in os.listdir(excel_dir) if (f.lower().endswith(".xlsx") or f.lower().endswith(".xls") or f.lower().endswith(".xlsm")) and not f.startswith("~$")]
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(excel_dir, x)) if os.path.exists(os.path.join(excel_dir, x)) else 0, reverse=True)
                    if files:
                        excel_path = os.path.join(excel_dir, files[0])
    
            # Update Library List FIRST so files are synced to DB before calculating progress
            if hasattr(self, 'library_manager_widget') and not sip.isdeleted(self.library_manager_widget):
                 try:
                     self.library_manager_widget.load_specific_company(real_ticker)
                 except Exception as e:
                     print(f"Error loading library for {real_ticker}: {e}")

            # Calculate real progress & hours from library_manager (DB-backed)
            pct = 0
            if real_ticker:
                try:
                    lib_mgr = self.library_manager_widget.library_manager
                    pct, _stats = lib_mgr.get_company_progress(real_ticker)
                    real_hours = lib_mgr.get_company_hours(real_ticker)
                    if real_hours > 0:
                        hours = real_hours  # Prefer Pomodoro hours over JSON
                except Exception as e:
                    print(f"[Progress] Could not calculate progress for {real_ticker}: {e}")

            # Update Header (with real progress now)
            if hasattr(self, 'header_widget') and not sip.isdeleted(self.header_widget):
                 self.header_widget.update_info(real_ticker, pct, hours)
                 self.header_widget.update_links(excel_path, custom_links)
                 
                 # Connect Edit Button (Safe)
                 try: 
                     self.header_widget.btn_edit.clicked.disconnect()
                 except: pass
                 self.header_widget.btn_edit.clicked.connect(self.open_edit_company_dialog)
            
            # Update Milestones
            if hasattr(self, 'status_widget') and not sip.isdeleted(self.status_widget):
                self.status_widget.update_status(real_ticker)

        except Exception as e:
            print(f"Error in on_company_changed: {e}")
            import traceback
            traceback.print_exc()

    def showEvent(self, event):
        super().showEvent(event)
        # Refresh the current company's library when the tab is shown.
        # IMPORTANT: Use currentData() not currentText() - the display text may
        # differ from the stored ticker (aliases, spacing, etc.). This prevents
        # the stale-company bug when switching tabs.
        if hasattr(self, 'header_widget') and hasattr(self.header_widget, 'combo_companies'):
            try:
                combo = self.header_widget.combo_companies
                current_ticker = combo.currentData() or combo.currentText()
                if current_ticker and current_ticker not in (" Company ", ""):
                    self.library_manager_widget.load_specific_company(current_ticker)
            except Exception:
                pass

    def load_company_from_link(self, ticker):
        """
        Called by MainWindow when navigating from Companies View (F2).
        Cancels any pending debounce and loads the company immediately.
        """
        if not ticker: return
        print(f"[InputStock] load_company_from_link: {ticker}")
        
        try:
            # Cancel any pending debounced load (avoids race condition)
            self._company_debounce.stop()
            self._pending_company_text = ticker

            # 1. Update Combo Box WITHOUT triggering signal (Prevent Loops)
            if hasattr(self, 'header_widget') and hasattr(self.header_widget, 'combo_companies'):
                combo = self.header_widget.combo_companies
                combo.blockSignals(True)
                combo.setCurrentText(ticker)
                combo.blockSignals(False)
                combo.setFocus()

            # 2. Load immediately (bypass debounce — this is an explicit navigation)
            self._do_load_company(ticker)
                 
        except Exception as e:
            print(f"[InputStock] CRASH inside load_company_from_link: {e}")
            import traceback
            traceback.print_exc() 


    def open_smart_resume_document(self, file_path):
        """
        Handles the signal from StatusPanel to open a specific document.
        """
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", f"Could not find file at: {file_path}")
            return
            
        # 1. Update DB 'last_accessed' (Ideally this happens inside PDF Manager, but we can double check)
        # 2. Open PDF
        # For now, let's use os.startfile as fallback
        try:
             os.startfile(file_path)
        except Exception as e:
             QMessageBox.critical(self, "Error", f"Could not open file: {e}")

    def on_company_deleted_from_dialog(self, ticker):
         """
         Slot called when a company is deleted via the Edit Dialog.
         Refreshes the library list to remove the deleted ticker.
         """
         # 1. Clear Preview (Visuals)
         self.on_company_changed("")
         
         # 2. Refresh Dropdown List (Data)
         self.refresh_company_list()
         
         # 3. Reset Dropdown Selection
         if hasattr(self, 'header_widget'):
              self.header_widget.combo_companies.setCurrentIndex(0)
         
         QMessageBox.information(self, "Deleted", f"Company {ticker} was deleted successfully.")

    def open_edit_company_dialog(self):
        # Use header combo
        if not hasattr(self, 'header_widget') or sip.isdeleted(self.header_widget): return
        
        try:
            # CRITICAL FIX: Get Ticker from UserData, not Text (which contains Name)
            ticker = self.header_widget.combo_companies.currentData()
        except RuntimeError:
            return

        # Fallback if data is missing but text exists (unlikely but safe)
        if not ticker:
             text = self.header_widget.combo_companies.currentText()
             # Extract (TICKER) from "Name (TICKER)" if needed
             if "(" in text and ")" in text:
                 ticker = text.split("(")[-1].strip(")")
             else:
                 ticker = text
                 
        if not ticker or ticker == " Company " or ticker == "":
            return
            
        base_path = os.path.join(LIBRARY_ROOT, "STOCK", ticker)
        info_path = os.path.join(base_path, "company_info.json")
        
        current_data = {}
        if os.path.exists(info_path):
             try:
                 import json
                 with open(info_path, 'r') as f:
                     current_data = json.load(f)
             except: pass
        
        if not current_data:
            current_data = {"ticker": ticker}

        # CRITICAL FIX: Detach dialog from self to prevent parent-deletion crashes
        # dial = NewCompanyDialog(self) 
        dial = NewCompanyDialog(None)
        dial.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        dial.setWindowTitle(f"Edit Company: {ticker}")
        
        
        # CONNECT SIGNAL for refresh
        try:
            dial.company_deleted.connect(lambda t: self.on_company_deleted_from_dialog(t))
        except AttributeError:
            print("Warning: on_company_deleted_from_dialog not found")
        except Exception as e:
            print(f"Error connecting signal: {e}")
        
        # DEBUG: Keep reference to prevent GC
        self.keep_alive_dial = dial
        
        # Pre-fill
        dial.txt_name.setText(current_data.get("name", ""))
        dial.txt_ticker.setText(current_data.get("ticker", ticker))
        dial.txt_ticker.setReadOnly(False)
        
        # Activate Delete Mode
        dial.enable_delete_mode(ticker)
        # dial.enable_delete_mode(ticker) # DISABLED FOR ISOLATION
        
        # New Yahoo Ticker load (fallback to empty if not set)
        dial.txt_yahoo_ticker.setText(current_data.get("yahoo_ticker", ""))
        
        # Load Aliases from DB
        companies = self.companies_manager.get_companies()
        db_company = next((c for c in companies if c['ticker'] == ticker), None)
        db_aliases = db_company.get('aliases', '') if db_company else ""
        if not db_aliases: db_aliases = "" # Handle None
        dial.txt_aliases.setText(db_aliases)
        
        dial.combo_exchange.setCurrentText(current_data.get("exchange", ""))
        dial.combo_currency.setCurrentText(current_data.get("currency", ""))
        dial.txt_idea.setText(current_data.get("idea_source", ""))
        
        # Load Category from DB (Best source) or JSON
        companies = self.companies_manager.get_companies()
        db_cat = next((c['category'] for c in companies if c['ticker'] == ticker), "Watchlist")
        if not db_cat: db_cat = "Watchlist"
        dial.combo_category.setCurrentText(db_cat)

        # New Fields
        dial.spin_price.setValue(float(current_data.get("price_first_time", 0.0)))
        dial.combo_kpi_type.setCurrentText(current_data.get("kpi_first_time_type", "P/S"))
        dial.spin_kpi_value.setValue(float(current_data.get("kpi_first_time_value", 0.0)))
        
        # LINKS MIGRATION & LOADING
        custom_links = current_data.get("custom_links", [])
        
        # If no custom links but verify generic fields exist (backward compatibility)
        if not custom_links:
             ir = current_data.get("ir_website", "")
             pr = current_data.get("pr_website", "")
             news = current_data.get("news_urls", [])
             
             if ir: custom_links.append({"title": "IR Web", "url": ir})
             if pr: custom_links.append({"title": "PR Web", "url": pr})
             for n_url in news:
                 custom_links.append({"title": "News", "url": n_url})
                 
        # Populate Dialog
        if custom_links:
            for link in custom_links:
                dial.add_link_field(link.get("title", ""), link.get("url", ""), link.get("color", "#3498DB"))
        else:
            dial.add_link_field() # Empty one to start
                 
        # Show Hours for Edit
        dial.lbl_hours.show()
        dial.spin_hours.show()
        dial.spin_hours.setValue(current_data.get("total_hours", 0.0))
        dial.btn_create.setText("Save Changes")
        
        # EXPERIMENTAL: Hide/Show to force clean state
        # self.setVisible(False) 
        # Actually, let's just disable updates to prevent painting during transition
        # self.setUpdatesEnabled(False)
        
        res = dial.exec()
        
        # self.setUpdatesEnabled(True)
        # self.setVisible(True)
        
        blackbox.log(f"Edit Dialog Exec Result: {res}")
        
        # SAFETY: Process pending events while we still have control
        QApplication.processEvents()
        
        # Restore focus to self to avoid Qt getting confused about where focus goes
        if not sip.isdeleted(self):
            self.setFocus()
            
        blackbox.log("Events processed. Checking result...")
        
        if res:
            blackbox.log("Edit accepted. extracting data...")
            # If exec() returns True (Accepted), it means User clicked SAVE.
            # If User clicked DELETE, dial called reject(), so we SKIP this block.
            # This prevents crashing by trying to save to a deleted folder.
            new_data = dial.get_data()
            blackbox.log("Data extracted.")
            
            try:
                new_data = dial.get_data()
                blackbox.log("Data extracted.")
                
                # DEFER SAVING to ensure dialog is fully closed and stack unwound
                blackbox.log("Scheduling deferred save...")
                QTimer.singleShot(200, lambda: self.process_edit_save(ticker, new_data, info_path))
                
            except Exception as e:
                blackbox.error("Error extracting data", e)
        
        blackbox.log("Exiting open_edit_company_dialog safely.")

    def process_edit_save(self, ticker, new_data, info_path):
        """
        Executes the actual save logic AFTER the dialog has closed.
        This prevents focus/event-loop crashes.
        """
        blackbox.log(f"Executing process_edit_save for {ticker}")
        try:
            # --- VALIDATION (Edit Mode) ---
            new_ticker = new_data.get('ticker', ticker).strip().upper()
            old_ticker = ticker.strip().upper()
            
            if new_ticker != old_ticker:
                # Call rename_company!
                from core.services.company_service import CompanyService
                success, err_msg = CompanyService().rename_company(old_ticker, new_ticker)
                if not success:
                    QMessageBox.critical(None, "Rename Error", f"Could not rename company ticker:\n{err_msg}")
                    return
                # Update variables for subsequent save logic
                ticker = new_ticker
                info_path = info_path.replace(f"\\STOCK\\{old_ticker}", f"\\STOCK\\{new_ticker}").replace(f"/STOCK/{old_ticker}", f"/STOCK/{new_ticker}")

            new_exchange = new_data.get('exchange', '')
            yahoo_ticker_edit = price_fetcher.get_yahoo_ticker(ticker, new_exchange)
            
            # isValid = price_fetcher.validate_ticker(yahoo_ticker_edit)
            # if not isValid:
            #     if sip.isdeleted(self): 
            #         # If self is deleted, we can't show a message box parented to self.
            #         # Try using None as parent (desktop)
            #         parent = None
            #     else: 
            #         parent = self
            #     
            #     # Use parent=None if self is deleted, or just safeguard
            #     # ret = QMessageBox.warning(parent, "Validation Warning", 
            #     #                           f"Ticker '{yahoo_ticker_edit}' was NOT found on Yahoo Finance.\n\n"
            #     #                           f"Automation may fail.\n"
            #     #                           f"Do you want to proceed with saving changes?",
            #     #                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            #     # if ret == QMessageBox.StandardButton.No:
            #     #      return # Cancel save
            blackbox.log("Yahoo Validation Warning SKIPPED (Ghost Mode).")
                     
            # --- END VALIDATION ---
            
            # Allow hours update from dialog (removed overwrite logic)
            
            # 2. Write JSON (RESTORED)
            import json
            try:
                 with open(info_path, 'w') as f:
                     json.dump(new_data, f, indent=4)
                 blackbox.log("JSON wrote successfully.")
            except Exception as e:
                 blackbox.error("JSON Write Error", e)
                 return

            # 3. Show Success (Parent=None to be safe)
            # if not sip.isdeleted(self):
            #      QMessageBox.information(None, "Success", "Company info updated.")
            blackbox.log("Success Message SKIPPED (Ghost Mode).")

            # 4. Trigger UI Refresh (Deferred again? No, we are already deferred)
            # Restore normal updates step-by-step
            
            # Update DB (Restored)
            if self.companies_manager:
                self.companies_manager.update_company(ticker, 
                                                      name=new_data.get('name', ticker),
                                                      category=new_data.get('category', 'Watchlist'),
                                                      primary_exchange=new_data.get('exchange', ''),
                                                      currency=new_data.get('currency', 'USD'),
                                                      yahoo_ticker=new_data.get('yahoo_ticker', ''),
                                                      aliases=new_data.get('aliases', ''),
                                                      metric_type=new_data.get('kpi_first_time_type', 'P/E'))
                                                  
            # --- SYNC WITH FORTRESS_VAULT.DB --- (DISABLED FOR ISOLATION)
            # try:
            #     session = self.Session()
            #     db_comp = session.query(DBCompany).filter_by(ticker=ticker).first()
            #     if db_comp:
            #         db_comp.name = new_data.get('name', ticker)
            #         db_comp.yahoo_ticker = new_data.get('yahoo_ticker') or None
            #         db_comp.primary_exchange = new_data.get('exchange')
            #         db_comp.aliases = new_data.get('aliases') or None
            #         session.commit()
                    
                    # Trigger Fetch if Ticker Changed
                    # em = EarningsManager(self.Session)
                    # em.update_company(ticker, session)
            #     session.close()
            # except Exception as e:
            #     print(f"Error syncing edit to Fortress DB: {e}")
            
            # CRITICAL FIX: Defer this update to next event loop iteration.
            # Use a lambda that checks for validity again just in case.
            blackbox.log("Scheduling safe_refresh...")
            QTimer.singleShot(0, lambda: self.safe_refresh(ticker))
            
            blackbox.log("Save Complete. Ready to re-enable DB sync.")
            
        except Exception as e:
            blackbox.error("Error in process_edit_save", e)
            # if not sip.isdeleted(self):
            #    QMessageBox.critical(self, "Error", f"Could not save info: {e}")

    def safe_refresh(self, ticker):
        """Helper to refresh UI safely after a delay."""
        blackbox.log(f"safe_refresh called for {ticker}")
        try:
            if not sip.isdeleted(self):
                # Refresh list so combo box has the updated list of companies
                self.refresh_company_list()
                
                # Set selection to the new ticker
                if hasattr(self, 'header_widget') and not sip.isdeleted(self.header_widget):
                    combo = self.header_widget.combo_companies
                    idx = combo.findData(ticker)
                    if idx >= 0:
                        combo.blockSignals(True)
                        combo.setCurrentIndex(idx)
                        combo.blockSignals(False)
                
                self.on_company_changed(ticker)
                
                # Notify Global (e.g. Companies View needs to know Currency changed)
                self.company_updated.emit(ticker)
                
                # Notify AppState that active company has changed
                from ui.app_state import AppState
                AppState.get().set_active_company(ticker)
                
        except Exception as e:
            blackbox.error(f"Error in safe_refresh: {e}")

    def on_file_dropped(self):
        self.update_preview()

    def update_preview(self):
        ticker = "NA"
        if hasattr(self, 'header_widget'):
            ticker = self.header_widget.combo_companies.currentText()
        if not ticker or ticker == " Company " or ticker == "":
             ticker = "NA"
        date_str = self.date_edit.text()
        period = self.combo_period.currentText() # Use Text for key
        doc_type = self.combo_type.currentText() # Use Text for key
        extra = self.txt_extra.text()
        
        ext = ".pdf"
        if self.drop_area.current_files:
            ext = os.path.splitext(self.drop_area.current_files[0])[1]
            
        filename = generate_sne_filename(date_str, ticker, period, doc_type, extra, ext)
        # self.lbl_preview.setText(filename) # Removed as UI element is gone

    def on_time_logged(self, ticker):
        """Called when Pomodoro logs time for a company"""
        # If this company is currently selected, refresh the display
        if hasattr(self, 'header_widget'):
            current = self.header_widget.combo_companies.currentText()
            if current == ticker:
                # Reload data to reflect new hours
                self.on_company_changed(ticker)

    def _refresh_progress_bar(self):
        """
        Called when a file's status/category is changed in the embedded library widget.
        Recalculates and updates the progress bar without reloading the whole library.
        """
        try:
            if not hasattr(self, 'header_widget') or not hasattr(self, 'library_manager_widget'):
                return

            real_ticker = ""
            try:
                data = self.header_widget.combo_companies.currentData()
                real_ticker = data if data else self.header_widget.combo_companies.currentText()
            except Exception:
                return

            if not real_ticker or real_ticker == " Company ":
                return

            lib_mgr = self.library_manager_widget.library_manager
            pct, _stats = lib_mgr.get_company_progress(real_ticker)
            hours = lib_mgr.get_company_hours(real_ticker)

            # Only update progress_bar - don't rebuild full header to avoid flicker
            self.header_widget.update_info(real_ticker, pct, hours)
            print(f"[Progress] Updated {real_ticker}: {pct}% / {hours:.1f}h")
        except Exception as e:
            print(f"[Progress] Error refreshing progress bar: {e}")


    def process_file(self):
        if not self.drop_area.current_files:
            QMessageBox.warning(self, "No File", "Please drop a file first.")
            return
            
        f_path = self.drop_area.current_files[0]
        # Fix: Use header widget combo as local combo was removed
        if hasattr(self, 'header_widget'):
            ticker = self.header_widget.combo_companies.currentText()
        else:
            ticker = ""
            
        if not ticker:
             QMessageBox.warning(self, "No Ticker", "Please select or create a company.")
             return

        date_str = self.date_edit.text()
        try:
             year = int(date_str.split('-')[0])
        except:
             year = datetime.datetime.now().year # Fallback
        period = self.combo_period.currentText()
        doc_type = self.combo_type.currentText()
        extra = self.txt_extra.text()
        ext = os.path.splitext(f_path)[1]
        
        sne_name = generate_sne_filename(date_str, ticker, period, doc_type, extra, ext)
        dest_dir = get_sne_destination_folder(LIBRARY_ROOT, ticker, doc_type, year)
        
        os.makedirs(dest_dir, exist_ok=True)
        
        try:
            shutil.copy2(f_path, os.path.join(dest_dir, sne_name))
            QMessageBox.information(self, "Success", f"File saved:\n{sne_name}")
            self.drop_area.clear_files()
            self.txt_extra.clear()
            
            # Refresh Updates
            self.status_widget.update_status(ticker)
            self.library_manager_widget.load_specific_company(ticker)
            
            # Trigger Last Update Calculation (Live)
            new_date = self.companies_manager.calculate_last_update(ticker)
            self.companies_manager.update_company(ticker, last_update=new_date)
            # Notify Header to reload companies? Or is it auto? 
            # Header reads from DB or memory? Usually CompaniesView reads DB.
            # We might need to refresh CompaniesView if it's visible.
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to move file: {e}")

    def format_date_input(self, text):
        """Auto-formats date input to YYYY-MM-DD"""
        # Remove any non-digit characters
        clean_text = re.sub(r'[^0-9]', '', text)
        
        formatted = clean_text
        if len(clean_text) > 4:
            formatted = formatted[:4] + '-' + clean_text[4:]
        if len(clean_text) > 6:
            formatted = formatted[:7] + '-' + clean_text[6:]
            
        if len(formatted) > 10:
            formatted = formatted[:10]
            
        if self.date_edit.text() != formatted:
             self.date_edit.blockSignals(True)
             self.date_edit.setText(formatted)
             self.date_edit.setCursorPosition(len(formatted))
             self.date_edit.blockSignals(False)
             self.update_preview()
             
    def get_date(self):
        """Helper to get QDate from the text input"""
        try:
            return datetime.datetime.strptime(self.date_edit.text(), "%Y-%m-%d").date()
        except:
             return datetime.datetime.now().date() # Fallback
