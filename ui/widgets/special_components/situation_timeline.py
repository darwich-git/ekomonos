import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QMenu, QInputDialog, QMessageBox, QHBoxLayout,
    QPushButton, QDialog, QFormLayout, QDateEdit, QLineEdit, QCheckBox, QDialogButtonBox, QStyle,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QAbstractSpinBox
)
from PyQt6.QtCore import Qt, QPoint, QDate, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QAction
from ui.styles import COLORS
from core.database import init_db, get_session_factory, CalendarEvent, Company
from sqlalchemy import and_
import re # Needed for regex

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

class MilestoneDialog(QDialog):
    def __init__(self, parent=None, name="", date_str="", synced=False):
        super().__init__(parent)
        self.setWindowTitle("Milestone")
        self.resize(300, 150)
        self.setStyleSheet(f"QDialog {{ background-color: {COLORS['surface']}; color: {COLORS['text_main']}; font-family: 'Segoe UI', sans-serif; }}")
        
        layout = QFormLayout(self)
        
        self.inp_name = QLineEdit(name)
        
        self.inp_date = SmartDateEdit()
        self.inp_date.set_from_db(date_str or datetime.date.today().strftime("%Y-%m-%d"))
        self.inp_date.setStyleSheet(f"background-color: {COLORS['surface_light']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; padding: 5px; border-radius: 4px;")
            
        self.inp_sync = QCheckBox("Sync to Calendar (F3)")
        self.inp_sync.setChecked(synced)
        
        layout.addRow("Name:", self.inp_name)
        layout.addRow("Date:", self.inp_date)
        layout.addRow("", self.inp_sync)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)
        
    def get_data(self):
        return {
            'name': self.inp_name.text(),
            'date': self.inp_date.text_for_db(),
            'synced': self.inp_sync.isChecked()
        }

class SituationTimelineWidget(QWidget):
    def __init__(self, situation_data, parent=None):
        super().__init__(parent)
        self.situation_data = situation_data
        self.milestones = [] # Init empty to prevent AttributeError if accessed early
        self.setMinimumHeight(500) # Increased height for table
        self.setStyleSheet(f"QWidget {{ background-color: {COLORS['surface']}; font-family: 'Segoe UI', sans-serif; }}")
        
        # Layout
        layout = QVBoxLayout(self)
        
        # Header Row (Stats + Add Button)
        header = QHBoxLayout()
        
        self.lbl_stats = QLabel()
        self.lbl_stats.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 14px; font-weight: bold;")
        
        btn_add = QPushButton(" + Add Milestone ")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"background-color: {COLORS['surface_light']}; border: 1px dashed {COLORS['primary']}; color: {COLORS['primary']}; padding: 6px; border-radius: 4px; font-weight: bold;")
        btn_add.clicked.connect(self.add_milestone)
        
        header.addWidget(self.lbl_stats)
        header.addStretch()
        header.addWidget(btn_add)
        
        layout.addLayout(header)
        
        # Canvas Placeholder 
        self.canvas_height = 250
        layout.addSpacing(self.canvas_height)
        
        # 2. Table Area (Lower)
        lbl_table = QLabel("Milestones List")
        lbl_table.setStyleSheet(f"color: {COLORS['text_main']}; font-size: 14px; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        layout.addWidget(lbl_table)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Date", "Name", "Sync F3", "Actions"])
        
        # Premium Table Styling
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['text_main']};
                gridline-color: {COLORS['border']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 13px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['surface']};
                color: {COLORS['primary']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['text_dim']};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {COLORS['border']};
                font-weight: bold;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
            }}
        """)
        
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Date
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Sync
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Actions
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setShowGrid(True)
        self.table.itemChanged.connect(self.on_table_item_changed)
        
        layout.addWidget(self.table)
        
        # Load Data AFTER UI is ready
        self.milestones = self._load_milestones()
        self.update_stats()
        self.update_table()

    def _load_milestones(self):
        # Default milestones if none exist
        defaults = [
            {"name": "PROPUESTA", "date": "2025-12-22", "synced": False},
            {"name": "PROPUESTA EN FIRME", "date": "2026-01-20", "synced": False},
            {"name": "CIERRE DEL ACUERDO", "date": "2026-03-25", "synced": False}
        ]
        
        spec = self.situation_data.get('specific_data', {})
        if 'milestones' in spec and isinstance(spec['milestones'], list) and len(spec['milestones']) > 0:
            ms = sorted(spec['milestones'], key=lambda x: x['date'])
            # Ensure 'synced' key exists
            for m in ms:
                if 'synced' not in m: m['synced'] = False
            return ms
            
        defaults.sort(key=lambda x: x['date'])
        self.save_milestones(defaults)
        return defaults

    def save_milestones(self, milestones=None):
        if milestones is not None:
            self.milestones = milestones
            self.milestones.sort(key=lambda x: x['date'])
            
        if 'specific_data' not in self.situation_data:
            self.situation_data['specific_data'] = {}
        
        self.situation_data['specific_data']['milestones'] = self.milestones
        
        # Persistence call
        # Persistence call
        if hasattr(self, 'special_situations_widget'):
            self.special_situations_widget.save_situation_specific_data(self.situation_data['id'], self.situation_data['specific_data'])
        else:
            wrapper = self
            while wrapper.parent():
                wrapper = wrapper.parent()
                if hasattr(wrapper, 'save_situation_specific_data'):
                    wrapper.save_situation_specific_data(self.situation_data['id'], self.situation_data['specific_data'])
                    break
        
        self.update_stats()
        self.update_table() # Sync Table
        self.update() # Repaint Canvas
        self.update() # Repaint Canvas
        # self.sync_to_calendar() # DISABLED: Using Virtual Events in CalendarView instead

    def update_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.milestones))
        
        for i, m in enumerate(self.milestones):
            d_str = m['date']
            date_widget = SmartDateEdit()
            date_widget.set_from_db(d_str)
            date_widget.setStyleSheet(f"background-color: transparent; border: none; color: {COLORS['text_main']}; font-size: 13px;")
                
            # Connect change signal
            date_widget.textChanged.connect(lambda _, idx=i, w=date_widget: self.on_date_changed(idx, w.text_for_db()))
            self.table.setCellWidget(i, 0, date_widget)
            
            # Name
            item_name = QTableWidgetItem(m['name'])
            self.table.setItem(i, 1, item_name)
            
            # Sync (Checkbox)
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(0,0,0,0)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            
            # CRITICAL: Block signals to prevent infinite loop/reset during table redraw
            chk.blockSignals(True)
            chk.setChecked(m.get('synced', False))
            chk.blockSignals(False)
            
            chk.stateChanged.connect(lambda state, idx=i: self.on_sync_changed(idx, state))
            chk_layout.addWidget(chk)
            # Ensure container is transparent so row hover works
            chk_widget.setStyleSheet("background-color: transparent;") 
            self.table.setCellWidget(i, 2, chk_widget)
            
            # Action (Delete)
            btn_del = QPushButton("❌")
            btn_del.setAutoDefault(False) # Prevent enter key triggering
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.clicked.connect(lambda _, idx=i: self.delete_milestone_direct(idx))
            btn_del.setFixedWidth(30)
            btn_del.setStyleSheet("background: transparent; color: red; border: none; font-weight: bold;")
            
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0,0,0,0)
            cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.addWidget(btn_del)
            self.table.setCellWidget(i, 3, cell_widget)
            
        self.table.blockSignals(False)

    def on_date_changed(self, idx, storage_date):
        if idx < 0 or idx >= len(self.milestones): return
        
        if self.milestones[idx]['date'] != storage_date:
            self.milestones[idx]['date'] = storage_date
            self.save_milestones()

    def on_table_item_changed(self, item):
        row = item.row()
        col = item.column()
        
        if row < 0 or row >= len(self.milestones): return
        
        # Guard: Column 0 is now a Widget, not an Item, so this won't trigger for Date.
        # Guard: Column 2 (Sync) and 3 (Delete) are also widgets.
        # Only Column 1 (Name) is a QTableWidgetItem.
        
        if col == 1: # Name
            val = item.text().strip()
            self.milestones[row]['name'] = val
            self.save_milestones() # Save and Resort

    def on_sync_changed(self, idx, state):
        if idx < 0 or idx >= len(self.milestones): return
        self.milestones[idx]['synced'] = (state == 2) # 2 = Checked
        self.save_milestones()

    def delete_milestone_direct(self, idx):
        if idx < 0 or idx >= len(self.milestones): return
        if QMessageBox.question(self, "Delete", "Delete this milestone?") == QMessageBox.StandardButton.Yes:
            self.milestones.pop(idx)
            self.save_milestones()

    def update_stats(self):
        today = datetime.date.today()
        
        # Get Start and Target dates from Situation Data (Preferred)
        start_date_str = self.situation_data.get('start_date')
        target_date_str = self.situation_data.get('target_date')
        
        # Fallback to milestones if dates missing
        if not start_date_str and self.milestones:
             sorted_m = sorted(self.milestones, key=lambda x: x['date'])
             if sorted_m[0]['date']: start_date_str = sorted_m[0]['date']
             
        if not target_date_str and self.milestones:
             sorted_m = sorted(self.milestones, key=lambda x: x['date'])
             if sorted_m[-1]['date']: target_date_str = sorted_m[-1]['date']
             
        # Parse
        s_date = None
        t_date = None
        
        try:
            if start_date_str:
                if isinstance(start_date_str, str):
                    s_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                elif isinstance(start_date_str, datetime.datetime):
                     s_date = start_date_str.date()
                elif isinstance(start_date_str, datetime.date):
                     s_date = start_date_str
            
            if target_date_str:
                if isinstance(target_date_str, str):
                    t_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
                elif isinstance(target_date_str, datetime.datetime):
                     t_date = target_date_str.date()
                elif isinstance(target_date_str, datetime.date):
                     t_date = target_date_str
        except: 
            pass
            
        parts = []
        if s_date and t_date:
            total = (t_date - s_date).days
            parts.append(f"TOTAL TIME: {total} Days")
        
        if t_date:
            remaining = (t_date - today).days
            parts.append(f"REMAINING: {remaining} Days")
        
        if not parts:
            self.lbl_stats.setText("Timeline: Data Insufficient")
        else:
            self.lbl_stats.setText(" | ".join(parts))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        # Restrict h to canvas height
        h = self.canvas_height
        
        margin_x = 50
        margin_y = 60 
        available_w = w - 2 * margin_x
        
        rect_canvas = QRectF(0, 0, w, h)
        # painter.fillRect(rect_canvas, QColor("#111")) # Debug background
        
        if not self.milestones:
             painter.setPen(QColor(COLORS['text_dim']))
             painter.drawText(rect_canvas, Qt.AlignmentFlag.AlignCenter, "No Milestones Defined")
             return
        
        today = datetime.date.today()
        # Filter out empty dates to avoid ValueError: time data '' does not match format '%Y-%m-%d'
        valid_milestones = [m for m in self.milestones if m.get('date')]
        if not valid_milestones:
             painter.setPen(QColor(COLORS['text_dim']))
             painter.drawText(rect_canvas, Qt.AlignmentFlag.AlignCenter, "No Valid Milestones (Check dates)")
             return
             
        dates = []
        for m in valid_milestones:
            d_val = m['date']
            if isinstance(d_val, str):
                dates.append(datetime.datetime.strptime(d_val, "%Y-%m-%d").date())
            elif isinstance(d_val, datetime.datetime):
                dates.append(d_val.date())
            elif isinstance(d_val, datetime.date):
                dates.append(d_val)
        min_date = min(dates + [today])
        max_date = max(dates + [today])
        
        total_days = (max_date - min_date).days
        if total_days == 0: total_days = 30
        
        y_axis = h / 2 
        
        # Axis
        pen = QPen(QColor(COLORS['border']))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(margin_x, int(y_axis), w - margin_x, int(y_axis))
        
        def get_x(date_obj):
            delta = (date_obj - min_date).days
            ratio = delta / total_days if total_days > 0 else 0
            return margin_x + ratio * available_w
            
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        
        self.hit_rects = [] 
        
        for i, m in enumerate(valid_milestones):
            d_val = m['date']
            d_obj = None
            if isinstance(d_val, str):
                d_obj = datetime.datetime.strptime(d_val, "%Y-%m-%d").date()
            elif isinstance(d_val, datetime.datetime):
                d_obj = d_val.date()
            elif isinstance(d_val, datetime.date):
                d_obj = d_val
                
            if not d_obj: continue 

            x = get_x(d_obj)
            
            radius = 6
            center = QPoint(int(x), int(y_axis))
            
            painter.setBrush(QBrush(QColor(COLORS['success'])))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, radius, radius)
            
            is_top = (i % 2 == 0)
            offset_y = -30 if is_top else 40
            
            painter.setPen(QColor(COLORS['text_main']))
            
            # Date (DD-MM-YYYY)
            date_display = d_obj.strftime("%d-%m-%Y")
            rect_date = QRectF(x - 50, y_axis + offset_y - 15, 100, 15)
            painter.drawText(rect_date, Qt.AlignmentFlag.AlignCenter, date_display)
            
            if m.get('synced', False):
                # Draw Calendar Icon (Unicode)
                rect_icon = QRectF(x + 35, y_axis + offset_y - 17, 20, 20)
                painter.drawText(rect_icon, Qt.AlignmentFlag.AlignLeft, "📅")

            # Name
            name_str = m['name']
            rect_name = QRectF(x - 75, y_axis + offset_y, 150, 20)
            font_bold = QFont(font)
            font_bold.setBold(True)
            painter.setFont(font_bold)
            painter.drawText(rect_name, Qt.AlignmentFlag.AlignCenter, name_str)
            painter.setFont(font)
            
            hit_r = QRectF(x - 20, y_axis - 20, 40, 40)
            self.hit_rects.append((hit_r, i))

        # Today Line
        x_today = get_x(today)
        pen_today = QPen(QColor("#2196F3"))
        pen_today.setWidth(2)
        pen_today.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen_today)
        painter.drawLine(int(x_today), int(y_axis - 40), int(x_today), int(y_axis + 40))
        painter.drawText(int(x_today) - 25, int(y_axis - 45), "TODAY")

    def contextMenuEvent(self, event):
        # Keep visual context menu for convenience
        clicked_idx = -1
        pos = event.pos()
        # Only check hit rects if in canvas area
        if pos.y() > self.canvas_height: return 
        
        for rect, idx in self.hit_rects:
            if rect.contains(pos):
                clicked_idx = idx
                break
        
        menu = QMenu(self)
        if clicked_idx >= 0:
            enc = menu.addAction("Edit")
            dele = menu.addAction("Delete")
            enc.triggered.connect(lambda: self.edit_milestone(clicked_idx))
            dele.triggered.connect(lambda: self.delete_milestone_direct(clicked_idx))
        else:
            add = menu.addAction("Add Milestone")
            add.triggered.connect(self.add_milestone)
            
        menu.exec(event.globalPos())

    def add_milestone(self):
        dlg = MilestoneDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            self.milestones.append(data)
            self.save_milestones()

    def edit_milestone(self, idx):
        m = self.milestones[idx]
        dlg = MilestoneDialog(self, m['name'], m['date'], m.get('synced', False))
        if dlg.exec():
            data = dlg.get_data()
            self.milestones[idx] = data
            self.save_milestones()
            
    def sync_to_calendar(self):
        """Syncs marked milestones to the main Calendar (F3) database."""
        try:
            # 1. Get Target Ticker
            tickers = self.situation_data.get('tickers', {})
            # Try target, then acquirer, then 'target' from specific dict if needed
            target_ticker = tickers.get('target') or tickers.get('acquirer')
            
            if not target_ticker:
                print("[SYNC] Skipping sync: No target ticker found.")
                return

            # 2. Setup DB Session
            engine = init_db()
            Session = get_session_factory(engine)
            session = Session()
            
            try:
                # 3. Find Company
                company = session.query(Company).filter(Company.ticker == target_ticker).first()
                if not company:
                    print(f"[SYNC] Skipping sync: Company {target_ticker} not found in DB.")
                    return
                
                # 4. Iterate Milestones
                for m in self.milestones:
                    is_synced = m.get('synced', False)
                    m_date_str = m['date']
                    m_name = m['name']
                    
                    # Define Event Logic
                    evt_desc = f"{self.situation_data.get('title', 'Special')} - {m_name}"
                    evt_date = datetime.datetime.strptime(m_date_str, "%Y-%m-%d")
                    evt_type = "Milestone"
                    
                    # Check existing
                    existing = session.query(CalendarEvent).filter(
                        and_(
                            CalendarEvent.company_id == company.id,
                            CalendarEvent.event_date == evt_date,
                            CalendarEvent.event_type == evt_type,
                            CalendarEvent.description == evt_desc
                        )
                    ).first()
                    
                    if is_synced:
                        if not existing:
                            print(f"[SYNC] Adding event: {evt_desc} on {m_date_str}")
                            new_evt = CalendarEvent(
                                company_id=company.id,
                                event_date=evt_date,
                                event_type=evt_type,
                                description=evt_desc,
                                source="special_situation",
                                status="Scheduled"
                            )
                            session.add(new_evt)
                        else:
                             # Exists, ensure update if needed (e.g. source)
                             pass
                    else:
                        if existing:
                            print(f"[SYNC] Removing event: {evt_desc}")
                            session.delete(existing)
                            
                session.commit()
                print("[SYNC] Calendar sync completed.")
                
            except Exception as e:
                session.rollback()
                print(f"[SYNC] Error during DB operations: {e}")
                import traceback
                traceback.print_exc()
            finally:
                session.close()
                
        except Exception as e:
             print(f"[SYNC] Fatal error in sync_to_calendar: {e}")
