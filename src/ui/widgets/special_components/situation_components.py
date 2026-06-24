import json
import os
import datetime
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QGridLayout, QSizePolicy,
    QProgressBar, QComboBox, QPushButton
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont
from ui.styles import COLORS

from config import LIBRARY_ROOT as _LIBRARY_ROOT_PATH
LIBRARY_ROOT = str(_LIBRARY_ROOT_PATH)
SPECIAL_ROOT = os.path.join(LIBRARY_ROOT, "SITUACIONES ESPECIALES")

CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "GBP.X": "£", "CAD": "C$", "AUD": "A$", "JPY": "¥",
    "CHF": "Fr", "CNY": "¥", "HKD": "HK$", "SGD": "S$", "INR": "₹", "BRL": "R$",
    "MXN": "Mex$", "PLN": "zł", "SEK": "kr", "NOK": "kr", "DKK": "kr", "ZAR": "R",
    "TRY": "₺", "ILS": "₪", "RUB": "₽", "KRW": "₩", "TWD": "NT$", "SAR": "﷼", "AED": "د.إ"
}

def calculate_special_progress(data):
    # 1. Time (30%) - Goal 10 Hours
    total_sec = data.get('total_seconds', 0)
    hours = total_sec / 3600.0
    score_time = min(hours / 10.0, 1.0) * 30.0

    h_int = int(hours)
    m_int = int((total_sec % 3600) // 60)
    time_str = f"{h_int:02d}:{m_int:02d} h"

    # 2. Files (10%)
    score_files = 0
    try:
        title = data.get('title', '').strip()
        if title:
            import re
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title).strip()
            folder_path = os.path.join(SPECIAL_ROOT, safe_title)
            if os.path.exists(folder_path):
                count = sum(len(files) for _, _, files in os.walk(folder_path))
                if count > 0:
                    score_files = 10.0
    except:
        pass

    # 3. Milestones (10%)
    m_list = data.get('milestones', [])
    score_miles = 10.0 if m_list else 0

    # 4. Notes (10%)
    spec = data.get('specific_data', {})
    score_notes = 10.0 if spec else 0

    # 5. Checklist Hielco (40%)
    score_checklist = 0.0
    checklist_g = spec.get('checklist_global',   {})
    checklist_s = spec.get('checklist_specific', {})
    all_checks = list(checklist_g.values()) + list(checklist_s.values())
    if all_checks:
        checked_count = sum(1 for c in all_checks if c.get('checked', False))
        score_checklist = (checked_count / len(all_checks)) * 40.0

    total = score_time + score_files + score_miles + score_notes + score_checklist
    return int(min(total, 100)), time_str


class SituationHeaderWidget(QFrame):
    navigation_requested = pyqtSignal(str)  # situation_id
    add_requested        = pyqtSignal()

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COLORS['surface_light']}; border-radius: 8px; border: 1px solid {COLORS['border']};")
        self.setFixedHeight(145)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(20)

        # 1. Left Col: Title & Category
        left_col = QVBoxLayout()
        left_col.setSpacing(5)
        left_col.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        # Title row: label + hidden combo + small + button
        title_row = QHBoxLayout()
        title_row.setSpacing(4)
        title_row.setContentsMargins(0, 0, 0, 0)

        # Dropdown integrated into company name display
        self.nav_combo = QComboBox()
        self.nav_combo.setStyleSheet(f"""
            QComboBox {{
                color: {COLORS['primary']}; 
                font-weight: bold; 
                font-size: 16pt; 
                border: none; 
                background: transparent;
                padding-right: 15px; /* space for arrow */
            }}
            QComboBox::drop-down {{
                border: none;
                background: transparent;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background: {COLORS['surface']};
                color: {COLORS['text_main']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['primary']};
                selection-color: black;
                font-size: 14pt;
                min-width: 300px;
            }}
        """)
        self.nav_combo.currentIndexChanged.connect(self._on_nav_changed)
        title_row.addWidget(self.nav_combo)

        # + button (small, orange)
        self.btn_add_new = QPushButton("+")
        self.btn_add_new.setFixedSize(22, 22)
        self.btn_add_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_new.setToolTip("New situation")
        self.btn_add_new.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
                border-radius: 11px;
                font-weight: bold;
                font-size: 14px;
                padding: 0;
            }}
            QPushButton:hover {{ background: {COLORS['primary']}; color: #000; }}
        """)
        self.btn_add_new.clicked.connect(self.add_requested.emit)
        title_row.addWidget(self.btn_add_new)
        title_row.addStretch()

        left_col.addLayout(title_row)

        self.lbl_category = QLabel("Category | Type")
        self.lbl_category.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px; border: none; background: transparent; margin-top: 2px;")
        left_col.addWidget(self.lbl_category)

        left_col.addSpacing(10)

        
        # Tickers & Prices Grid
        tp_grid = QGridLayout()
        tp_grid.setAlignment(Qt.AlignmentFlag.AlignLeft)
        tp_grid.setHorizontalSpacing(8)
        tp_grid.setVerticalSpacing(2)
        
        self.lbl_tick_1 = self._make_ticker_label()
        self.lbl_tick_2 = self._make_ticker_label()
        self.lbl_price_1 = self._make_price_label()
        self.lbl_price_2 = self._make_price_label()
        
        tp_grid.addWidget(self.lbl_tick_1, 0, 0)
        tp_grid.addWidget(self.lbl_tick_2, 0, 1)
        tp_grid.addWidget(self.lbl_price_1, 1, 0)
        tp_grid.addWidget(self.lbl_price_2, 1, 1)
        
        left_col.addLayout(tp_grid)
        
        # 2. Middle Col: Dates
        mid_col = QVBoxLayout()
        mid_col.setSpacing(5)
        mid_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- PROGRESS ABOVE DATES ---
        self.lbl_time_spent = QLabel("00:00 h")
        self.lbl_time_spent.setStyleSheet(f"color: #FFEB3B; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        self.lbl_time_spent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.pbar_header = QProgressBar()
        self.pbar_header.setFixedHeight(22)
        self.pbar_header.setMinimumWidth(120)
        self.pbar_header.setMaximumWidth(350)
        self.pbar_header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.pbar_header.setTextVisible(True)
        self.pbar_header.setFormat("%p%")
        self.pbar_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pbar_header.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: #333;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
                border-radius: 6px;
            }}
        """)
        
        mid_col.addWidget(self.lbl_time_spent)
        mid_col.addWidget(self.pbar_header)
        mid_col.addSpacing(10)
        # ----------------------------
        
        dates_layout = QHBoxLayout()
        dates_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dates_layout.setSpacing(20)
        dates_layout.setContentsMargins(0, 0, 0, 0)
        
        start_layout = QVBoxLayout()
        start_layout.setSpacing(2)
        start_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_start_t = QLabel("START")
        lbl_start_t.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px; border: none; background: transparent;")
        lbl_start_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_start_date = QLabel("-")
        self.lbl_start_date.setStyleSheet(f"color: white; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        self.lbl_start_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        start_layout.addWidget(lbl_start_t)
        start_layout.addWidget(self.lbl_start_date)
        
        end_layout = QVBoxLayout()
        end_layout.setSpacing(2)
        end_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_end_t = QLabel("END")
        lbl_end_t.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px; border: none; background: transparent;")
        lbl_end_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_end_date = QLabel("-")
        self.lbl_end_date.setStyleSheet(f"color: {COLORS['success']}; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        
        end_layout.addWidget(lbl_end_t)
        end_layout.addWidget(self.lbl_end_date)
        
        dates_layout.addLayout(start_layout)
        dates_layout.addLayout(end_layout)
        mid_col.addLayout(dates_layout)
        
        # 3. Right Col: Metrics
        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        
        metrics_grid = QGridLayout()
        metrics_grid.setHorizontalSpacing(20)
        metrics_grid.setVerticalSpacing(2)
        
        lbl_irr_t = QLabel("IRR")
        lbl_irr_t.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px; border: none; background: transparent;")
        lbl_spread_t = QLabel("SPREAD")
        lbl_spread_t.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px; border: none; background: transparent;")
        
        metrics_grid.addWidget(lbl_irr_t, 0, 0, Qt.AlignmentFlag.AlignCenter)
        metrics_grid.addWidget(lbl_spread_t, 0, 1, Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_irr = QLabel("-")
        self.lbl_irr.setStyleSheet(f"color: {COLORS['accent']}; font-size: 18px; font-weight: bold; border: none; background: transparent;")
        self.lbl_spread = QLabel("-")
        self.lbl_spread.setStyleSheet(f"color: {COLORS['primary']}; font-size: 18px; font-weight: bold; border: none; background: transparent;")
        
        metrics_grid.addWidget(self.lbl_irr, 1, 0, Qt.AlignmentFlag.AlignCenter)
        metrics_grid.addWidget(self.lbl_spread, 1, 1, Qt.AlignmentFlag.AlignCenter)
        
        lbl_money_t = QLabel("MONEY IN")
        lbl_money_t.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px; border: none; background: transparent;")
        lbl_profit_t = QLabel("EXP. PROFIT")
        lbl_profit_t.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px; border: none; background: transparent;")
        
        metrics_grid.addWidget(lbl_money_t, 2, 0, Qt.AlignmentFlag.AlignCenter)
        metrics_grid.addWidget(lbl_profit_t, 2, 1, Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_money = QLabel("-")
        self.lbl_money.setStyleSheet(f"color: white; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        self.lbl_profit = QLabel("-")
        self.lbl_profit.setStyleSheet(f"color: {COLORS['success']}; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        
        metrics_grid.addWidget(self.lbl_money, 3, 0, Qt.AlignmentFlag.AlignCenter)
        metrics_grid.addWidget(self.lbl_profit, 3, 1, Qt.AlignmentFlag.AlignCenter)
        
        right_col.addLayout(metrics_grid)
        
        main_layout.addLayout(left_col, stretch=4)
        main_layout.addLayout(mid_col, stretch=3)
        main_layout.addLayout(right_col, stretch=4)
        
        if data:
            self.update_data(data)

    def _make_ticker_label(self):
        l = QLabel("-")
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['primary']}; font-weight: bold; border-radius: 4px; padding: 2px 8px; font-size: 13px; border: 1px solid {COLORS['border']};")
        return l

    def _make_price_label(self):
        l = QLabel("-")
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text_main']}; font-weight: bold; border-radius: 4px; padding: 2px 8px; font-size: 13px; border: 1px solid {COLORS['border']};")
        return l

    def populate_nav_combo(self, situations_list, current_id=None):
        """Fill the navigation combo with all situations. situations_list is a list of dicts with 'id' and 'title'."""
        self._nav_situations = situations_list  # [{id, title}, ...]
        self.nav_combo.blockSignals(True)
        self.nav_combo.clear()
        
        self.nav_combo.addItem("Select a situation...", None)
        selected_idx = 0
        
        for i, s in enumerate(situations_list):
            self.nav_combo.addItem(s.get('title', '?'), s.get('id'))
            if s.get('id') == current_id:
                selected_idx = i + 1  # +1 because of the first item
                
        self.nav_combo.setCurrentIndex(selected_idx)
        self.nav_combo.blockSignals(False)

    def _on_nav_changed(self, index):
        if index < 0:
            return
        sid = self.nav_combo.itemData(index)
        if sid is not None:
            self.navigation_requested.emit(sid)


    def update_data(self, data, live_prices={}, spread_txt="0.0%", irr_txt="0.0%"):
        cat = data.get('strategy_type', 'Generic')
        self.lbl_category.setText(f"{cat}")
        
        # Date Formatting (DD-MM-YYYY)
        def fmt_date(d):
            if not d: return "-"
            if isinstance(d, str):
                try: d = datetime.datetime.strptime(d, "%Y-%m-%d").date()
                except: return d
            if hasattr(d, 'strftime'): return d.strftime("%d-%m-%Y")
            return str(d)

        self.lbl_start_date.setText(fmt_date(data.get('start_date')))
        self.lbl_end_date.setText(fmt_date(data.get('target_date')))
        
        tickers_map = data.get('tickers_dict', data.get('tickers', {}))
        if isinstance(tickers_map, str):
             try: tickers_map = json.loads(tickers_map)
             except: tickers_map = {}
        
        specific = data.get('specific_data', {})
        yahoo_tickers = specific.get('yahoo_tickers', {})
        
        display_items = []
        if 'target' in tickers_map:
            dt = tickers_map['target']
            pk = yahoo_tickers.get('target', dt)
            display_items.append((dt, pk))
        if 'acquirer' in tickers_map:
            dt = tickers_map['acquirer']
            pk = yahoo_tickers.get('acquirer', dt)
            display_items.append((dt, pk))
            
        if not display_items:
             for k, v in tickers_map.items():
                 pk = yahoo_tickers.get(k, v)
                 display_items.append((v, pk))
        
        labels = [(self.lbl_tick_1, self.lbl_price_1), (self.lbl_tick_2, self.lbl_price_2)]
        for tick_l, price_l in labels:
            tick_l.setText("")
            price_l.setText("")
            tick_l.hide()
            price_l.hide()
            
        for i, (disp_tick, price_key) in enumerate(display_items):
            if i >= len(labels): break
            lbl_t, lbl_p = labels[i]
            lbl_t.setText(disp_tick)
            lbl_t.show()
            lbl_t.show()
            px = live_prices.get(price_key, 0.0)
            
            # Determine Currency Symbol
            # 1. find role (target/acquirer) for this ticker
            role = 'target'
            if 'acquirer' in tickers_map and tickers_map['acquirer'] == disp_tick: role = 'acquirer'
            elif 'target' in tickers_map and tickers_map['target'] == disp_tick: role = 'target'
            else:
                 # fallback search in values
                 for r, t in tickers_map.items():
                     if t == disp_tick: 
                         role = r
                         break
            
            curr_code = data.get('specific_data', {}).get('currencies', {}).get(role, 'USD')
            # Extract "USD" from "USD - US Dollar" if needed
            if " - " in curr_code: curr_code = curr_code.split(" - ")[0]
            
            # --- TRANSLATE GBX to GBP visually ---
            if curr_code.upper() in ["GBX", "GBP.X", "GBP.X - BRITISH PENCE"] and px > 0:
                curr_code = "GBP"
            
            sym = CURRENCY_SYMBOLS.get(curr_code, "$")
            
            lbl_p.setText(f"{sym}{px:.2f}" if px > 0 else "-")
            lbl_p.show()
        
        
        # Currency for global values (Money In / Profit)
        # Use Target currency as main, or whatever we have
        main_curr = data.get('specific_data', {}).get('currencies', {}).get('target', 'USD')
        if not main_curr: main_curr = data.get('specific_data', {}).get('currencies', {}).get('acquirer', 'USD')
        
        if " - " in main_curr: main_curr = main_curr.split(" - ")[0]
        
        # --- TRANSLATE GBX to GBP ---
        if main_curr.upper() in ["GBX", "GBP.X", "GBP.X - BRITISH PENCE"]: 
            main_curr = "GBP"
            
        main_sym = CURRENCY_SYMBOLS.get(main_curr, "$")
        
        self.lbl_irr.setText(irr_txt)
        self.lbl_spread.setText(spread_txt)
        cap = data.get('capital_allocated', 0.0)
        self.lbl_money.setText(f"{main_sym}{cap:,.0f}")
        
        try:
            spread_val = float(spread_txt.replace('%','').strip())
            profit = cap * (spread_val / 100.0)
            self.lbl_profit.setText(f"{main_sym}{profit:,.0f}")
            color = COLORS['success'] if profit >= 0 else COLORS['danger']
            self.lbl_profit.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        except:
            self.lbl_profit.setText(f"{main_sym}-")
            self.lbl_profit.setStyleSheet(f"color: {COLORS['success']}; font-size: 15px; font-weight: bold; border: none; background: transparent;")
            
        # Progress Update
        pct, t_str = calculate_special_progress(data)
        self.lbl_time_spent.setText(t_str)
        self.pbar_header.setValue(pct)
