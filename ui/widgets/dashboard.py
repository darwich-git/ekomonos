from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGridLayout, QPushButton, QFrame, QListWidget, 
                             QListWidgetItem, QProgressBar, QSizePolicy, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QSize
from PyQt6.QtGui import QIcon, QFont
from ui.styles import COLORS
from core.services import CompanyService, SpecialService
from core.services.price_service import PriceService
from ui.app_state import AppState
from config import POMODORO_LOG
import os
import csv
from datetime import datetime, timedelta

_POMODORO_LOG = str(POMODORO_LOG)

class DashboardCardFrame(QFrame):
    def __init__(self, title, accent_color=COLORS['primary']):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        # Header
        header = QLabel(title)
        header.setStyleSheet(f"color: {accent_color}; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        self.layout.addWidget(header)
        
        # Divider
        # line = QFrame()
        # line.setFrameShape(QFrame.Shape.HLine)
        # line.setStyleSheet(f"color: {COLORS['border']};")
        # self.layout.addWidget(line)

    def add_widget(self, widget):
        self.layout.addWidget(widget)
        
    def add_stretch(self):
        self.layout.addStretch()

# --- 1. RADAR (Upcoming Dates) ---
class DashboardRadarWidget(DashboardCardFrame):
    def __init__(self, portfolio_manager, special_manager):
        super().__init__("📡 RADAR (7 Days)", COLORS['warning'])
        self.pm = portfolio_manager
        self.sm = special_manager
        self._init_content()
        
    def _init_content(self):
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"background: transparent; border: none; font-size: 12px;")
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.add_widget(self.list_widget)
        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        events = []
        today = QDate.currentDate()
        limit = today.addDays(7)
        
        # 1. Earnings/Calendar (Mock for now, or fetch if PM has logic)
        # Assuming PM doesn't strictly hold upcoming events in memory efficiently without full scan.
        # We will skip PM scan for speed in Dashboard, or define a light fetch.
        # Use Special Situations Target Dates
        
        situations = self.sm.get_all_situations()
        for s in situations:
            t_date = s.get('target_date')
            if t_date:
                # Convert to QDate
                if isinstance(t_date, str):
                    try: d = datetime.strptime(t_date, "%Y-%m-%d").date()
                    except: continue
                elif isinstance(t_date, datetime):
                    d = t_date.date()
                else:
                    continue
                    
                qd = QDate(d.year, d.month, d.day)
                if today <= qd <= limit:
                    days = today.daysTo(qd)
                    events.append({'date': qd, 'title': f"{s['title']} (Target)", 'days': days})

        # Sort
        events.sort(key=lambda x: x['days'])

        if not events:
            item = QListWidgetItem("No imminent events.")
            item.setForeground(Qt.GlobalColor.gray)
            self.list_widget.addItem(item)
            return

        for e in events:
            txt = f"[T-{e['days']}] {e['title']}"
            if e['days'] == 0: txt = f"[TODAY] {e['title']}"
            elif e['days'] == 1: txt = f"[TOMORROW] {e['title']}"
            
            item = QListWidgetItem(txt)
            if e['days'] <= 1:
                item.setForeground(Qt.GlobalColor.red)
            else:
                item.setForeground(Qt.GlobalColor.white)
            self.list_widget.addItem(item)

# --- 2. OPPORTUNITY MONITOR ---
class DashboardOpportunityWidget(DashboardCardFrame):
    def __init__(self, special_manager):
        super().__init__("💎 OPPORTUNITY MONITOR", COLORS['primary'])
        self.sm = special_manager
        self._init_content()
        
    def _init_content(self):
        # Stats Row
        self.stats_lbl = QLabel()
        self.stats_lbl.setStyleSheet("color: white; font-size: 12px; border: none; background: transparent;")
        self.add_widget(self.stats_lbl)
        
        # Top 3 List
        self.top_list = QListWidget()
        self.top_list.setStyleSheet("background: transparent; border: none;")
        self.add_widget(self.top_list)
        
        self.refresh()
        
    def refresh(self):
        sits = self.sm.get_all_situations()
        
        # Capital
        total_cap = sum(s.get('capital_allocated', 0) for s in sits)
        active_count = sum(1 for s in sits if s.get('status') == 'Active')
        pipeline_count = sum(1 for s in sits if s.get('status') == 'Pipeline')
        
        self.stats_lbl.setText(f"Active: {active_count} | Pipeline: {pipeline_count}\nCapital Allocated: ${total_cap:,.0f}")
        
        # Rank by Spread/TIR (Mock rank by title for now, or calc)
        # Let's show top 3 Active
        active_sits = [s for s in sits if s.get('status') == 'Active']
        # Mock sort logic here if we had live prices
        
        self.top_list.clear()
        if not active_sits:
            self.top_list.addItem(QListWidgetItem("No active opportunities."))
        else:
            for s in active_sits[:3]:
                # Try fetch TIR if calc exists
                spec = s.get('specific_data', {})
                tir = spec.get('annualized_irr', 0)
                spread = spec.get('spread', 0)
                
                txt = f"{s['title']} - TIR: {tir:.1f}%"
                item = QListWidgetItem(txt)
                item.setForeground(Qt.GlobalColor.green)
                self.top_list.addItem(item)

# --- 3. PRODUCTIVITY (Deep Work) ---
class DashboardProductivityWidget(DashboardCardFrame):
    def __init__(self):
        super().__init__("🧠 DEEP WORK", COLORS['accent'])
        self._init_content()
        
    def _init_content(self):
        self.hour_lbl = QLabel("0.0 h")
        self.hour_lbl.setStyleSheet(f"font-size: 36px; font-weight: bold; color: {COLORS['text_main']}; border: none; background: transparent;")
        self.hour_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_widget(self.hour_lbl)
        
        self.sub_lbl = QLabel("Focus Today")
        self.sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_lbl.setStyleSheet("color: #888; border: none; background: transparent;")
        self.add_widget(self.sub_lbl)
        
        self.refresh()
        
    def refresh(self):
        # Read CSV
        total_mins = 0
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        if os.path.exists(_POMODORO_LOG):
            try:
                with open(_POMODORO_LOG, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if not row: continue
                        if row[0] == today_str:
                            try: total_mins += float(row[3])
                            except: pass
            except: pass
            
        hours = total_mins / 60.0
        self.hour_lbl.setText(f"{hours:.1f} h")

# --- 4. CONTINUITY (Recent) ---
class DashboardContinuityWidget(DashboardCardFrame):
    def __init__(self, special_manager):
        super().__init__("⏱ RECENT ACTIVITY", "#9C27B0") # Purple
        self.sm = special_manager
        self._init_content()
        
    def _init_content(self):
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"background: transparent; border: none;")
        self.add_widget(self.list_widget)
        self.refresh()
        
    def refresh(self):
        self.list_widget.clear()
        # Mock logic: Show recently modified situations or just list them by creation for now
        # Ideally we'd have a 'last_modified' field. 
        # For now, let's list the top 3 situations created/updated.
        sits = self.sm.get_all_situations()
        # Sort by creation as proxy
        # s['created_at'] might be string or datetime
        
        def parse_date(d):
            if isinstance(d, datetime): return d
            if isinstance(d, str):
                try: return datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
                except: pass
            return datetime.min
            
        sits.sort(key=lambda x: parse_date(x.get('created_at')), reverse=True)
        
        for s in sits[:4]:
            item = QListWidgetItem(f"📂 {s['title']}")
            item.setForeground(Qt.GlobalColor.white)
            self.list_widget.addItem(item)

# --- 5. LAUNCHPAD ---
class DashboardLaunchpadWidget(DashboardCardFrame):
    # Signals
    req_new_idea = pyqtSignal()
    req_deep_work = pyqtSignal()
    req_diary = pyqtSignal()
    req_broker = pyqtSignal()
    
    def __init__(self):
        super().__init__("🚀 LAUNCHPAD", COLORS['success'])
        self._init_content()
        
    def _init_content(self):
        grid = QGridLayout()
        grid.setSpacing(10)
        
        def mk_btn(text, slot, color):
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ opacity: 0.8; }}
            """)
            btn.clicked.connect(slot)
            return btn
            
        btn_idea = mk_btn("New Idea", self.req_new_idea.emit, COLORS['primary'])
        btn_work = mk_btn("Deep Work", self.req_deep_work.emit, COLORS['accent'])
        btn_diary = mk_btn("Harvest", self.req_diary.emit, "#9C27B0")
        btn_broker = mk_btn("Broker", self.req_broker.emit, COLORS['success'])
        
        grid.addWidget(btn_idea, 0, 0)
        grid.addWidget(btn_work, 0, 1)
        grid.addWidget(btn_diary, 1, 0)
        grid.addWidget(btn_broker, 1, 1)
        
        self.layout.addLayout(grid)
        self.add_stretch()


# --- MAIN DASHBOARD WIDGET ---
class DashboardWidget(QWidget):
    request_new_idea = pyqtSignal() # To Main Window
    request_focus = pyqtSignal()    # To Main Window (Pomodoro)
    request_diary = pyqtSignal()
    request_broker = pyqtSignal()
    
    def __init__(self):
        super().__init__()

        # Use service singletons (same instances as CompaniesView — no duplicates)
        self._company_svc  = CompanyService()
        self._special_svc  = SpecialService()

        # Keep backward-compat refs for sub-widgets that still use old API
        self.portfolio_manager = self._company_svc._mgr
        self.special_manager   = self._special_svc._mgr
        
        self.setup_ui()

        # React to price updates from AppState (no polling needed)
        AppState.get().prices_updated.connect(self._on_prices_updated)

    def _on_prices_updated(self, prices: dict):
        """Called when PriceWorker (in CompaniesView) broadcasts fresh prices.
        Dashboard updates its portfolio values without fetching anything itself."""
        try:
            # Only refresh the Radar (dates) and Continuity (pipeline) — they show live data
            self.radar.refresh()
            self.cont.refresh()
        except Exception:
            pass

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 1. Header
        header = QLabel("COMPOUNDING LAB | Command Center")
        header.setStyleSheet(f"color: {COLORS['text_main']}; font-size: 22px; font-weight: bold; letter-spacing: 1px;")
        main_layout.addWidget(header)
        
        # 2. Main Grid
        grid = QGridLayout()
        grid.setSpacing(15)
        
        # Radar (Row 0, Col 0)
        self.radar = DashboardRadarWidget(self.portfolio_manager, self.special_manager)
        grid.addWidget(self.radar, 0, 0)
        
        # Opportunity (Row 0, Col 1)
        self.opps = DashboardOpportunityWidget(self.special_manager)
        grid.addWidget(self.opps, 0, 1)
        
        # Productivity (Row 0, Col 2)
        self.prod = DashboardProductivityWidget()
        grid.addWidget(self.prod, 0, 2)
        
        # Continuity (Row 1, Col 0, Span 2)
        self.cont = DashboardContinuityWidget(self.special_manager)
        grid.addWidget(self.cont, 1, 0, 1, 2)
        
        # Launchpad (Row 1, Col 2)
        self.launch = DashboardLaunchpadWidget()
        self.launch.req_new_idea.connect(self.request_new_idea.emit)
        self.launch.req_deep_work.connect(self.request_focus.emit)
        self.launch.req_diary.connect(self.request_diary.emit)
        self.launch.req_broker.connect(self.request_broker.emit)
        
        grid.addWidget(self.launch, 1, 2)
        
        main_layout.addLayout(grid)
        
        # Push to top
        main_layout.addStretch()

    def showEvent(self, event):
        # Auto-refresh data when viewing dashboard
        self.radar.refresh()
        self.opps.refresh()
        self.prod.refresh()
        self.cont.refresh()
        super().showEvent(event)
