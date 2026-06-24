from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QListWidget, QStackedWidget, QLabel, QListWidgetItem, QApplication,
                             QPushButton, QMessageBox)

from PyQt6.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
import ctypes
from ctypes import wintypes
from config import LIBRARY_ROOT, STOCK_PATH, DESKTOP_ICON
from ui.styles import STYLESHEET, COLORS
from ui.app_state import AppState
from ui.widgets.dashboard import DashboardWidget
from ui.views.companies_view import CompaniesView
from ui.widgets.pdf_manager import PdfManagerWidget
from ui.widgets.calendar_view import CalendarWidget
from ui.widgets.pomodoro import PomodoroWidget
from ui.widgets.company_detail import CompanyDetailWidget
from ui.widgets.codigos import CodigosWidget
from ui.widgets.input_stock import InputStockWidget
from ui.widgets.special_situations import SpecialSituationsWidget
from ui.tools.runtime_designer import DesignerOverlay
from ui.widgets.prompt_library import PromptLibraryDialog
from ui.widgets.tools_widget import ToolsWidget
from ui.widgets.wealth_analytics import WealthAnalyticsWidget
from ui.widgets.objectives_widget import ObjectivesWidget
from ui.widgets.tikr_harvest import TikrHarvestWidget
from core.portfolio_manager import PortfolioManager
import webbrowser
import subprocess
import os
from version import __version__

# Worker for Async Backup
class BackupWorker(QThread):
    finished_signal = pyqtSignal(str) # Returns path or empty string
    
    def __init__(self, source_dir):
        super().__init__()
        self.source_dir = source_dir
        
    def run(self):
        try:
             from core.backup_manager import BackupManager
             # Call the blocking function here
             zip_file = BackupManager.create_backup(self.source_dir, show_msg=False)
             if zip_file:
                 self.finished_signal.emit(zip_file)
             else:
                 self.finished_signal.emit("")
        except Exception as e:
            print(f"Backup Error in Thread: {e}")
            self.finished_signal.emit("")

class PlaceholderWidget(QWidget):
    def __init__(self, name):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel(f"Page: {name}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: #666;")
        layout.addWidget(label)

from PyQt6.QtGui import QShortcut, QKeySequence

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"EKKOMONOS {__version__} - Financial Dashboard")
        self.setWindowIcon(QIcon(os.path.join(os.getcwd(), "assets", "desktop_icon.ico")))
        self.resize(1600, 900)
        self.setMinimumSize(1200, 800) # Allow shrinking for split-screen
        self._initial_pos_set = False
        
        # Initialize DB and Session Factory
        from core.database import init_db, get_session_factory
        self.db_engine = init_db()
        self.session_factory = get_session_factory(self.db_engine)
        
        # Initialize Portfolio Manager
        self.portfolio_manager = PortfolioManager(str(STOCK_PATH))
        
        # Apply Theme
        self.setStyleSheet(STYLESHEET)
        
        # Main Layout Container
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QHBoxLayout(main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- Sidebar ---
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(250)
        self.sidebar.setStyleSheet(f"background-color: {COLORS['surface']}; border-right: 1px solid {COLORS['border']};")
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)
        
        # App Title in Sidebar
        
        title_label = QLabel("Ekomonos")
        title_label.setStyleSheet(f"color: {COLORS['primary']}; font-weight: bold; font-size: 32px; padding-top: 25px; padding-bottom: 5px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_layout.addWidget(title_label)
        
        subtitle_label = QLabel("COMPOUNDING LAB")
        subtitle_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px; padding-bottom: 20px;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_layout.addWidget(subtitle_label)

        # Navigation List
        self.nav_list = QListWidget()
        
        # 1. Dashboard (F1)
        self.nav_list.addItem("  Dashboard (F1)")
        # 2. Companies (F2)
        self.nav_list.addItem("  Companies (F2)")
        # 3. Calendar (F3) - MOVED UP
        self.nav_list.addItem("  Calendar (F3)")
        # 4. Library (F4) - MOVED & RENAMED
        self.nav_list.addItem("  Library (F4)")
        # 5. Special Situations (F5)
        self.nav_list.addItem("  Special Situations (F5)")
        # 6. Prompts (F6)
        self.nav_list.addItem("  Prompts (F6)")

        # 7. Analitica patrimonial (F7)
        self.nav_list.addItem("  Analitica patrimonial (F7)")
        # 8. Analitica de gastos (F8)
        self.nav_list.addItem("  Analitica de gastos (F8)")
        # 9. TIKR Harvest (F9)
        self.nav_list.addItem("  TIKR Harvest (F9)")
        
        # Spacer Item (Empty item with some height)
        # We need to consider this in index calculations if it's selectable, 
        # but we set flags to NoItemFlags so it shouldn't receive focus via arrows, 
        # but it exists in the list logic.
        spacer_item = QListWidgetItem("")
        spacer_item.setFlags(Qt.ItemFlag.NoItemFlags) 
        spacer_item.setSizeHint(QSize(0, 40)) 
        self.nav_list.addItem(spacer_item)
        
        # 10. Tools (F10) - MOVED & RENAMED
        self.nav_list.addItem("  Tools (F10)")
        # 11. Objetivos Anuales (F11)
        self.nav_list.addItem("  Objetivos Anuales (F11)")
        # 12. Glossary (F12)
        self.nav_list.addItem("  Glossary (F12)")

        self.nav_list.currentRowChanged.connect(self.switch_page)
        
        # No scroll — items always visible
        self.nav_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Expand to fill all available space between title and Pomodoro
        from PyQt6.QtWidgets import QSizePolicy
        self.nav_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.sidebar_layout.addWidget(self.nav_list)
        
        # Shortcuts for Navigation (F1 - F12)
        self.shortcuts = []
        for key_str, idx in [("F1", 0), ("F2", 1), ("F3", 2), ("F4", 3), 
                             ("F5", 4), ("F6", 5), ("F7", 6), ("F8", 7), 
                             ("F9", 8), ("F10", 10), ("F11", 11), ("F12", 12)]:
            sc = QShortcut(QKeySequence(key_str), self)
            sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(lambda i=idx: self.nav_list.setCurrentRow(i))
            self.shortcuts.append(sc)

        
        # Pomodoro Widget — anchored at the bottom of the sidebar
        self.pomodoro = PomodoroWidget(self.portfolio_manager)
        self.pomodoro.time_logged_signal.connect(self.on_pomodoro_logged)
        
        # Pomodoro anchored at the bottom — nav_list Expanding pushes it down naturally
        self.sidebar_layout.addWidget(self.pomodoro)
        
        self.designer_overlay = None

        self.main_layout.addWidget(self.sidebar)
        
        # --- Main Content Area ---
        self.content_area = QStackedWidget()
        self.main_layout.addWidget(self.content_area)
        
        # Initialize Pages & Reorder Content Stack to Match List
        
        # 1. Dashboard (Index 0)
        # 1. Dashboard (Index 0)
        self.dashboard_page = DashboardWidget()
        # Signals
        self.dashboard_page.request_new_idea.connect(self.on_dashboard_new_idea)
        self.dashboard_page.request_focus.connect(self.on_dashboard_focus)
        self.dashboard_page.request_diary.connect(lambda: self.nav_list.setCurrentRow(8)) # F9
        self.dashboard_page.request_broker.connect(self.open_tikr)
        
        self.content_area.addWidget(self.dashboard_page) 
        
        # 2. Companies (Index 1)
        self.companies_page = CompaniesView(str(LIBRARY_ROOT))
        self.content_area.addWidget(self.companies_page)
        
        # 3. Calendar (Index 2)
        # CalendarWidget now requires session_factory
        self.calendar_page = CalendarWidget(self.session_factory, self.portfolio_manager)
        self.calendar_page.company_selected.connect(self.open_company_in_library)
        self.calendar_page.special_situation_selected.connect(self.open_special_situation)
        self.content_area.addWidget(self.calendar_page)
        
        # 4. Library (InputStock) (Index 3)
        self.input_stock_page = InputStockWidget(self.portfolio_manager)
        self.input_stock_page.company_deleted.connect(self._on_company_deleted)
        self.input_stock_page.company_updated.connect(self.on_company_updated_globally)
        self.content_area.addWidget(self.input_stock_page)
        
        # 5. Specal Situations (Index 4)
        self.special_page = SpecialSituationsWidget(self.portfolio_manager)
        self.special_page.data_changed.connect(self.calendar_page.grid.refresh_data)
        self.special_page.data_changed.connect(lambda: self.companies_page.load_data(fetch_prices=False))
        self.content_area.addWidget(self.special_page)

        # Connect Companies Page Signals (AFTER ALL WIDGETS CREATED)
        # Connect Companies Page Signals (AFTER ALL WIDGETS CREATED)
        self.companies_page.request_open_company.connect(self.open_company_in_library)
        self.companies_page.request_open_special_situation.connect(self.open_special_situation)
        self.companies_page.request_edit_company.connect(self.on_request_edit_company)
        self.companies_page.request_edit_special_situation.connect(self.on_request_edit_special_situation)
        
        # 6. Prompts Library (Index 5)
        from ui.widgets.prompt_library import PromptLibraryWidget
        self.prompt_library_page = PromptLibraryWidget()
        self.content_area.addWidget(self.prompt_library_page)


        # 7. Analitica patrimonial (Index 6)
        self.wealth_analytics_page = WealthAnalyticsWidget()
        self.content_area.addWidget(self.wealth_analytics_page)
        
        # 8. Analitica de gastos (Index 7)
        self.content_area.addWidget(PlaceholderWidget("Analitica de gastos"))
        
        # 9. TIKR Harvest (Index 8)
        self.tikr_harvest_page = TikrHarvestWidget()
        self.content_area.addWidget(self.tikr_harvest_page)
        
        # Spacer in List (Index 9) -> No widget here, handled in switch_page
        
        # 10. Tools (Index 9 in Stack!)
        self.content_area.addWidget(ToolsWidget())
        
        # 11. Objetivos Anuales (Index 10 in Stack!)
        self.objectives_page = ObjectivesWidget()
        self.content_area.addWidget(self.objectives_page)
        
        # 12. Glossary (Index 11 in Stack!)
        self.content_area.addWidget(CodigosWidget())
        

        self.nav_list.setCurrentRow(0)

        # Connect AppState signals for cross-widget communication
        AppState.get().company_deleted.connect(self._on_company_deleted_global)
        AppState.get().company_created.connect(self._on_company_created_global)
        AppState.get().request_create_company.connect(self.open_new_company_dialog_with_ticker)


        # Auto-Snap to Left (Direct positioning)
        QTimer.singleShot(100, self.snap_to_left_half)
        
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtWidgets import QApplication, QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QComboBox
        if event.type() == QEvent.Type.KeyPress:
            # 1 to 7 keys on top row or numpad
            if Qt.Key.Key_1 <= event.key() <= Qt.Key.Key_7:
                focus_w = QApplication.focusWidget()
                
                # Verify if focus is on a text input. We shouldn't steal numbers if they are typing.
                is_input = False
                if isinstance(focus_w, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox)):
                    # Special check: if read-only, it's not a real input
                    if hasattr(focus_w, 'isReadOnly') and focus_w.isReadOnly():
                        is_input = False
                    else:
                        is_input = True
                elif isinstance(focus_w, QComboBox):
                    if focus_w.isEditable():
                        is_input = True
                        
                if is_input:
                    return False # Let input handle the number
                
                # Attempt tab switch on current page
                current_page = self.content_area.currentWidget()
                if current_page and hasattr(current_page, 'tabs') and hasattr(current_page.tabs, 'count'):
                    idx = event.key() - Qt.Key.Key_1
                    if idx < current_page.tabs.count():
                        # Switch only if the tabs widget is actually shown (F5 hides it when empty)
                        if current_page.tabs.isVisible():
                            current_page.tabs.setCurrentIndex(idx)
                            return True # Consume
        return super().eventFilter(obj, event)

    def snap_to_left_half(self):
        """
        Snaps the window to the left half using native Windows Aero Snap.
        Simulates Win+Left keystroke for proper title bar and snap behavior.
        """
        try:
            import ctypes
            import time
            from PyQt6.QtCore import QTimer
            
            # Windows Virtual Key Codes
            VK_LWIN = 0x5B  # Left Windows key
            VK_LEFT = 0x25  # Left Arrow key
            KEYEVENTF_KEYUP = 0x0002
            
            def send_snap_keys():
                """Send Win+Left keystroke to Windows"""
                try:
                    # Ensure window is active first
                    self.activateWindow()
                    self.raise_()
                    
                    # Small delay to ensure window is ready
                    time.sleep(0.1)
                    
                    # Press Windows key
                    ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
                    time.sleep(0.05)
                    
                    # Press Left Arrow
                    ctypes.windll.user32.keybd_event(VK_LEFT, 0, 0, 0)
                    time.sleep(0.05)
                    
                    # Release Left Arrow
                    ctypes.windll.user32.keybd_event(VK_LEFT, 0, KEYEVENTF_KEYUP, 0)
                    time.sleep(0.05)
                    
                    # Release Windows key
                    ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
                    
                    print("[SNAP] Applied native Windows snap to left half")
                    
                except Exception as e:
                    print(f"[SNAP] Error sending snap keys: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Use QTimer to delay snap until window is fully shown
            QTimer.singleShot(200, send_snap_keys)
            print("[SNAP] Scheduled Windows snap keys")
            
        except Exception as e:
            print(f"[SNAP] Error in snap_to_left_half: {e}")
            import traceback
            traceback.print_exc()


    def switch_page(self, index):
        # Handle the spacer index (9)
        if index == 9:
            return # Do nothing
            
        # Map list index to stacked widget index
        # List Index 0-8  -> Page Index 0-8
        # List Index 10 (Tools)              -> Page Index 9
        # List Index 11 (Glossary)           -> Page Index 10
        # List Index 12 (Objetivos Anuales)  -> Page Index 11
        
        page_index = index
        if index > 9:
            page_index = index - 1
            
        self.content_area.setCurrentIndex(page_index)

    def on_dashboard_company_selected(self, item):
        # Get ticker from the first column of the selected row
        row = item.row()
        ticker = self.dashboard_page.focus_table.item(row, 0).text()
        self.open_company_detail(ticker)

    def open_company_detail(self, ticker):
        # Create detail view for this ticker
        # We pass the portfolio manager from dashboard to reuse it
        detail_view = CompanyDetailWidget(ticker, self.portfolio_manager)
        
        # Check if we already have a detail view at the end
        # The number of static pages is 11 (0-10)
        if self.content_area.count() > 11:
            self.content_area.removeWidget(self.content_area.widget(11))
            
        self.content_area.addWidget(detail_view)
        # The new dynamic page is at index 11
        self.content_area.setCurrentIndex(11)

    def on_pomodoro_logged(self, task_name):
        if hasattr(self, 'input_stock_page'):
            try: self.input_stock_page.on_time_logged(task_name)
            except: pass
        if hasattr(self, 'special_page'):
            try: self.special_page.on_time_logged(task_name)
            except: pass

    def open_company_in_library(self, ticker):
        print(f"[MainWindow] open_company_in_library called for {ticker}")
        
        # CRITICAL ORDER FIX: Load the company BEFORE switching pages.
        # If we switch first, showEvent fires on InputStockWidget and re-loads
        # the OLD company (whatever was in the combo). By loading first we set
        # input_stock_page's internal state so that when showEvent fires it is
        # already in sync — or showEvent becomes a no-op.
        if hasattr(self, 'input_stock_page'):
            print(f"[MainWindow] Calling input_stock_page.load_company_from_link({ticker})")
            self.input_stock_page.load_company_from_link(ticker)
        else:
            print("[MainWindow] ERROR: No input_stock_page found!")

        # Switch to Library Page AFTER the company data is already loaded.
        # In new order: Library is Index 3
        self.nav_list.setCurrentRow(3)

    def _on_company_deleted(self, ticker: str):
        """Bridge: input_stock_page signal → AppState broadcast."""
        AppState.get().notify_company_deleted(ticker)

    def _on_company_deleted_global(self, ticker: str):
        """
        Called when AppState broadcasts a company deletion.
        Refreshes all views to remove the ghost entry.
        """
        print(f"[AppState] Global Refresh: {ticker} deleted.")
        try:
            self.companies_page.load_data(fetch_prices=False)
        except Exception as e:
            print(f"[AppState] Error refreshing CompaniesView: {e}")
        try:
            self.calendar_page.load_data()
        except Exception:
            pass

    def _on_company_created_global(self, ticker: str):
        """Called when AppState broadcasts a new company creation."""
        print(f"[AppState] Company created: {ticker}")
        try:
            self.companies_page.load_data(fetch_prices=False)
        except Exception:
            pass

    def on_company_deleted_globally(self, ticker: str):
        """Legacy alias — kept for compatibility, delegates to AppState."""
        self._on_company_deleted(ticker)

    def on_company_updated_globally(self, ticker):
        """
        Called when a company is updated (e.g. Currency Change) in InputStockWidget.
        Refreshes CompaniesView to reflect changes.
        """
        print(f"Global Update: Refreshing views for {ticker}")
        try:
            # Refresh Companies View (Table) w/o fetching new prices, just reload JSON
            self.companies_page.load_data(fetch_prices=False) 
        except Exception as e:
             print(f"Error refreshing CompaniesView on update: {e}")

    def open_special_situation(self, sit_id):
        print(f"[MainWindow] open_special_situation called with ID: {sit_id}")
        
        # Switch to Special Situations Page (Index 4)
        self.nav_list.setCurrentRow(4)
        
        # Select Situation
        try:
            self.special_page.select_situation(sit_id)
        except Exception as e:
            print(f"[MainWindow] CRASH prevented calling select_situation: {e}")
            import traceback
            traceback.print_exc()

    def on_request_edit_company(self, ticker):
        """Handle edit request from Companies View context menu"""
        print(f"[MainWindow] Edit Request for Company: {ticker}")
        self.open_company_in_library(ticker)
        # Delay to allow view switch and combo update
        def trigger_dialog():
            if hasattr(self.input_stock_page, 'open_edit_company_dialog'):
                self.input_stock_page.open_edit_company_dialog()
            else:
                print("Error: input_stock_page has no open_edit_company_dialog")
        
        QTimer.singleShot(300, trigger_dialog)

    def open_new_company_dialog_with_ticker(self, ticker, name=""):
        """Handle create request from TIKR Harvest / other sources"""
        print(f"[MainWindow] Create Request for Company with ticker: {ticker}, name: {name}")
        if hasattr(self, 'input_stock_page'):
            self.input_stock_page.open_new_company_dialog_with_ticker(ticker, name)


    def on_request_edit_special_situation(self, sit_id):
        """Handle edit request from Companies View context menu"""
        print(f"[MainWindow] Edit Request for Situation ID: {sit_id}")
        
        # 1. Switch View
        self.nav_list.setCurrentRow(4) # Special Situations
        
        # 2. Select Situation
        self.special_page.select_situation(sit_id)
        
        # 3. Open Dialog
        # Fetch fresh data to ensure we have valid dict
        data = self.special_page.manager.get_situation(sit_id)
        if data:
            # Short delay to ensure UI painted selection
            QTimer.singleShot(100, lambda: self.special_page.open_edit_dialog(data))
        else:
            QMessageBox.warning(self, "Error", f"Could not load data for situation ID {sit_id}")

    def toggle_designer_mode(self, active):
        if active:
            if not self.designer_overlay:
                self.designer_overlay = DesignerOverlay(self)
            self.designer_overlay.show()
            self.designer_overlay.raise_()
            QMessageBox.information(self, "Designer Mode Active", 
                                    "Visual Designer Enabled.\n\n"
                                    "- HOVER to highlight.\n"
                                    "- CLICK to select.\n"
                                    "- DRAG handles to resize (modifies Stretch factors).")
        else:
            if self.designer_overlay:
                self.designer_overlay.save_report()
                self.designer_overlay.hide()
                self.designer_overlay = None # Fully reset to clear logs? or Keep?
                self.designer_overlay = None # Fully reset to clear logs? or Keep?
                # Reset for fresh session to avoid duplicate logs in next report
                # If we recreate on start, setting to None is fine.

    def launch_antigravity(self):
        # 1. Open VS Code IMMEDIATELY (Non-blocking)
        try:
             subprocess.Popen(["code", "."], cwd=os.getcwd(), shell=True)
        except Exception as e:
             QMessageBox.warning(self, "Error", f"Could not launch VS Code:\n{e}")

        # 2. Add extra dev functions here if needed
        pass

    def save_app_state(self):
        # User requested a Popup confirmation before backup
        reply = QMessageBox.question(self, "Backup", 
                                     "Do you want to create a Backup ZIP?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            # Trigger Backup in Background
            self.run_background_backup("Backup Complete.\nSaved to:\n")

    def run_background_backup(self, success_prefix):
        # Prevent multiple backups running at once? (Optional, but good practice)
        if hasattr(self, 'backup_worker') and self.backup_worker.isRunning():
            print("Backup already in progress...")
            return

        self.backup_worker = BackupWorker(os.getcwd())
        
        def on_backup_complete(zip_file):
            if zip_file:
                 # Optional: Show toast or status bar instead of Box to be less intrusive?
                 # For now, user requested unresponsive fix, so a box at the end is fine,
                 # as long as it doesn't freeze DURING the process.
                 # Actually, let's just use status bar if possible, or a non-modal info?
                 # Used QMessageBox for visibility as requested previously.
                 QMessageBox.information(self, "System", f"{success_prefix}{zip_file}")
            else:
                 QMessageBox.warning(self, "Backup Failed", "Could not create backup.")
        
        self.backup_worker.finished_signal.connect(on_backup_complete)
        self.backup_worker.start()

    def open_gemini_library(self):
        dlg = PromptLibraryDialog(self)
        dlg.exec()

    def open_tikr(self):
        # Force chrome on Windows
        try:
             # Use Popen to avoid blocking if webbrowser decides to wait
            subprocess.Popen(["start", "chrome", "https://tikr.com"], shell=True)
        except:
            webbrowser.open("https://tikr.com")

    def on_dashboard_new_idea(self):
        # Switch to F5 (Special Situations)
        self.nav_list.setCurrentRow(4)
        # Open New Dialog
        if hasattr(self.special_page, 'open_add_dialog'):
            self.special_page.open_add_dialog()

    def on_dashboard_focus(self):
        # Focus on Pomodoro Widget in Sidebar
        # Optionally start it or just highlight inputs
        self.pomodoro.timer_edit.setFocus()
        self.pomodoro.timer_edit.selectAll()

