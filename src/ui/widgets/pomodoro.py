from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
                             QComboBox, QMessageBox, QSpinBox, QDialog, QDialogButtonBox, QLineEdit, QFrame)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QIntValidator
from ui.styles import COLORS
import os
import csv
from datetime import datetime
import threading
import time
import winsound

from config import LIBRARY_ROOT as _LIBRARY_ROOT_PATH
LIBRARY_ROOT = str(_LIBRARY_ROOT_PATH)

from core.services import CompanyService, SpecialService

class CompanySelectionDialog(QDialog):
    def __init__(self, companies, situations=[], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Task / Company")
        self.setFixedWidth(350)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']};")
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Select a company or situation to focus on:")
        layout.addWidget(lbl)
        
        self.combo = QComboBox()
        self.combo.setStyleSheet(f"background-color: {COLORS['surface_light']}; padding: 5px;")
        
        # Sort Stocks
        for ticker in sorted(companies.keys()):
            self.combo.addItem(f"STOCK: {ticker}", {'type': 'stock', 'id': ticker, 'name': ticker})
            
        # Sort Situations
        for s in situations:
            self.combo.addItem(f"SIT: {s['title']}", {'type': 'situation', 'id': s['id'], 'name': s['title']})
            
        layout.addWidget(self.combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected(self):
        return self.combo.currentData()



class PomodoroWidget(QWidget):
    time_logged_signal = pyqtSignal(str) # Ticker or Title
    
    def __init__(self, portfolio_manager=None):
        super().__init__()
        self.portfolio_manager = portfolio_manager
        self.special_manager = SpecialService()
        self.companies_manager = CompanyService()
        self.setStyleSheet(f"background-color: {COLORS['surface_light']}; border-radius: 8px; padding: 10px;")
        
        layout = QVBoxLayout(self)
        
        # 1. Timer Display Box
        self.timer_container = QFrame()
        self.timer_container.setStyleSheet(f"background-color: {COLORS['surface']}; border-radius: 10px; border: 1px solid {COLORS['border']};")
        timer_layout = QVBoxLayout(self.timer_container)
        timer_layout.setContentsMargins(5, 5, 5, 5) 
        
        # Editable Timer Display
        self.timer_edit = QLineEdit("25:00")
        self.timer_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_edit.setStyleSheet(f"font-size: 42px; font-weight: bold; color: {COLORS['primary']}; background: transparent; border: none;")
        self.timer_edit.editingFinished.connect(self.on_time_edited)
        timer_layout.addWidget(self.timer_edit)
        
        layout.addWidget(self.timer_container)
        
        self.lbl_company = QLabel("")
        self.lbl_company.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_company.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; margin-bottom: 5px; font-weight: bold;")
        layout.addWidget(self.lbl_company)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        # 1. Start (Dull Green)
        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self.toggle_timer)
        self.btn_start.setStyleSheet("background-color: #388E3C; color: white; border: none; font-weight: bold;") 
        btn_layout.addWidget(self.btn_start)
        
        # 2. Reset (Dark Red)
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset_timer)
        self.btn_reset.setStyleSheet("background-color: #B71C1C; color: white; border: none; font-weight: bold;")
        btn_layout.addWidget(self.btn_reset)
        
        # 3. Log (Dark Blue)
        self.btn_log = QPushButton("Log") 
        self.btn_log.clicked.connect(self.manual_log)
        self.btn_log.setStyleSheet("background-color: #0D47A1; color: white; border: none; font-weight: bold;")
        self.btn_log.setEnabled(False) 
        btn_layout.addWidget(self.btn_log)
        
        layout.addLayout(btn_layout)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        
        self.default_minutes = 25
        self.time_left = self.default_minutes * 60
        self.is_running = False
        self.current_task = None # {type, id, name}

    def set_active_company(self, company_obj_or_dict):
        # External set (e.g. from F5 button)
        if isinstance(company_obj_or_dict, dict):
            self.current_task = company_obj_or_dict
            self.lbl_company.setText(f"Focusing: {self.current_task['name']}")
        else:
             # Assume Stock Object
             self.current_task = {'type': 'stock', 'id': company_obj_or_dict.ticker, 'name': company_obj_or_dict.ticker}
             self.lbl_company.setText(f"Focusing: {self.current_task['name']}")
        
        # Auto-reset/ready
        self.reset_timer()

    def on_time_edited(self):
        text = self.timer_edit.text()
        try:
            if ":" in text:
                parts = text.split(":")
                mins = int(parts[0])
                secs = int(parts[1]) if len(parts) > 1 else 0
            else:
                mins = int(text)
                secs = 0
            
            self.default_minutes = mins # Store as new default
            self.time_left = mins * 60 + secs
            self.update_display()
        except ValueError:
            self.update_display()

    def toggle_timer(self):
        if not self.is_running:
            # 1. Select if not set
            if not self.current_task:
                # Load ALL companies from DB (Portfolio + Watchlist)
                all_comps_list = self.companies_manager.get_companies()
                # Convert to dict for Dialog: {ticker: {data}}
                stocks = {c['ticker']: c for c in all_comps_list}
                
                situations = self.special_manager.get_all_situations()
                
                if not stocks and not situations:
                    QMessageBox.warning(self, "No Tasks", "No companies or situations found.")
                    return

                dialog = CompanySelectionDialog(stocks, situations, self)
                
                # Auto-select active context from MainWindow
                main_win = self.window()
                pre_select_id = None
                pre_select_type = None
                if hasattr(main_win, "content_area"):
                    current_widget = main_win.content_area.currentWidget()
                    if current_widget:
                        if hasattr(current_widget, "header_widget") and hasattr(current_widget.header_widget, "combo_companies"):
                            pre_select_id = current_widget.header_widget.combo_companies.currentData()
                            pre_select_type = 'stock'
                        elif hasattr(current_widget, "current_situation_id") and current_widget.current_situation_id:
                            pre_select_id = current_widget.current_situation_id
                            pre_select_type = 'situation'

                if pre_select_id and pre_select_type:
                    for i in range(dialog.combo.count()):
                        data = dialog.combo.itemData(i)
                        if data and data.get('type') == pre_select_type and data.get('id') == pre_select_id:
                            dialog.combo.setCurrentIndex(i)
                            break

                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.current_task = dialog.get_selected()
                    self.lbl_company.setText(f"Focusing: {self.current_task['name']}")
                else:
                    return

            # Start
            self.timer_edit.setReadOnly(True)
            self.timer.start(1000)
            self.btn_start.setText("Pause")
            self.btn_start.setStyleSheet(f"background-color: {COLORS['primary']}; color: black; border: none; font-weight: bold;")
            self.btn_log.setEnabled(True)
            self.is_running = True
        else:
            self.timer.stop()
            self.btn_start.setText("Resume")
            self.btn_start.setStyleSheet("background-color: #388E3C; color: white; border: none; font-weight: bold;")
            self.is_running = False

    def manual_log(self):
         if self.current_task:
             self.log_session()

    def reset_timer(self):
        self.timer.stop()
        self.is_running = False
        self.timer_edit.setReadOnly(False)
        self.time_left = self.default_minutes * 60
        self.update_display()
        self.btn_start.setText("Start")
        self.btn_start.setStyleSheet("background-color: #388E3C; color: white; border: none; font-weight: bold;")
        self.btn_log.setEnabled(False)
        # Keep current task selected for convenience? User can clear by restart?
        # self.current_task = None 
        # self.lbl_company.setText("")

    def update_timer(self):
        if self.time_left > 0:
            self.time_left -= 1
            self.update_display()
        else:
            self.timer.stop()
            self.is_running = False
            self.timer_edit.setText("DONE!")
            
            threading.Thread(target=self.play_alarm, daemon=True).start()
            
            # Defer logging to avoid blocking timer callback with modal dialog
            QTimer.singleShot(100, self._handle_session_end)

    def _handle_session_end(self):
        self.log_session()
        self.reset_timer()

    def play_alarm(self):
        for _ in range(3):
            winsound.Beep(1000, 800)
            time.sleep(0.2)

    def update_display(self):
        mins, secs = divmod(self.time_left, 60)
        self.timer_edit.setText(f"{mins:02d}:{secs:02d}")

    def log_session(self):
        # 1. Log to CSV (Audit Trail)
        if not os.path.exists(LIBRARY_ROOT):
            os.makedirs(LIBRARY_ROOT, exist_ok=True)
            
        log_file = os.path.join(LIBRARY_ROOT, "pomodoro_log.csv")
        
        try:
            with open(log_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                now = datetime.now()
                writer.writerow([
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S"),
                    self.current_task['name'],
                    self.default_minutes
                ])
        except Exception as e:
            print(f"Error logging session: {e}")
            
        # 2. Add to Total
        consumed_seconds = (self.default_minutes * 60) - self.time_left
        minutes_done = round(consumed_seconds / 60.0)
        if minutes_done < 0: minutes_done = 0
        
        reply = QMessageBox.question(self, "Log Time", f"Add {minutes_done} mins to {self.current_task['name']}?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.current_task['type'] == 'stock':
                self.save_time_to_company(self.current_task['id'], minutes_done)
            else:
                 self.special_manager.log_time(self.current_task['id'], minutes_done * 60)
                 self.time_logged_signal.emit(self.current_task['name'])

    def save_time_to_company(self, ticker, minutes):
        stock_path = os.path.join(LIBRARY_ROOT, "STOCK", ticker)
        info_path = os.path.join(stock_path, "company_info.json")
        
        try:
            import json
            data = {}
            if os.path.exists(info_path):
                with open(info_path, 'r') as f:
                    data = json.load(f)
            
            current_hours = data.get('total_hours', 0.0)
            added_hours = minutes / 60.0
            data['total_hours'] = current_hours + added_hours
            
            with open(info_path, 'w') as f:
                json.dump(data, f, indent=4)
                
            QMessageBox.information(self, "Time Saved", f"Added {minutes} mins to {ticker}.\nTotal: {data['total_hours']:.2f} h")
            self.time_logged_signal.emit(ticker)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save time: {e}")
