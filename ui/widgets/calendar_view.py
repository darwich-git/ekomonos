from datetime import date, datetime, timedelta
import calendar
from collections import defaultdict

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QSizePolicy, QDialog, 
                             QLineEdit, QDialogButtonBox, QComboBox, QDateEdit, QMessageBox,
                             QGridLayout, QFormLayout, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QSize, QThread, QRect, QPoint, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QBrush
import locale
from sqlalchemy.orm import joinedload

from core.database import CalendarEvent, Company, init_db, get_session_factory
from core.earnings_manager import EarningsManager
from ui.styles import COLORS

# Worker Thread for Sync
class SyncWorker(QThread):
    finished = pyqtSignal(dict) # Returns stats
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # Progress updates
    
    def __init__(self, manager, calendar_view):
        super().__init__()
        self.manager = manager
        self.view = calendar_view
        # self.setAutoDelete(False)  # Removed: QThread does not have setAutoDelete
        print("[WORKER] Initialized", flush=True)

    def run(self):
        """Run sync with comprehensive error handling"""
        try:
            print("[WORKER] Starting sync...", flush=True)
            
            # Call the actual sync - wrapped in try/catch
            try:
                print("[WORKER] Calling sync_all_companies()...", flush=True)
                results = self.manager.sync_all_companies()
                print(f"[WORKER] Sync completed: {results}", flush=True)
                
                # Emit success
                self.finished.emit(results)
                print("[WORKER] Success signal emitted", flush=True)
                
            except Exception as sync_error:
                # Catch errors from sync_all_companies specifically
                import traceback
                error_msg = f"Sync error: {str(sync_error)}\n\n{traceback.format_exc()}"
                print(f"[WORKER] Sync failed: {error_msg}", flush=True)
                self.error.emit(error_msg)
                
        except Exception as outer_error:
            # Catch any other unexpected errors
            import traceback
            error_msg = f"Worker thread error: {str(outer_error)}\n\n{traceback.format_exc()}"
            print(f"[WORKER] Outer error: {error_msg}", flush=True)
            self.error.emit(error_msg)

# --- Constants & Config ---
EVENT_COLORS = {
    "Earnings": "#3498DB",       # Blue
    "Presentation": "#FF9800",   # Orange
    "Dividend": "#2ECC71",       # Green
    "Investor Day": "#E0E0E0",   # White/Gray
    "Transcript": "#9B59B6",     # Purple
    "Milestone": "#E74C3C",      # Red (Synced from F5)
}

class EventFilter(QWidget):
    filter_changed = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(15)
        
        self.abbrev_map = {
            "Earnings": "Earnings",
            "Presentation": "Events",
            "Dividend": "Divs",
            "Investor Day": "Inv Day",
            "Transcript": "Trscrpt",
            "Milestone": "Sync"
        }

        self.checkboxes = {}
        for event_type, color in EVENT_COLORS.items():
            cb = QCheckBox(self.abbrev_map.get(event_type, event_type))
            cb.setChecked(True)
            cb.setStyleSheet(f"""
                QCheckBox {{ color: {COLORS['text_dim']}; font-weight: bold; spacing: 5px; }}
                QCheckBox::indicator {{ width: 12px; height: 12px; border-radius: 6px; border: 2px solid {color}; background: transparent; }}
                QCheckBox::indicator:checked {{ background: {color}; }}
                QCheckBox::indicator:hover {{ border-color: {COLORS['text_main']}; }}
            """)
            cb.stateChanged.connect(self.emit_filter)
            layout.addWidget(cb)
            self.checkboxes[event_type] = cb
            
        layout.addStretch()

    def emit_filter(self):
        active_types = [etype for etype, cb in self.checkboxes.items() if cb.isChecked()]
        self.filter_changed.emit(active_types)

class AddEventDialog(QDialog):
    def __init__(self, session_factory, initial_date=None, parent=None, preselect_ticker=None):
        super().__init__(parent)
        self.setWindowTitle("Add Calendar Event")
        self.setFixedWidth(400)
        self.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text_main']};")
        
        self.desc_edits = []
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Company
        self.company_cb = QComboBox()
        
        # Load companies from DB
        session = session_factory()
        try:
            comps = session.query(Company).order_by(Company.ticker).all()
            tickers = [c.ticker for c in comps]
            self.company_cb.addItems(tickers)
        except Exception as e:
            print(f"Error loading companies: {e}")
        finally:
            session.close()

        self.company_cb.setEditable(True) 
        if preselect_ticker:
            self.company_cb.setCurrentText(preselect_ticker)
            
        self.company_cb.setStyleSheet(f"background-color: {COLORS['surface']}; padding: 5px; border: 1px solid {COLORS['border']};")
        form.addRow("Company:", self.company_cb)
        
        # Event Type
        self.type_cb = QComboBox()
        self.type_cb.addItems(list(EVENT_COLORS.keys()))
        self.type_cb.setStyleSheet(f"background-color: {COLORS['surface']}; padding: 5px; border: 1px solid {COLORS['border']};")
        form.addRow("Type:", self.type_cb)

        # Period
        self.period_cb = QComboBox()
        self.period_cb.addItems(["", "N/A", "Q1", "Q2", "Q3", "Q4", "FY"])
        self.period_cb.setStyleSheet(f"background-color: {COLORS['surface']}; padding: 5px; border: 1px solid {COLORS['border']};")
        form.addRow("Period:", self.period_cb)
        
        # Date
        self.date_edit = QDateEdit(initial_date if initial_date else date.today())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setStyleSheet(f"background-color: {COLORS['surface']}; padding: 5px; border: 1px solid {COLORS['border']};")
        form.addRow("Date:", self.date_edit)
        
        layout.addLayout(form)
        
        # Description (Dynamic)
        layout.addWidget(QLabel("Description:"))
        
        self.desc_container = QWidget()
        self.desc_layout = QVBoxLayout(self.desc_container)
        self.desc_layout.setContentsMargins(0,0,0,0)
        self.desc_layout.setSpacing(5)
        layout.addWidget(self.desc_container)
        
        # Add first field
        self.add_desc_line()
        
        # Add Button
        btn_add_desc = QPushButton("+ Add Line")
        btn_add_desc.setStyleSheet(f"color: {COLORS['primary']}; border: none; font-weight: bold; text-align: left;")
        btn_add_desc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_desc.clicked.connect(lambda: self.add_desc_line(""))
        layout.addWidget(btn_add_desc)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_desc_line(self, text=""):
        line = QLineEdit(text)
        line.setPlaceholderText("Enter description...")
        line.setStyleSheet(f"background-color: {COLORS['surface']}; padding: 5px; border: 1px solid {COLORS['border']};")
        self.desc_layout.addWidget(line)
        self.desc_edits.append(line)

    def get_data(self):
        # Join descriptions with newline
        lines = [e.text().strip() for e in self.desc_edits if e.text().strip()]
        full_desc = "\n".join(lines)
        
        return {
            "ticker": self.company_cb.currentText(),
            "type": self.type_cb.currentText(),
            "period": self.period_cb.currentText(),
            "date": self.date_edit.date().toPyDate(),
            "desc": full_desc
        }

class DayEventItem(QLabel):
    double_clicked = pyqtSignal(object)
    
    def __init__(self, event_obj):
        # Determine Icon
        icon_char = ""
        is_special = False
        source = event_obj.get('source')
        if source == "Yahoo":
             icon_char = "⚡"
        elif source == "Manual":
             icon_char = "👤"
        elif source == "special_situation":
             icon_char = "★"

        ticker_display = event_obj.get('ticker', '???')
        
        super().__init__(None) # Initialize first

        display_text = f"{icon_char} {ticker_display}".strip()
        # Truncate text to prevent long names from stretching the day cell and breaking grid parity
        if len(display_text) > 14:
            display_text = display_text[:12] + ".."
            
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setText(display_text)
        self.event_obj = event_obj
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        col = EVENT_COLORS.get(event_obj.get('event_type'), "#888")
        self.setStyleSheet(f"""
            background-color: {col}; 
            color: white; 
            border-radius: 3px; 
            padding: 2px 4px; 
            font-size: 10px; 
            font-weight: bold;
        """)
        self.setFixedHeight(18)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setToolTip(f"{event_obj.get('event_type')} - {event_obj.get('description') or ''}")
        
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.event_obj)

class DayCell(QFrame):
    clicked = pyqtSignal(date)
    event_double_clicked = pyqtSignal(object) # Changed to object

    def __init__(self, day_date, is_current_month, events=None):
        super().__init__()
        self.day_date = day_date
        self.is_current_month = is_current_month
        self.events = events or []
        
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        
        bg_color = COLORS['surface'] if is_current_month else COLORS['background']
        border_color = COLORS['border']
        
        if day_date == date.today():
            border_color = COLORS['primary']
            self.setLineWidth(2)

        self.setStyleSheet(f"""
            DayCell {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
            DayCell:hover {{
                background-color: {COLORS['surface_light']};
            }}
        """)
        
        self.setMinimumHeight(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Layout
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(2, 2, 2, 2)
        self.layout_.setSpacing(2)
        
        # Day Number
        top_row = QHBoxLayout()
        # Spacer to push number to right or left? PaintEvent drew it top-left.
        lbl_day = QLabel(str(day_date.day))
        lbl_day.setStyleSheet(f"color: {COLORS['text_main'] if is_current_month else COLORS['text_dim']}; font-weight: bold; border: none; background: transparent;")
        lbl_day.setAlignment(Qt.AlignmentFlag.AlignLeft)
        top_row.addWidget(lbl_day)
        self.layout_.addLayout(top_row)
        
        # Events
        for i, evt in enumerate(self.events):
            if i >= 4: # Max 4 events visible
                more = QLabel(f"+{len(self.events)-4} more")
                more.setStyleSheet("color: #888; font-size: 9px; border: none; background: transparent;")
                more.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.layout_.addWidget(more)
                break
                
            item = DayEventItem(evt)
            item.double_clicked.connect(self.event_double_clicked.emit)
            self.layout_.addWidget(item)
            
        self.layout_.addStretch()

    def mousePressEvent(self, event):
        # We still want to allow selecting the day
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.day_date)
        super().mousePressEvent(event)

class CalendarGrid(QWidget):
    date_selected = pyqtSignal(date)
    event_double_clicked = pyqtSignal(object) # Changed to object

    def __init__(self, session_factory, parent=None):
        super().__init__(parent)
        self.Session = session_factory
        # self.setWindowTitle("Add Event") # Removed incorrect line
        # self.preselect_ticker = preselect_ticker # Removed incorrect line
        self.current_date = date.today()
        self.active_filters = list(EVENT_COLORS.keys())
        self.events_cache = {} 
        self.start_refresh_date = None
        self.end_refresh_date = None

        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 10, 0)

        # Header
        header_layout = QHBoxLayout()
        self.month_label = QLabel()
        self.month_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        
        btn_prev = QPushButton("<")
        btn_prev.setFixedWidth(30)
        btn_prev.clicked.connect(self.prev_month)
        
        btn_next = QPushButton(">")
        btn_next.setFixedWidth(30)
        btn_next.clicked.connect(self.next_month)
        
        btn_today = QPushButton("Today")
        btn_today.clicked.connect(self.go_today)

        header_layout.addWidget(self.month_label)
        header_layout.addStretch()
        header_layout.addWidget(btn_prev)
        header_layout.addWidget(btn_today)
        header_layout.addWidget(btn_next)
        
        self.layout_.addLayout(header_layout)

        # Days Header
        days_layout = QHBoxLayout()
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            lbl = QLabel(day)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-weight: bold;")
            days_layout.addWidget(lbl)
        self.layout_.addLayout(days_layout)
        
        # Grid
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(5)
        self.layout_.addLayout(self.grid_layout)
        
        # Refresh Data
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        # self.refresh_timer.start(300000) # 5 mins

        self.refresh_data()

    def go_today(self):
        self.set_date(date.today())

    def prev_month(self):
        first = self.current_date.replace(day=1)
        prev = first - timedelta(days=1)
        self.set_date(prev)

    def next_month(self):
        # logic to add month
        # simplistic:
        if self.current_date.month == 12:
            self.set_date(self.current_date.replace(year=self.current_date.year + 1, month=1, day=1))
        else:
            self.set_date(self.current_date.replace(month=self.current_date.month + 1, day=1))

    def set_filter(self, active_types):
        self.active_filters = active_types
        self.refresh_view()

    def on_sync_finished(self):
        print("DEBUG: Sync Finished")
        if hasattr(self, 'btn_sync'):
            self.btn_sync.setText("🔄 Sync Library")
            self.btn_sync.setEnabled(True)
        self.refresh_data()
        # self.refresh_list() # Refresh missing earnings too:
        
    def refresh_data(self):
        print("DEBUG: Grid refresh_data called.")
        from core.services.calendar_service import CalendarService
        svc = CalendarService()
        self.events_cache = svc.get_all_events()
        
        print(f"DEBUG: Grid Cache after injection has {sum(len(v) for v in self.events_cache.values())} events.")
        self.refresh_view()

    def set_date(self, new_date):
        self.current_date = new_date
        self.refresh_view()

    def refresh_view(self):
        # Clear
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget() and item.widget().metaObject().className() == "DayCell":
                widget = item.widget()
                self.grid_layout.removeWidget(widget)
                widget.deleteLater()
        
        year = self.current_date.year
        month = self.current_date.month
        self.month_label.setText(self.current_date.strftime("%B %Y"))

        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdatescalendar(year, month)
        
        # Save range for timeline
        self.start_refresh_date = month_days[0][0]
        self.end_refresh_date = month_days[-1][-1]

        row = 1
        for week in month_days:
            col = 0
            for day in week:
                is_current = (day.month == month)
                day_events = self.events_cache.get(day, [])
                filtered_events = [e for e in day_events if e.get('event_type') in self.active_filters]
                
                cell = DayCell(day, is_current, filtered_events)
                cell.clicked.connect(lambda d=day: self.date_selected.emit(d))
                cell.event_double_clicked.connect(self.event_double_clicked.emit)
                
                self.grid_layout.addWidget(cell, row, col)
                col += 1
            row += 1

class AgendaCard(QFrame):
    clicked = pyqtSignal(object)
    double_clicked = pyqtSignal(object)
    delete_requested = pyqtSignal(int) # Event ID
    edit_requested = pyqtSignal(object)

    def __init__(self, event_obj):
        super().__init__()
        self.event_obj = event_obj
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
            QFrame:hover {{
                border-color: {COLORS['primary']};
                background-color: {COLORS['surface_light']};
            }}
        """)
        
        card_layout = QHBoxLayout(self)
        card_layout.setContentsMargins(10, 10, 10, 10)
        
        # Make child widgets ignore mouse events so hover style (border) works on parent QFrame
        # OR set their background to transparent. 
        # The issue is usually that children don't let mouse event pass through or have own opaque bg.
        # But QFrame:hover relies on the frame receiving the event.
        # Setting Attribute to transparent for children
        
        indicator = QLabel()
        indicator.setFixedSize(4, 30)
        col = EVENT_COLORS.get(event_obj.get('event_type'), 'white')
        indicator.setStyleSheet(f"background-color: {col}; border-radius: 2px;")
        card_layout.addWidget(indicator)
        
        content = QVBoxLayout()
        top = QHBoxLayout()
        
        # Ticker & Icon
        icon_char = ""
        source = event_obj.get('source')
        if source == "Yahoo":
             icon_char = "⚡"
        elif source == "Manual":
             icon_char = "👤"
        elif source == "special_situation":
             icon_char = "★"
                 
        ticker_display = event_obj.get('ticker', '???')
        t = QLabel(f"{icon_char} {ticker_display}".strip())
        t.setWordWrap(True)
        t.setStyleSheet("font-weight: bold; background: transparent;") # Transparent bg
        t.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        top.addWidget(t)
        top.addStretch()
        l_type = QLabel(event_obj.get('event_type'))
        l_type.setStyleSheet("background: transparent;")
        l_type.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        top.addWidget(l_type)
        content.addLayout(top)
        
        # 1. Estimates FIRST
        if event_obj.get('est_eps') is not None:
             lbl_est = QLabel(f"Est EPS: ${event_obj.get('est_eps'):.2f}")
             lbl_est.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px; font-weight: bold; background: transparent;")
             lbl_est.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
             content.addWidget(lbl_est)

        # 2. Descriptions BELOW
        desc_text = event_obj.get('description') or ""
        lines = desc_text.split('\n')
        for line in lines:
            if not line.strip(): continue
            lbl = QLabel(line.strip())
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px; background: transparent;")
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            content.addWidget(lbl)
        
        card_layout.addLayout(content)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.event_obj)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.event_obj)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        
        edit_action = menu.addAction("Edit Event")
        delete_action = menu.addAction("Delete Event")
        
        action = menu.exec(event.globalPos())
        
        if action == delete_action:
            self.delete_requested.emit(self.event_obj.get('id', -1))
        elif action == edit_action:
            self.edit_requested.emit(self.event_obj)

class AgendaView(QWidget):
    event_clicked = pyqtSignal(object)
    event_double_clicked = pyqtSignal(object)
    delete_event_requested = pyqtSignal(int)
    edit_event_requested = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        
        header = QLabel("Upcoming")
        header.setStyleSheet(f"font-weight: bold; border-bottom: 2px solid {COLORS['border']}; padding-bottom: 5px;")
        layout.addWidget(header)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.container = QWidget()
        self.box = QVBoxLayout(self.container)
        self.box.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def load_events(self, events):
        while self.box.count():
            child = self.box.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        if not events:
            self.box.addWidget(QLabel("No events."))
            return

        # Safe sort handling both date and datetime
        sorted_events = sorted(events, key=lambda x: x.get('event_date') if isinstance(x.get('event_date'), datetime) else datetime.combine(x.get('event_date'), datetime.min.time()))
        curr_date = None
        
        for e in sorted_events:
            evt_dt = e.get('event_date')
            d = evt_dt.date() if isinstance(evt_dt, datetime) else evt_dt
            if d != curr_date:
                lbl = QLabel(d.strftime("%a, %b %d"))
                lbl.setStyleSheet(f"color: {COLORS['primary']}; font-weight: bold; margin-top: 10px;")
                self.box.addWidget(lbl)
                curr_date = d
            
            card = AgendaCard(e)
            card.clicked.connect(self.event_clicked.emit)
            card.double_clicked.connect(self.event_double_clicked.emit)
            card.delete_requested.connect(self.delete_event_requested.emit)
            card.edit_requested.connect(self.edit_event_requested.emit) # Connect new signal
            self.box.addWidget(card)

class MissingEarningsWidget(QWidget):
    date_set = pyqtSignal()

    def __init__(self, portfolio_manager, session_factory):
        super().__init__()
        self.portfolio_manager = portfolio_manager
        self.Session = session_factory
        
        # Auto-Migration for 'status' column if needed
        # We do this here as a safety measure since this view relies on it
        session = self.Session()
        try:
             # Check if column exists
             inspector = session.connection().dialect.get_columns(session.connection(), "companies")
             cols = [c["name"] for c in inspector]
             
             if "status" not in cols:
                  from sqlalchemy import text
                  session.execute(text("ALTER TABLE companies ADD COLUMN status TEXT DEFAULT 'To Research'"))
                  print("Migrated 'status' column to companies table.")
                  
             if "ignore_earnings" not in cols:
                  from sqlalchemy import text
                  session.execute(text("ALTER TABLE companies ADD COLUMN ignore_earnings BOOLEAN DEFAULT 0"))
                  print("Migrated 'ignore_earnings' column.")
                  
             session.commit()
        except Exception as e:
             session.rollback()
             print(f"Migration check failed: {e}")
        finally:
             session.close()

        layout = QVBoxLayout(self)
        
        header = QLabel("⚠️ Empresas sin fecha de resultados futura")
        header.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['danger']}; margin-bottom: 10px;")
        layout.addWidget(header)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.container = QWidget()
        self.box = QVBoxLayout(self.container)
        self.box.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.box.setSpacing(10)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def refresh_list(self):
        # Clear existing
        while self.box.count():
            child = self.box.takeAt(0)
            if child.widget(): child.widget().deleteLater()

        from core.services.calendar_service import CalendarService
        svc = CalendarService()
        missing_companies = svc.get_missing_earnings_companies()
        
        if not missing_companies:
            lbl = QLabel("✅ ¡Todo al día! No hay empresas pendientes.")
            lbl.setStyleSheet(f"color: {COLORS['success']}; font-size: 16px; margin-top: 20px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.box.addWidget(lbl)
            return

        for comp_dict in missing_companies:
            self.add_company_card(comp_dict)

    def add_company_card(self, company):
        # Create clickable frame
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = lambda event, c=company: self.open_set_date_dialog(c)
        
        # Context Menu
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        card.customContextMenuRequested.connect(lambda pos, c=company: self.open_context_menu(pos, c, card))
        
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {COLORS['primary']};
                background-color: {COLORS['surface_light']};
            }}
        """)
        card.setFixedHeight(60)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Ticker
        lbl_ticker = QLabel(company.get('ticker', ''))
        lbl_ticker.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['primary']}; border: none; background: transparent;")
        
        # Name
        lbl_name = QLabel(company.get('name', ''))
        lbl_name.setStyleSheet(f"font-size: 14px; color: {COLORS['text_main']}; border: none; background: transparent;")
        
        # Warning Icon
        lbl_icon = QLabel("⚠️")
        lbl_icon.setStyleSheet("font-size: 18px; border: none; background: transparent;")
        
        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_ticker)
        layout.addWidget(lbl_name)
        layout.addStretch()
        
        self.box.addWidget(card)

    def open_context_menu(self, pos, company, card_widget):
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        menu = QMenu(card_widget)
        action_ignore = QAction("Ignore / Hide from List", card_widget)
        action_ignore.triggered.connect(lambda: self.ignore_company(company))
        menu.addAction(action_ignore)
        
        menu.exec(card_widget.mapToGlobal(pos))

    def ignore_company(self, company):
        # 1. Update DB
        session = self.Session()
        try:
            c = session.query(Company).filter_by(ticker=company.get('ticker')).first()
            if c:
                c.ignore_earnings = True 
                session.commit()
                # print(f"Ignored company: {company.ticker}")
                
            # 2. Refresh List
            self.refresh_list()
            
        except Exception as e:
            print(f"Error ignoring company: {e}")
            session.rollback()
        finally:
            session.close()
        


    def open_set_date_dialog(self, company):
        # Use existing AddEventDialog but prefill ticker and Type=Earnings
        # Passing a dict of {ticker: ticker} to mimic portfolio expected input?
        # Actually AddEventDialog takes a dict of companies.
        
        # Hacky: create a dialog just for this company
        from ui.widgets.calendar_view import AddEventDialog # Local import to avoid circular
        
        # Minimal mock of companies dict
        companies = {company.get('ticker'): company} 
        
        # We need to find the parent CalendarWidget to execute valid save
        # Or we implement save logic here? Better to delegate to parent or reuse.
        # But this widget is inside CalendarWidget.
        
        parent = self.parent()
        # Traverse up to find CalendarWidget
        while parent and not isinstance(parent, CalendarWidget):
            parent = parent.parent()
            
        if parent:
            # Updated to match new signature: session_factory, initial_date, parent, preselect_ticker
            dlg = AddEventDialog(self.Session, parent=parent, preselect_ticker=company.get('ticker'))
            dlg.type_cb.setCurrentText("Earnings")
            dlg.company_cb.setEnabled(False) # Lock company
            
            if dlg.exec():
                print(f"[MISSING] Dialog accepted for {company.get('ticker')}", flush=True)
                data = dlg.get_data()
                print(f"[MISSING] Event data: {data}", flush=True)
                parent.save_event(data)
                print("[MISSING] Event saved, refreshing...", flush=True)
                # Refresh calendar views
                parent.grid.refresh_data()
                parent.update_agenda_view()
                # Refresh this missing list
                print("[MISSING] Calling refresh_list()...", flush=True)
                self.refresh_list()
                print("[MISSING] Refresh complete!", flush=True)

class TimelineWidget(QFrame):
    """Improved 12-month timeline. Stacks events per month, marks today, click navigates calendar."""
    date_clicked = pyqtSignal(date)
    MONTHS_AHEAD = 13

    def __init__(self, events_cache):
        super().__init__()
        self.events_cache = events_cache
        self.setMinimumHeight(180)
        self.setMaximumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; border-top: 1px solid {COLORS['border']};")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.click_areas = []

    def update_events(self, cache):
        self.events_cache = cache
        self.update()

    def set_range(self, start_date, end_date):
        # API compatibility – we always derive range from today
        self.update()

    def paintEvent(self, paint_event):
        import calendar as _cal
        from collections import defaultdict
        from PyQt6.QtGui import QPainter, QPen, QBrush, QFont, QColor, QFontMetrics, QPolygon
        from PyQt6.QtCore import QRect, QPoint

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        H = self.height()

        PADDING_L  = 8
        PADDING_R  = 8
        usable_w   = W - PADDING_L - PADDING_R
        AXIS_Y     = H - 36          # horizontal time axis
        MONTH_LBL_Y = AXIS_Y + 20   # month name below axis
        EVENT_TOP  = 6               # topmost event row
        EVENT_ZONE_H = AXIS_Y - EVENT_TOP - 4
        ROW_H  = 15
        ROW_GAP = 2
        MAX_ROWS = max(1, int(EVENT_ZONE_H / (ROW_H + ROW_GAP)))

        # ── Background ─────────────────────────────────────────────────────
        painter.fillRect(self.rect(), QColor(COLORS.get('surface', '#1e1e1e')))

        # ── Date range: 13 months from today ──────────────────────────────
        today = date.today()
        start = date(today.year, today.month, 1)
        e_mo  = start.month + self.MONTHS_AHEAD - 1
        e_yr  = start.year + (e_mo - 1) // 12
        e_mo  = ((e_mo - 1) % 12) + 1
        end   = date(e_yr, e_mo, _cal.monthrange(e_yr, e_mo)[1])
        total_days  = max((end - start).days, 1)
        px_per_day  = usable_w / total_days

        def x_for(d):
            return PADDING_L + int(max(0, (d - start).days) * px_per_day)

        # ── Axis line ──────────────────────────────────────────────────────
        painter.setPen(QPen(QColor(COLORS.get('border', '#444')), 2))
        painter.drawLine(PADDING_L, AXIS_Y, W - PADDING_R, AXIS_Y)

        # ── Month separators + labels ──────────────────────────────────────
        month_font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(month_font)
        fm_mo = QFontMetrics(month_font)

        self.click_areas = []
        cur = start
        while cur <= end:
            xc = x_for(cur)
            # ── separator tick ──
            painter.setPen(QPen(QColor(COLORS.get('border', '#555')), 1))
            painter.drawLine(xc, AXIS_Y - 5, xc, AXIS_Y + 5)

            # next month start x
            nm = cur.month + 1; ny = cur.year + (1 if nm > 12 else 0); nm = nm if nm <= 12 else 1
            nx = x_for(date(ny, nm, 1))

            # label
            lbl  = cur.strftime("%b '%y") if cur.month == 1 else cur.strftime("%b")
            lw   = fm_mo.horizontalAdvance(lbl)
            lx   = xc + (nx - xc - lw) // 2
            painter.setPen(QColor(COLORS.get('text_dim', '#888')))
            painter.drawText(lx, MONTH_LBL_Y, lbl)

            # click zone for entire month column
            self.click_areas.append((QRect(xc, 0, nx - xc, H), cur))

            cur = date(ny, nm, 1)

        # ── Group events by month ──────────────────────────────────────────
        month_events = defaultdict(list)
        for d, evts in self.events_cache.items():
            if start <= d <= end:
                for e in evts:
                    month_events[(d.year, d.month)].append((d, e))

        # ── Draw events (stacked badges per month) ─────────────────────────
        evt_font = QFont("Arial", 7, QFont.Weight.Bold)
        painter.setFont(evt_font)
        fm_evt = QFontMetrics(evt_font)

        for (yr, mo), pairs in month_events.items():
            mo_start  = date(yr, mo, 1)
            mo_end    = date(yr, mo, _cal.monthrange(yr, mo)[1])
            mx_s = x_for(mo_start)
            mx_e = x_for(min(mo_end, end))
            center_x = mx_s + (mx_e - mx_s) // 2

            pairs.sort(key=lambda p: p[0])

            for row_i, (d, e) in enumerate(pairs):
                if row_i >= MAX_ROWS:
                    painter.setPen(QColor(COLORS.get('text_dim', '#888')))
                    oy = EVENT_TOP + MAX_ROWS * (ROW_H + ROW_GAP) + ROW_H
                    painter.drawText(center_x - 3, min(oy, AXIS_Y - 2), "…")
                    break

                col   = QColor(EVENT_COLORS.get(e.get('event_type'), '#aaaaaa'))
                row_y = EVENT_TOP + row_i * (ROW_H + ROW_GAP)

                ticker = e.get('ticker', '?')
                lw_b   = fm_evt.horizontalAdvance(ticker) + 8
                bx     = max(PADDING_L, min(center_x - lw_b // 2, W - PADDING_R - lw_b))
                badge  = QRect(bx, row_y, lw_b, ROW_H)

                # Badge fill
                bg = QColor(col); bg.setAlpha(210)
                painter.setBrush(QBrush(bg))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(badge, 3, 3)

                # Badge text
                painter.setPen(QColor('#000000'))
                painter.drawText(badge.adjusted(2, 0, -2, 0), Qt.AlignmentFlag.AlignCenter, ticker)

                # Connector line badge → axis
                dot_x = x_for(d)
                line_x = min(max(dot_x, bx + 2), bx + lw_b - 2)
                cc = QColor(col); cc.setAlpha(100)
                painter.setPen(QPen(cc, 1, Qt.PenStyle.DotLine))
                painter.drawLine(line_x, row_y + ROW_H, line_x, AXIS_Y)

                # Dot on axis
                painter.setBrush(QBrush(col))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPoint(dot_x, AXIS_Y), 4, 4)

                # Badge is a clickable area (prepend so it takes priority)
                self.click_areas.insert(0, (badge, d))

        # ── TODAY marker ───────────────────────────────────────────────────
        if start <= today <= end:
            tx = x_for(today)
            tc = QColor(COLORS.get('primary', '#FF9800'))

            painter.setPen(QPen(tc, 2))
            painter.drawLine(tx, EVENT_TOP, tx, AXIS_Y + 8)

            # Diamond
            diamond = [QPoint(tx, AXIS_Y - 7),
                       QPoint(tx + 4, AXIS_Y),
                       QPoint(tx, AXIS_Y + 7),
                       QPoint(tx - 4, AXIS_Y)]
            painter.setBrush(QBrush(tc))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(QPolygon(diamond))

            # "HOY" label
            tf = QFont("Arial", 7, QFont.Weight.Bold)
            painter.setFont(tf)
            fm_t = QFontMetrics(tf)
            lbl = "HOY"
            tlw = fm_t.horizontalAdvance(lbl)
            lx  = tx - tlw // 2
            ly  = AXIS_Y + 26
            painter.setPen(QColor('#000')); [painter.drawText(lx+dx, ly+dy, lbl) for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]]
            painter.setPen(tc)
            painter.drawText(lx, ly, lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            for rect, d in self.click_areas:
                if rect.contains(pos):
                    # Navigate to the 1st of the clicked month
                    self.date_clicked.emit(date(d.year, d.month, 1))
                    return
        super().mousePressEvent(event)



class CalendarWidget(QWidget):
    # Signals
    date_selected = pyqtSignal(date)
    event_clicked = pyqtSignal(object) # Changed to object
    event_double_clicked = pyqtSignal(object) # Changed to object
    company_selected = pyqtSignal(str) # Ticker
    special_situation_selected = pyqtSignal(str) # Situation ID
    
    def __init__(self, session_factory, portfolio_manager):
        super().__init__()
        self.Session = session_factory
        self.portfolio_manager = portfolio_manager
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 1. Top Bar: Title & Add Button
        top_bar = QHBoxLayout()
        
        title = QLabel("Calendario")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['primary']};")
        top_bar.addWidget(title)
        
        top_bar.addStretch()
        
        self.btn_action = QPushButton("⚠️ Faltan Fechas")
        self.btn_action.setCheckable(True)
        self.btn_action.setStyleSheet(f"background-color: transparent; color: {COLORS['text_dim']}; border: 1px solid {COLORS['border']}; font-weight: bold; padding: 5px 15px;")
        self.btn_action.clicked.connect(self.on_toggle_action_required)
        top_bar.addWidget(self.btn_action)

        self.btn_sync = QPushButton("🔄 Sync") # Restore sync button ref for methods that use it
        self.btn_sync.setVisible(False) # Hidden by default if we auto-sync
        top_bar.addWidget(self.btn_sync)

        self.btn_add = QPushButton("+ Add Event")
        self.btn_add.setStyleSheet(f"background-color: {COLORS['surface_light']}; color: {COLORS['success']}; border: 1px solid {COLORS['success']}; font-weight: bold; padding: 5px 15px;")
        self.btn_add.clicked.connect(self.on_add_event)
        top_bar.addWidget(self.btn_add)
        
        main_layout.addLayout(top_bar)
        
        # 2. Main Content Split
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0,0,0,0)
        
        # Grid Split (Normal View)
        self.normal_view = QWidget()
        split_layout = QHBoxLayout(self.normal_view)
        split_layout.setContentsMargins(0,0,0,0)
        
        self.grid = CalendarGrid(session_factory)
        self.grid.date_selected.connect(self.on_grid_date_selected) # Fixed connection
        self.grid.event_double_clicked.connect(self.on_event_double_clicked)
        
        container_grid = QWidget()
        l_grid = QVBoxLayout(container_grid)
        l_grid.setContentsMargins(0,0,0,0)
        l_grid.addWidget(self.grid)
        split_layout.addWidget(container_grid, 7)
        
        self.agenda = AgendaView()
        self.agenda.event_clicked.connect(self.on_event_clicked)
        self.agenda.delete_event_requested.connect(self.delete_event)
        self.agenda.event_double_clicked.connect(self.on_event_double_clicked)   
        self.agenda.edit_event_requested.connect(self.edit_event)
        split_layout.addWidget(self.agenda, 3)
        
        self.content_layout.addWidget(self.normal_view)
        
        # Missing Earnings (Initially Hidden)
        self.missing_earnings_view = MissingEarningsWidget(self.portfolio_manager, self.Session)
        self.missing_earnings_view.setVisible(False)
        self.missing_earnings_view.date_set.connect(self.on_manual_date_set)
        self.content_layout.addWidget(self.missing_earnings_view)
        
        main_layout.addWidget(self.content_container, stretch=1)
        
        # 3. Timeline
        self.timeline = TimelineWidget(self.grid.events_cache)
        self.timeline.date_clicked.connect(self.on_timeline_date_clicked)
        main_layout.addWidget(self.timeline)
        
        # 4. Filters (Legend) - Bottom
        self.filters = EventFilter()
        self.filters.filter_changed.connect(self.on_filter_changed)
        main_layout.addWidget(self.filters)
        
        # Auto-Sync Library on Startup
        QTimer.singleShot(1000, self.sync_library_to_db)
        
        # Auto-Sync Earnings on Startup
        QTimer.singleShot(3000, self.auto_sync_earnings_subprocess)

        self.update_agenda_view()
        
    def showEvent(self, event):
        super().showEvent(event)
        # Automatic refresh when entering the page
        try:
            self.grid.refresh_data()
            self.update_agenda_view()
        except Exception as e:
            print(f"Error refreshing calendar on show: {e}")
        
    def sync_library_to_db(self):
        """Syncs folders from library to Calendar DB (non-destructive check)."""
        if not self.portfolio_manager: return
        
        # print("Scanning Library for new companies...") # Optional log
        session = self.Session()
        try:
            library_tickers = self.portfolio_manager.companies.keys()
            existing_companies = {c.ticker for c in session.query(Company).all()}
            
            added_count = 0
            for ticker in library_tickers:
                if ticker not in existing_companies:
                    print(f"Importing {ticker} from Library to DB...")
                    new_comp = Company(ticker=ticker, name=ticker)
                    session.add(new_comp)
                    existing_companies.add(ticker) 
                    added_count += 1
            
            if added_count > 0:
                session.commit()
                print(f"Imported {added_count} new companies to Calendar DB.")
            
        except Exception as e:
            print(f"Error syncing library to DB: {e}")
        finally:
            session.close()

    def on_manual_date_set(self):
        # Refresh logic after setting a date manually from the missing list
        print("Date set manually, refreshing...")
        self.grid.refresh_data()
        self.update_agenda_view()
        self.missing_earnings_view.refresh_list() # Remove the item from list

    def open_add_event_dialog(self, date=None, preselect_ticker=None):
        # Pass session factory and parent
        dlg = AddEventDialog(self.Session, initial_date=date, parent=self, preselect_ticker=preselect_ticker)
        if dlg.exec():
            print("[ADD EVENT] Dialog accepted", flush=True)
            data = dlg.get_data()
            print(f"[ADD EVENT] Event data: {data}", flush=True)
            # CRITICAL: Actually save the event!
            self.save_event(data)
            print("[ADD EVENT] Event saved, refreshing views...", flush=True)
            # Refresh calendar after adding
            self.grid.refresh_data()
            self.update_agenda_view()
            if self.missing_earnings_view.isVisible():
                self.missing_earnings_view.refresh_list()
            print("[ADD EVENT] Refresh complete", flush=True)

    def on_toggle_action_required(self):
        is_active = self.btn_action.isChecked()
        if is_active:
            # Hide Calendar & Agenda, Show List
            self.normal_view.setVisible(False) # Hides grid/agenda
            self.timeline.setVisible(False)
            self.filters.setVisible(False)
            self.missing_earnings_view.setVisible(True)
            self.missing_earnings_view.refresh_list()
            self.btn_action.setStyleSheet(f"background-color: {COLORS['danger']}; color: white; font-weight: bold; border: 1px solid {COLORS['danger']}; padding: 5px 15px;")
        else:
            # Show Normal
            self.normal_view.setVisible(True)
            self.timeline.setVisible(True)
            self.filters.setVisible(True)
            self.missing_earnings_view.setVisible(False)
            self.btn_action.setStyleSheet(f"background-color: transparent; color: {COLORS['text_dim']}; border: 1px solid {COLORS['border']}; font-weight: bold; padding: 5px 15px;")

    def auto_sync(self):
        print("DEBUG: Starting Auto-Sync...")
        if hasattr(self, 'sync_worker') and not self.sync_worker.isRunning():
            self.sync_worker.start()

    def auto_sync_earnings_subprocess(self):
        """Run earnings sync in subprocess with results popup"""
        import subprocess
        import os
        
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   'sync_calendar_earnings.py')
        self.results_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'sync_results.json')
        
        # Delete old results
        if os.path.exists(self.results_path):
            try:
                os.remove(self.results_path)
            except:
                pass
        
        if not os.path.exists(script_path):
            print(f"[AUTO-SYNC] Script not found: {script_path}", flush=True)
            return
        
        try:
            print("[AUTO-SYNC] Starting sync...", flush=True)
            
            subprocess.Popen(
                ['python', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            print("[AUTO-SYNC] Started (will show popup when done)", flush=True)
            
            # Check for results every 5 seconds
            self.sync_check_timer = QTimer()
            self.sync_check_timer.timeout.connect(self.check_sync_results)
            self.sync_check_timer.start(5000)
            
        except Exception as e:
            print(f"[AUTO-SYNC] Failed: {e}", flush=True)
    
    def check_sync_results(self):
        """Check if sync completed and show results popup"""
        import os
        import json
        
        if os.path.exists(self.results_path):
            try:
                with open(self.results_path, 'r') as f:
                    results = json.load(f)
                
                self.sync_check_timer.stop()
                
                # Refresh all views
                self.grid.refresh_data()
                self.update_agenda_view()
                if self.btn_action.isChecked():
                    self.missing_earnings_view.refresh_list()
                
                # Show popup
                from PyQt6.QtWidgets import QMessageBox
                if 'error' in results:
                    QMessageBox.warning(self, "Sync Error", 
                        f"Auto-sync error:\n\n{results['error']}")
                else:
                    msg = f"✓ Actualizadas: {results['updated']} empresas\n"
                    if results['failed'] > 0:
                        msg += f"✗ Fallidas: {results['failed']} empresas\n\n"
                        msg += "Algunas fallaron (delisted, non-US tickers)"
                    else:
                        msg += "\n¡Todas actualizadas correctamente!"
                    
                    QMessageBox.information(self, "Sync Completo", msg)
                
                # Clean up
                try:
                    os.remove(self.results_path)
                except:
                    pass
                    
            except Exception as e:
                print(f"[AUTO-SYNC] Error reading results: {e}", flush=True)
                self.sync_check_timer.stop()

    def on_sync_earnings(self):
        """PERMANENTLY DISABLED - Segfault persists even with updated dependencies"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Sync Unavailable", 
            "Automatic sync is disabled due to library conflicts.\n\n"
            "Earnings data can be viewed but not auto-updated.\n\n"
            "To update manually, edit companies individually."
        )
        print("[SYNC] Disabled permanently - causes segfault", flush=True)

    def on_sync_finished(self, results):
        print(f"Sync complete: {results}")
        self.btn_sync.setText("🔄 Sync")
        self.btn_sync.setEnabled(True)
        self.btn_action.setEnabled(True)

        # Refresh all views
        self.grid.refresh_data()
        self.update_agenda_view()
        if self.btn_action.isChecked():
            self.missing_earnings_view.refresh_list()
            
        QMessageBox.information(self, "Sync Complete", f"Updated: {results.get('updated')}\nFailed: {results.get('failed')}")

    def on_sync_error(self, err_msg):
        print(f"Sync error: {err_msg}")
        self.btn_sync.setText("🔄 Sync")
        self.btn_sync.setEnabled(True)
        self.btn_action.setEnabled(True)
        QMessageBox.warning(self, "Sync Error", f"An error occurred during sync:\n{err_msg}")
        
        # Refresh all views
        self.grid.refresh_data()
        self.update_agenda_view()
        if self.btn_action.isChecked():
            self.missing_earnings_view.refresh_list()

    def on_timeline_date_clicked(self, date_obj):
        # Jump grid to this date
        self.grid.set_date(date_obj)
        # Also select it?
        self.grid.date_selected.emit(date_obj)

    def on_filter_changed(self, active_types):
        self.grid.set_filter(active_types)
        self.update_agenda_view(active_types=active_types)
        # Also could filter timeline?
        # For now timeline shows all events to be comprehensive

    def on_grid_date_selected(self, date_obj):
        self.update_agenda_from_date(date_obj)

    def update_agenda_view(self, active_types=None):
        self.update_agenda_from_date(date.today(), active_types)
        # Update timeline events
        self.timeline.update_events(self.grid.events_cache)
        # Update range: Show Today to +6 months to satisfy "ver eventos mas lejanos"
        today = date.today()
        self.timeline.set_range(today, today + timedelta(days=180))

    def update_agenda_from_date(self, start_date, active_types=None):
        if active_types is None:
            active_types = self.grid.active_filters
        
        # Increase range to see NA9 (April is > 60 days from Jan)
        end_date = start_date + timedelta(days=180)
        matches = []
        for d, events in self.grid.events_cache.items():
            if start_date <= d <= end_date:
                for e in events:
                    if e.get('event_type') in active_types:
                        matches.append(e)
        self.agenda.load_events(matches)

    def on_add_event(self):
        # Pass session factory to dialog
        print("[BTN] Add Event clicked - opening dialog", flush=True)
        dlg = AddEventDialog(self.Session, parent=self)
        print("[BTN] Dialog created, waiting for exec()", flush=True)
        if dlg.exec():
            print("[BTN] Dialog accepted!", flush=True)
            data = dlg.get_data()
            print(f"[BTN] Got data: {data}", flush=True)
            self.save_event(data)
            print("[BTN] save_event called", flush=True)
        else:
            print("[BTN] Dialog cancelled", flush=True)


    def save_event(self, data):
        print(f"DEBUG: Saving event {data}")
        from core.services.calendar_service import CalendarService
        svc = CalendarService()
        success = svc.add_event(data)
        
        if success:
            print("DEBUG: Event saved to DB successfully.")
            # Refresh
            self.grid.refresh_data()
            self.update_agenda_view()
            self.timeline.update_events(self.grid.events_cache)
            self.timeline.repaint() 
        else:
            print("Error saving event using CalendarService.")

    def delete_event(self, event_id):
        print(f"DEBUG: Deleting event ID {event_id}")
        from core.services.calendar_service import CalendarService
        svc = CalendarService()
        success = svc.delete_event(event_id)
        if success:
            print("DEBUG: Event deleted.")
            # Refresh UI
            self.grid.refresh_data()
            self.update_agenda_view()
            self.timeline.update_events(self.grid.events_cache)
            self.timeline.repaint()
        else:
            print("DEBUG: Event not found or could not be deleted.")

    def on_event_clicked(self, event_obj):
        # Forward single clicks to double click handler logic for consistency/simplicity if desired
        # Or keep separate. User mentioned "click" closes program.
        self.on_event_double_clicked(event_obj)
        
    def on_event_double_clicked(self, event_obj):
        print(f"[CALENDAR] Double-click on: {event_obj.get('description', 'None')}")
        try:
            # 1. Special Situation Navigation
            # Robustly check source
            source = event_obj.get('source')
            if source in ["special_situation", "Special"]:
                print(f"[NAV] Special Situation Source detected: {source}")
                
                # Use stored situation_id if available (Robust)
                sit_id = event_obj.get('id')
                if str(sit_id).startswith('virtual_'):
                     sit_id = sit_id.split('_')[1]
                     print(f"[NAV] Using stored ID: {sit_id}")
                     self.special_situation_selected.emit(str(sit_id))
                     return

                # Fallback: Logic to find Situation ID from Ticker (Legacy/Backup)
                ticker = event_obj.get('ticker')
                print(f"[NAV] Stored ID missing, searching by ticker: {ticker}")
                
                from core.services.special_service import SpecialService
                svc = SpecialService()
                sits = svc.get_all()
                
                target_sit = None
                for s in sits:
                    t = s.get('tickers_dict', {}).get('target')
                    if t == ticker:
                        target_sit = s
                        break
                    t_yahoo = s.get('specific_data', {}).get('yahoo_tickers', {}).get('target')
                    if t_yahoo == ticker:
                        target_sit = s
                        break

                if target_sit:
                    print(f"[NAV] Found situation {target_sit['id']}. Emitting signal.")
                    self.special_situation_selected.emit(target_sit['id'])
                    return
                else:
                    print(f"[NAV] ERROR: No situation found for ticker {ticker}")
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Navigation Error", f"Could not find Special Situation linked to {ticker}")
                    return
            else:
                # Standard Company Event -> Go to Library
                ticker = event_obj.get('ticker')
                if ticker:
                    print(f"[NAV] Standard Event. Emitting signal for ticker: {ticker}")
                    self.company_selected.emit(ticker)
                else:
                    print("[NAV] ERROR: Event has no company object.")
        except Exception as e:
            print(f"Error handling event click: {e}")
            import traceback
            traceback.print_exc()

    def edit_event(self, event_obj):
        print(f"Editing event {event_obj.get('id')}")
        from pprint import pprint
        print("DEBUG event_obj:", event_obj)
        # Cannot edit virtual events
        if str(event_obj.get('id', '')).startswith('virtual_'):
            return
            
        ticker = event_obj.get('ticker')
        
        dlg = AddEventDialog(self.Session, parent=self)
        
        # Prefill
        dlg.setWindowTitle("Edit Event")
        dlg.company_cb.setCurrentText(ticker)
        dlg.company_cb.setEnabled(False) 
        
        # Prefill description lines
        desc_lines = (event_obj.get('description') or "").split('\n')
        while dlg.desc_layout.count():
             child = dlg.desc_layout.takeAt(0)
             if child.widget(): child.widget().deleteLater()
        dlg.desc_edits.clear()
        
        if not desc_lines:
             dlg.add_desc_line()
        else:
             for line in desc_lines:
                 dlg.add_desc_line(line)
        
        # Handle Date
        evt_dt = event_obj.get('event_date')
        d = evt_dt.date() if isinstance(evt_dt, datetime) else evt_dt
        dlg.date_edit.setDate(d)
        
        if dlg.exec():
            data = dlg.get_data()
            
            from core.services.calendar_service import CalendarService
            svc = CalendarService()
            success = svc.edit_event(event_obj.get('id'), data)
            
            if success:
                print("Event updated.")
                self.grid.refresh_data()
                self.update_agenda_view()
                self.timeline.update_events(self.grid.events_cache)
            else:
                print("Event not found for update.")
