
from ui.shared.dialogs.special_dialogs import SituationSettingsDialog, AddAttributeDialog, AddSituationWizard
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget, 
    QListWidget, QListWidgetItem, QFrame, QScrollArea, QSplitter, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
    QDialog, QFormLayout, QLineEdit, QComboBox, QDateEdit, QDialogButtonBox,
    QGroupBox, QSpinBox, QDoubleSpinBox, QWizard, QWizardPage, QMenu, QMessageBox, QInputDialog,
    QSizePolicy, QGridLayout, QCheckBox, QTextEdit, QSlider, QTabWidget, QCompleter
)
from core.price_fetcher import EXCHANGE_SUFFIXES
from PyQt6.QtCore import Qt, QSize, QDate, pyqtSignal, QUrl, QThread, QTimer
from PyQt6.QtGui import QIcon, QAction, QDesktopServices, QColor
import webbrowser
from ui.widgets.special_tabs.checklist_tab import SituationChecklistWidget
from core.services.special_service import SpecialService

from core.special_definitions import (
    SITUATION_TYPES, SITUATION_CATEGORIES, CHECKLIST_GLOBAL, CHECKLIST_BY_TYPE,
    calculate_global_core, calculate_scenario_irr, calculate_xirr, resolve_type
)
from ui.styles import COLORS
from ui.widgets.special_components.situation_prompts import SituationPromptManagerDialog
from ui.widgets.special_components.situation_timeline import SituationTimelineWidget
from ui.widgets.special_components.situation_library import SituationLibraryWidget
from ui.widgets.special_components.situation_notes import SituationNotesWidget
from ui.widgets.special_components.situation_components import SituationHeaderWidget, CURRENCY_SYMBOLS
from ui.widgets.edit_attributes_dialog import EditAttributesDialog
import json
import os
import re
import datetime


# --- CUSTOM WIDGETS ---
class NoScrollComboBox(QComboBox):
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
        # Remove anything not numeric
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
        # Convert DD-MM-YYYY to YYYY-MM-DD
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

# --- WORKER THREAD FOR PRICES ---
class PriceWorker(QThread):
    finished = pyqtSignal(int, dict, dict) # req_id, updates, raw_prices

    def __init__(self, req_id, tickers_dict, current_data_role_map):
        super().__init__()
        self.req_id = req_id
        self.tickers = tickers_dict
        self.role_map = current_data_role_map 

    def run(self):
        from core.price_fetcher import price_fetcher
        
        updates = {}
        raw_prices = {}
        
        for key, symbol in self.tickers.items():
            if not symbol: continue
            try:
                price = price_fetcher.get_price(symbol)
                if price:
                    raw_prices[symbol] = price
                    if key == 'target': updates['target_price'] = price
                    elif key == 'parent': updates['parent_price'] = price
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
        
        self.finished.emit(self.req_id, updates, raw_prices)

# --- CONSTANTS & CONFIGURATION ---

# SITUATION_CATEGORIES is now imported from core.special_definitions (V2)



# --- CLASSES ---

class SituationSidebarItemWidget(QWidget):
    def __init__(self, title, category, status):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Left: Title & Category
        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['text_main']}; border: none;")
        
        lbl_cat = QLabel(category)
        lbl_cat.setStyleSheet(f"font-size: 12px; color: {COLORS['text_dim']}; border: none;")
        
        left_layout.addWidget(lbl_title)
        left_layout.addWidget(lbl_cat)
        
        layout.addLayout(left_layout)
        layout.addStretch()
        
        # Right: Status Dot
        dot = QLabel()
        dot.setFixedSize(10, 10)
        
        color = "#FFFFFF"
        s_lower = status.lower()
        if "pipeline" in s_lower:
            color = "#FF9800" # Golden Orange
        elif "active" in s_lower:
            color = "#2ECC71" # Green
        elif "basic" in s_lower:
            color = "#9B59B6" # Purple
        elif "close" in s_lower or "closed" in s_lower:
            color = "#E74C3C" # Red
        else:
            color = "#999999" # Gray for others
            
        dot.setStyleSheet(f"background-color: {color}; border-radius: 5px; border: none;")
        layout.addWidget(dot)
        
        # Transparent background to let selection show through
        self.setStyleSheet("background: transparent; border: none;")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True) 



class LinkButton(QPushButton):
    config_changed = pyqtSignal(str, dict)  # btn_id, new_config

    def __init__(self, btn_id, default_label, is_fixed_name=False, parent=None):
        super().__init__(default_label, parent)
        self.btn_id = btn_id
        self.default_label = default_label
        self.is_fixed_name = is_fixed_name
        self.url = ""
        self.custom_label = default_label
        self.custom_color = ""  # empty = use default theme color

        self.clicked.connect(self.open_link)
        self._apply_style()

    def _apply_style(self):
        clr = self.custom_color if self.custom_color else COLORS['text_main']
        border_clr = self.custom_color if self.custom_color else COLORS['border']
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                color: {clr};
                border: 1px solid {border_clr};
                border-radius: 4px;
                padding: 6px 12px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
                border-color: {clr};
            }}
        """)

    def set_config(self, config):
        self.url = config.get('url', '')
        self.custom_label = config.get('label', self.default_label)
        self.custom_color = config.get('color', '')
        self.setText(self.custom_label)
        self._apply_style()
        self.setToolTip(self.url if self.url else "Right-click to configure")

    def get_config(self):
        return {'label': self.custom_label, 'url': self.url, 'color': self.custom_color}

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        edit_action  = menu.addAction("Edit Button")
        color_action = menu.addAction("Change Color...")
        reset_action = menu.addAction("Reset Color")
        action = menu.exec(event.globalPos())

        if action == edit_action:
            self.edit_button()
        elif action == color_action:
            self._pick_color()
        elif action == reset_action:
            self.custom_color = ""
            self._apply_style()
            self.config_changed.emit(self.btn_id, self.get_config())

    def _pick_color(self):
        from PyQt6.QtWidgets import QColorDialog
        from PyQt6.QtGui import QColor
        init = QColor(self.custom_color) if self.custom_color else QColor(COLORS['text_main'])
        clr = QColorDialog.getColor(init, self, "Choose Button Color")
        if clr.isValid():
            self.custom_color = clr.name()
            self._apply_style()
            self.config_changed.emit(self.btn_id, self.get_config())

    def edit_button(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Button")
        layout = QFormLayout(dialog)

        lbl_edit = QLineEdit(self.custom_label)
        if self.is_fixed_name:
            lbl_edit.setEnabled(False)

        url_edit = QLineEdit(self.url)
        url_edit.setPlaceholderText("https://...")

        # Color preview row
        from PyQt6.QtWidgets import QColorDialog
        from PyQt6.QtGui import QColor
        color_btn = QPushButton(self.custom_color or "Default")
        color_btn.setFixedHeight(28)
        _clr = self.custom_color or COLORS['text_main']
        color_btn.setStyleSheet(f"background:{COLORS['surface_light']}; color:{_clr}; border:1px solid {_clr}; border-radius:3px; padding:0 8px;")

        def pick():
            init = QColor(self.custom_color) if self.custom_color else QColor(COLORS['text_main'])
            c = QColorDialog.getColor(init, dialog, "Choose Color")
            if c.isValid():
                color_btn._chosen = c.name()
                color_btn.setText(c.name())
                color_btn.setStyleSheet(f"background:{COLORS['surface_light']}; color:{c.name()}; border:1px solid {c.name()}; border-radius:3px; padding:0 8px;")
        color_btn._chosen = self.custom_color
        color_btn.clicked.connect(pick)

        layout.addRow("Label:",  lbl_edit)
        layout.addRow("URL:",    url_edit)
        layout.addRow("Color:",  color_btn)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec():
            new_label = lbl_edit.text().strip()
            self.custom_label = new_label if new_label else self.default_label
            self.url = url_edit.text().strip()
            self.custom_color = color_btn._chosen
            self.setText(self.custom_label)
            self.setToolTip(self.url)
            self._apply_style()
            self.config_changed.emit(self.btn_id, self.get_config())

    def open_link(self):
        if self.url:
            from ui.styles import open_url_chrome
            open_url_chrome(self.url)
        else:
            self.edit_button()


class LinkBarWidget(QWidget):
    data_changed = pyqtSignal(dict) # Full config dict

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(8)

        self.buttons = {}

        # EDIT button (orange outline)
        self.btn_edit_action = QPushButton("EDIT")
        self.btn_edit_action.setFixedHeight(32)
        self.btn_edit_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit_action.setToolTip("Edit this situation")
        self.btn_edit_action.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
                border-radius: 4px;
                padding: 4px 14px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary']};
                color: #000;
            }}
        """)
        layout.addWidget(self.btn_edit_action)

        # Separator
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(24)
        sep.setStyleSheet(f"background: {COLORS['border']};")
        layout.addWidget(sep)

        # ── Configurable link buttons ──────────────────────────
        defs = [
            ("btn_gem",  "Gem",          True),
            ("btn_ltm",  "LTM Notebook", True),
            ("btn_c1",   "Variable 1",   False),
            ("btn_c2",   "Variable 2",   False),
            ("btn_c3",   "Variable 3",   False),
        ]

        for bid, label, fixed in defs:
            btn = LinkButton(bid, label, is_fixed_name=fixed)
            btn.config_changed.connect(self.on_btn_changed)
            layout.addWidget(btn)
            self.buttons[bid] = btn

        layout.addStretch()

    def load_config(self, config):
        if not config: config = {}
        for bid, btn in self.buttons.items():
            if bid in config:
                btn.set_config(config[bid])
            else:
                btn.set_config({'label': btn.default_label, 'url': ''})

    def on_btn_changed(self, btn_id, new_btn_config):
        full_config = {}
        for bid, btn in self.buttons.items():
            full_config[bid] = btn.get_config()
        self.data_changed.emit(full_config)


class SpecialSituationsWidget(QWidget):
    data_changed = pyqtSignal()
    
    def __init__(self, portfolio_manager):
        super().__init__()
        self.portfolio_manager = portfolio_manager
        self.service = SpecialService() # New service
        self.manager = self.service # Drop-in replacement for Legacy calls
        self.current_situation_id = None
        self.current_data = None
        self._all_situations = []
        self.price_worker = None
        self.fetch_id = 0

        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(400) # 400ms debounce
        self.save_timer.timeout.connect(self._save_inline_params_to_db)

        self.init_ui()
        self.load_sidebar()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # Track collapsed state
        self.sidebar_collapsed = True  # Start collapsed
        self.sidebar_width = 300  # Width when expanded
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Custom splitter styling with double-line handle
        self.splitter.setHandleWidth(8)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {COLORS['border']};
                border-left: 2px solid {COLORS['surface_light']};
                border-right: 2px solid {COLORS['surface_light']};
            }}
            QSplitter::handle:hover {{
                background-color: {COLORS['primary']};
            }}
        """)
        
        # --- Left Panel: Sidebar List ---
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setStyleSheet(f"background-color: {COLORS['surface']}; border-right: 1px solid {COLORS['border']};")
        # Start with 0 width (collapsed)
        self.sidebar_frame.setFixedWidth(0)
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        
        lbl_title = QLabel("SITUATIONS")
        lbl_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['primary']}; margin-bottom: 10px;")
        sidebar_layout.addWidget(lbl_title)
        
        # Filter Combo
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Status", "Pipeline", "Active", "Basic", "Closed"])
        self.filter_combo.currentTextChanged.connect(self.load_sidebar)
        sidebar_layout.addWidget(self.filter_combo)

        self.situations_list = QTreeWidget()
        self.situations_list.setHeaderHidden(True)
        self.situations_list.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['surface']};
                border: none;
                outline: none;
            }}
            QTreeWidget::item {{
                height: 50px; 
                padding-left: 5px;
                border: none;
                border-bottom: 1px solid #252525;
            }}
            QTreeWidget::item:selected {{
                background-color: {COLORS['surface_light']};
                border: none;
            }}
            QTreeWidget::item:hover {{
                background-color: {COLORS['surface_light']};
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: none; /* Custom arrow if needed */
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings  {{
                border-image: none;
                image: none;
            }}
        """)
        self.situations_list.setIndentation(20)
        self.situations_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.situations_list.customContextMenuRequested.connect(self.show_sidebar_context_menu)
        self.situations_list.itemClicked.connect(self.on_situation_selected)
        sidebar_layout.addWidget(self.situations_list)
        
        btn_add = QPushButton("+ NEW SITUATION")
        btn_add.setStyleSheet(f"background-color: {COLORS['accent']}; color: black; font-weight: bold; padding: 10px;")
        btn_add.clicked.connect(self.open_add_dialog)
        sidebar_layout.addWidget(btn_add)
        
        # --- Right Panel: Workspace ---
        self.workspace_frame = QFrame()
        self.workspace_layout = QVBoxLayout(self.workspace_frame)
        self.workspace_layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. Header (Always Visible)
        self.header_widget = SituationHeaderWidget()
        self.header_widget.navigation_requested.connect(self._navigate_to_situation)
        self.header_widget.add_requested.connect(self.open_add_dialog)
        self.workspace_layout.addWidget(self.header_widget)

        self.empty_label = QLabel("Select a situation or create a new one.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 18px; margin: 40px;")
        self.workspace_layout.addWidget(self.empty_label)
        
        self.content_container = QWidget()
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10) # Spacing
        self.link_bar = LinkBarWidget()
        self.link_bar.data_changed.connect(self.save_link_config)
        self.link_bar.btn_edit_action.clicked.connect(self._open_edit_from_linkbar)

        content_layout.addWidget(self.link_bar)

        
        # 3. Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLORS['border']}; background: {COLORS['surface']}; border-radius: 4px; }}
            QTabBar::tab {{ background: {COLORS['surface_light']}; color: {COLORS['text_dim']}; padding: 8px 15px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
            QTabBar::tab:selected {{ background: {COLORS['primary']}; color: #000; font-weight: bold; }}
        """)
        
        # Tab 1: Analysis calc
        self.tab_analysis = QWidget()
        self.init_analysis_tab()
        self.tabs.addTab(self.tab_analysis, "Analysis calc")

        # Tab 2: Checklist Hielco (V2)
        self.tab_checklist = SituationChecklistWidget(self)
        self.tab_checklist.checklist_updated.connect(lambda txt: self.tabs.setTabText(self.tab_checklist_index, txt))
        self.tab_checklist_index = self.tabs.count()
        self.tabs.addTab(self.tab_checklist, "Checklist [0%]")

        # Tab 3: Temp. line
        self.tab_timeline = QWidget()
        self.tab_timeline_layout = QVBoxLayout(self.tab_timeline)
        self.tabs.addTab(self.tab_timeline, "Temp. line")

        # Tab 4: Documentos
        self.tab_documents = QWidget()
        self.tab_documents_layout = QVBoxLayout(self.tab_documents)
        self.tabs.addTab(self.tab_documents, "Documentos")

        # Tab 5: Riesgos
        self.tab_risks = QWidget()
        self.tab_risks_layout = QVBoxLayout(self.tab_risks)
        self.tabs.addTab(self.tab_risks, "Riesgos")

        # Tab 6: Share holders
        self.tab_shareholders = QWidget()
        self.tab_shareholders_layout = QVBoxLayout(self.tab_shareholders)
        self.tabs.addTab(self.tab_shareholders, "Share holders")

        # Tab 7: Notas
        self.tab_notes = QWidget()
        self.tab_notes_layout = QVBoxLayout(self.tab_notes)
        self.tabs.addTab(self.tab_notes, "Notas")


        
        content_layout.addWidget(self.tabs)
        
        self.workspace_layout.addWidget(self.content_container)
        self.content_container.hide() 

        self.splitter.addWidget(self.sidebar_frame)
        self.splitter.addWidget(self.workspace_frame)
        # Start collapsed: sidebar=0, workspace gets all space
        self.splitter.setSizes([0, 1300])
        
        # Install event filter on splitter handle for double-click
        self.splitter.handle(1).installEventFilter(self)
        
        main_layout.addWidget(self.splitter)


    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        return super().eventFilter(obj, event)

    def toggle_sidebar(self):
        """Toggle sidebar collapse/expand via ☰ button"""
        if self.sidebar_collapsed:
            self.sidebar_frame.setFixedWidth(self.sidebar_width)
            self.splitter.setSizes([self.sidebar_width, 1000])
            self.sidebar_collapsed = False
        else:
            self.sidebar_frame.setFixedWidth(0)
            self.splitter.setSizes([0, 1300])
            self.sidebar_collapsed = True

    def _open_edit_from_linkbar(self):
        """Open edit wizard from the EDIT button in the link bar."""
        if self.current_data:
            self.open_edit_dialog(self.current_data)



    # ... [Tab Inits similar to before, but we will focus on the Sidebar and Add Dialog enhancements first] ...
    
    def init_analysis_tab(self):
        layout = QHBoxLayout(self.tab_analysis)
        layout.setSpacing(12)

        # ── LEFT: vertical scroll = Params inline + Strategy Inputs ─────────
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setStyleSheet("background: transparent;")

        left_container = QWidget()
        left_container.setStyleSheet("background: transparent;")
        left_vlay = QVBoxLayout(left_container)
        left_vlay.setSpacing(4)
        left_vlay.setContentsMargins(0, 0, 5, 0)
        left_scroll.setWidget(left_container)

        _ps = (
            f"QGroupBox {{ font-weight:bold; color:{COLORS['primary']};"
            f" border:1px solid {COLORS['border']}; border-radius:6px;"
            f" margin-top:8px; padding-top:8px; background:{COLORS['surface']}; }}"
            f" QGroupBox::title {{ subcontrol-origin:margin; left:10px; padding:0 4px; }}"
        )

        def _spin(lo=0, hi=999999, dec=2, suf=""):
            sb = QDoubleSpinBox()
            sb.setRange(lo, hi)
            sb.setDecimals(dec)
            sb.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            if suf: sb.setSuffix(suf)
            sb.setStyleSheet(f"background:{COLORS['surface_light']}; color:white; border:1px solid {COLORS['border']}; padding:3px; border-radius:3px;")
            return sb

        # ── STRATEGY SPECIFIC INPUTS ──────────────────────────────────
        self.inputs_group = QGroupBox("STRATEGY SPECIFIC INPUTS")
        self.inputs_group.setStyleSheet(_ps)
        self.inputs_layout = QGridLayout(self.inputs_group)
        self.inputs_layout.setVerticalSpacing(2)
        self.inputs_layout.setHorizontalSpacing(10)
        left_vlay.addWidget(self.inputs_group)

        # ── TIMELINE ──────────────────────────────────────────────────
        grp_tl = QGroupBox("TIMELINE")
        grp_tl.setStyleSheet(_ps)
        form_tl = QFormLayout(grp_tl)
        form_tl.setVerticalSpacing(2); form_tl.setHorizontalSpacing(10)
        self.ip_start_date = SmartDateEdit(placeholder="Inicio DD-MM-YYYY")
        self.ip_start_date.setStyleSheet(f"background:{COLORS['surface_light']}; color:white; border:1px solid {COLORS['border']}; padding:3px; border-radius:3px;")
        self.ip_end_date   = SmartDateEdit(placeholder="Target DD-MM-YYYY")
        self.ip_end_date.setStyleSheet(f"background:{COLORS['surface_light']}; color:white; border:1px solid {COLORS['border']}; padding:3px; border-radius:3px;")
        form_tl.addRow("Start Date:",  self.ip_start_date)
        form_tl.addRow("Target Date:", self.ip_end_date)
        left_vlay.addWidget(grp_tl)

        # ── DEAL PARAMETERS ──────────────────────────────────────────
        self.grp_dp = QGroupBox("DEAL PARAMETERS")
        self.grp_dp.setStyleSheet(_ps)
        form_dp = QFormLayout(self.grp_dp)
        form_dp.setVerticalSpacing(2); form_dp.setHorizontalSpacing(10)
        self.ip_outside_date = SmartDateEdit(placeholder="Outside Date DD-MM-YYYY")
        self.ip_outside_date.setStyleSheet(f"background:{COLORS['surface_light']}; color:white; border:1px solid {COLORS['border']}; padding:3px; border-radius:3px;")
        self.ip_close_prob   = _spin(0, 100, 0, " %")
        self.ip_break_fee    = _spin(0, 100, 2, " %")
        form_dp.addRow("Outside Date:",  self.ip_outside_date)
        form_dp.addRow("Close Prob %:",  self.ip_close_prob)
        form_dp.addRow("Break Fee %:",   self.ip_break_fee)
        left_vlay.addWidget(self.grp_dp)

        # ── FINANCIALS ───────────────────────────────────────────────
        grp_fin2 = QGroupBox("FINANCIALS")
        grp_fin2.setStyleSheet(_ps)
        form_fin = QFormLayout(grp_fin2)
        form_fin.setVerticalSpacing(2); form_fin.setHorizontalSpacing(10)
        self.ip_entry_price = _spin(0, 9999999, 2)
        self.ip_deal_value  = _spin(0, 9999999, 2)
        self.ip_downside    = _spin(0, 9999999, 2)
        self.ip_capital     = _spin(0, 999999999, 0)
        self.ip_reinforce   = _spin(0, 9999999, 2)
        self.ip_reduce      = _spin(0, 9999999, 2)
        form_fin.addRow("Entry Price:",    self.ip_entry_price)
        form_fin.addRow("Deal Price:",     self.ip_deal_value)
        form_fin.addRow("Downside Price:", self.ip_downside)
        form_fin.addRow("Capital:",        self.ip_capital)
        rr_w = QWidget(); rr_l = QHBoxLayout(rr_w); rr_l.setContentsMargins(0,0,0,0); rr_l.setSpacing(4)
        rr_l.addWidget(QLabel("Reforzar:")); rr_l.addWidget(self.ip_reinforce)
        rr_l.addWidget(QLabel("Reducir:"));  rr_l.addWidget(self.ip_reduce)
        form_fin.addRow("Precios R/R:",   rr_w)
        left_vlay.addWidget(grp_fin2)

        # Wire auto-save
        for w in [self.ip_close_prob, self.ip_break_fee, self.ip_entry_price,
                  self.ip_deal_value, self.ip_downside, self.ip_capital,
                  self.ip_reinforce, self.ip_reduce]:
            w.valueChanged.connect(self._save_inline_params)
        for w in [self.ip_start_date, self.ip_end_date, self.ip_outside_date]:
            w.editingFinished.connect(self._save_inline_params)

        left_vlay.addStretch()
        layout.addWidget(left_scroll, stretch=1)


        # ── RIGHT: Scrollable column ─────────────────────────────────────
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setStyleSheet("background: transparent;")
        
        right_col_widget = QWidget()
        right_col = QVBoxLayout(right_col_widget)
        right_col.setContentsMargins(5, 0, 0, 0)
        right_col.setSpacing(4)
        right_scroll.setWidget(right_col_widget)
        
        _grp_style = (
            f"QGroupBox {{ font-weight: bold; color: {COLORS['primary']};"
            f" border: 1px solid {COLORS['border']}; border-radius:6px;"
            f" margin-top:8px; padding-top:8px; background:{COLORS['surface']}; }}"
            f" QGroupBox::title {{ subcontrol-origin: margin; left:10px; padding: 0 4px; }}"
        )

        # ── Section 1: Key Metrics ────────────────────────────────────────
        calcs_group = QGroupBox("METRICAS CLAVE")
        calcs_group.setStyleSheet(_grp_style)
        calcs_form = QGridLayout(calcs_group)
        calcs_form.setVerticalSpacing(6)
        calcs_form.setHorizontalSpacing(12)

        def _metric_row(grid, row, icon, label_text, attr_name, val_color=None):
            lbl_name = QLabel(f"{icon}  {label_text}")
            lbl_name.setStyleSheet(f"color: {COLORS['text_dim']}; font-size:12px; background:transparent;")
            lbl_val = QLabel("--")
            c = val_color if val_color else COLORS.get('text_main', 'white')
            lbl_val.setStyleSheet(f"font-size:14px; font-weight:bold; padding:2px 6px; color:{c}; background:transparent;")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(lbl_name, row, 0)
            grid.addWidget(lbl_val,  row, 1)
            setattr(self, attr_name, lbl_val)

        _metric_row(calcs_form, 0, "Spread",      "Spread Mercado",   "lbl_m_spread")
        _metric_row(calcs_form, 1, "IRR-E",       "IRR Entrada",      "lbl_m_irr_entry",  COLORS.get('accent', '#FF9800'))
        _metric_row(calcs_form, 2, "IRR-M",       "IRR Mercado",      "lbl_m_irr_market", COLORS.get('primary','#9B59B6'))
        _metric_row(calcs_form, 3, "EV%",         "EV Ponderado %",   "lbl_m_ev_pct")
        _metric_row(calcs_form, 4, "EV$",         "EV Precio",        "lbl_m_ev_price")
        _metric_row(calcs_form, 5, "Dias",        "Dias al Cierre",   "lbl_m_days")
        _metric_row(calcs_form, 6, "R/R",         "Risk / Reward",    "lbl_m_rr")
        _metric_row(calcs_form, 7, "No-Deal",     "IRR si No-Deal",   "lbl_m_irr_nodeal", COLORS.get('danger','#E74C3C'))
        _metric_row(calcs_form, 8, "BFee",        "Break Fee Signal", "lbl_m_breakfee")
        right_col.addWidget(calcs_group)

        # ── Section 2: Scenarios Bear / Base / Bull ──────────────────────
        scen_group = QGroupBox("ESCENARIOS  Bear | Base | Bull")
        scen_group.setStyleSheet(_grp_style)
        scen_layout_v = QVBoxLayout(scen_group)
        scen_layout_v.setContentsMargins(5, 5, 5, 5)
        scen_layout_v.setSpacing(4)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("      "))
        for txt, color in [("BEAR","#E74C3C"),("BASE",COLORS.get('primary','#9B59B6')),("BULL","#2ECC71")]:
            h = QLabel(txt)
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.setStyleSheet(f"color:{color}; font-weight:bold; font-size:12px; background:transparent;")
            hdr.addWidget(h)
        scen_layout_v.addLayout(hdr)

        def _scen_spin(default_val, decimals=2):
            sb = QDoubleSpinBox()
            sb.setRange(0, 999999)
            sb.setDecimals(decimals)
            sb.setValue(default_val)
            sb.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            sb.setStyleSheet(f"background:{COLORS['surface_light']}; color:white; border:1px solid {COLORS['border']}; padding:3px; border-radius:3px;")
            sb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return sb

        for row_label, row_attrs, defaults in [
            ("Precio", ["scen_bear_price","scen_base_price","scen_bull_price"], [0, 0, 0]),
            ("Prob %", ["scen_bear_prob", "scen_base_prob", "scen_bull_prob"],  [20, 65, 15]),
        ]:
            r = QHBoxLayout()
            lb = QLabel(row_label)
            lb.setStyleSheet(f"color:{COLORS['text_dim']}; font-size:11px; min-width:55px; background:transparent;")
            r.addWidget(lb)
            dec = 0 if "Prob" in row_label else 2
            for attr, default in zip(row_attrs, defaults):
                w = _scen_spin(default, dec)
                
                def make_handler(current_attr=attr):
                    def handler():
                        if "prob" in current_attr:
                            self._sync_probabilities(current_attr)
                        self.update_scenario_irrs()
                        self._save_inline_params()
                    return handler

                w.valueChanged.connect(make_handler())
                setattr(self, attr, w)
                r.addWidget(w)
            scen_layout_v.addLayout(r)

        irr_row = QHBoxLayout()
        lb_irr = QLabel("IRR %")
        lb_irr.setStyleSheet(f"color:{COLORS['text_dim']}; font-size:11px; min-width:55px; background:transparent;")
        irr_row.addWidget(lb_irr)
        for attr, color in [("lbl_scen_bear_irr","#E74C3C"),("lbl_scen_base_irr",COLORS.get('primary','#9B59B6')),("lbl_scen_bull_irr","#2ECC71")]:
            lbl = QLabel("--")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"font-size:13px; font-weight:bold; color:{color}; background:transparent;")
            setattr(self, attr, lbl)
            irr_row.addWidget(lbl)
        scen_layout_v.addLayout(irr_row)
        right_col.addWidget(scen_group)

        # ── Section 3: Outside Date urgency bar ──────────────────────────
        od_group = QGroupBox("OUTSIDE DATE / PLAZO MAXIMO")
        od_group.setStyleSheet(_grp_style)
        od_layout = QVBoxLayout(od_group)
        od_layout.setSpacing(4)
        self.lbl_outside_date = QLabel("No definida")
        self.lbl_outside_date.setStyleSheet(f"font-size:13px; color:white; background:transparent;")
        self.lbl_outside_days = QLabel("")
        self.lbl_outside_days.setStyleSheet(f"font-size:11px; color:{COLORS['text_dim']}; background:transparent;")
        self.od_bar = QFrame()
        self.od_bar.setFixedHeight(8)
        self.od_bar.setStyleSheet("background-color: #555; border-radius:4px;")
        od_layout.addWidget(self.lbl_outside_date)
        od_layout.addWidget(self.lbl_outside_days)
        od_layout.addWidget(self.od_bar)
        right_col.addWidget(od_group)

        # ── Section 4: Compact File Upload ──────────────────────────
        _grp_style_light = (
            f"QGroupBox {{ font-weight: bold; color: {COLORS['primary']};"
            f" border: 1px solid {COLORS['border']}; border-radius:6px;"
            f" margin-top:8px; padding-top:8px; background:{COLORS['surface_light']}; }}"
            f" QGroupBox::title {{ subcontrol-origin: margin; left:10px; padding: 0 4px; }}"
        )
        self.compact_files_container = QGroupBox("FILE UPLOAD & TRACKING")
        right_col.addStretch()
        layout.addWidget(right_scroll, stretch=1)
        self.dynamic_widgets = {}

    def _sync_probabilities(self, changed_attr):
        """Forces the probabilities of target to sum to 100% when one is changed."""
        # Unhook signals to avoid recursive infinite loop
        w_bear = self.scen_bear_prob
        w_base = self.scen_base_prob
        w_bull = self.scen_bull_prob
        
        w_bear.blockSignals(True)
        w_base.blockSignals(True)
        w_bull.blockSignals(True)
        
        v_bear = w_bear.value()
        v_base = w_base.value()
        v_bull = w_bull.value()
        
        # We find out which ones were NOT explicitly changed, and balance them out
        if changed_attr == "scen_bear_prob":
            remaining = max(0, 100 - v_bear)
            # Try to proportion it or just give to base
            w_bull.setValue(min(v_bull, remaining))
            w_base.setValue(remaining - w_bull.value())
            
        elif changed_attr == "scen_base_prob":
            remaining = max(0, 100 - v_base)
            w_bear.setValue(min(v_bear, remaining))
            w_bull.setValue(remaining - w_bear.value())
            
        elif changed_attr == "scen_bull_prob":
            remaining = max(0, 100 - v_bull)
            w_base.setValue(min(v_base, remaining))
            w_bear.setValue(remaining - w_base.value())
            
        w_bear.blockSignals(False)
        w_base.blockSignals(False)
        w_bull.blockSignals(False)
        
    def load_sidebar(self):
        self.situations_list.clear()
        situations = self.manager.get_all_situations()
        filter_status = self.filter_combo.currentText()

        # Store all situations for navigation combo (regardless of filter)
        self._all_situations = situations

        # Grouping Logic
        groups = {}
        status_order = ["Pipeline", "Active", "Basic", "Closed"]

        for s in situations:
            st = s.get('status', 'Pipeline')
            found_key = "Other"
            for k in status_order:
                if k.lower() == st.lower():
                    found_key = k
                    break
            if found_key == "Other" and st not in groups:
                status_order.append(st)
                found_key = st
            if found_key not in groups: groups[found_key] = []
            groups[found_key].append(s)

        if filter_status == "All Status":
            for key in status_order:
                if key not in groups: continue
                for s in groups[key]:
                    self._add_tree_item(s, None)
        else:
            target_items = [s for s in situations if s.get('status', '') == filter_status]
            for s in target_items:
                self._add_tree_item(s, None)

        # Update nav combo in header
        self.header_widget.populate_nav_combo(
            [{'id': s['id'], 'title': s['title']} for s in situations],
            self.current_situation_id
        )

    def _navigate_to_situation(self, situation_id):
        """Select a situation by ID (called from nav combo in header)."""
        all_items = []
        root = self.situations_list.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            all_items.append(item)
            for j in range(item.childCount()):
                all_items.append(item.child(j))

        for item in all_items:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('id') == situation_id:
                self.situations_list.setCurrentItem(item)
                self.on_situation_selected(item)
                return

        # If not in tree (filtered out), load directly from manager
        fresh = self.manager.get_situation(situation_id)
        if fresh:
            self.current_situation_id = fresh['id']
            self.current_data = fresh
            self.empty_label.hide()
            self.content_container.show()
            self.header_widget.update_data(fresh)
            self.render_dynamic_inputs(fresh.get('strategy_type'), fresh.get('specific_data', {}))
            self.update_calculations()
            self.load_timeline_widget(fresh)
            self.load_library_widget(fresh)
            self.load_notes_widgets(fresh)
            self.tab_checklist.load_data(fresh)
            # Refresh combo selection
            self.header_widget.populate_nav_combo(
                [{'id': s['id'], 'title': s['title']} for s in self._all_situations],
                situation_id
            )



    def _add_tree_item(self, s, parent):
        str_cols = [''] # Empty text because we use a custom widget overlay
        item = QTreeWidgetItem(parent, str_cols) if parent else QTreeWidgetItem(self.situations_list, str_cols)
        item.setData(0, Qt.ItemDataRole.UserRole, s)
        
        # Widget
        title = s['title']
        cat = s.get('strategy_type', 'Generic') 
        status = s.get('status', 'Pipeline')
        
        widget = SituationSidebarItemWidget(title, f"[{cat}]", status)
        self.situations_list.setItemWidget(item, 0, widget)


    def load_timeline_widget(self, data):
        # Clear old
        if self.tab_timeline_layout.count() > 0:
            for i in reversed(range(self.tab_timeline_layout.count())):
                 w = self.tab_timeline_layout.itemAt(i).widget()
                 if w: w.deleteLater()
            
        self.timeline_widget = SituationTimelineWidget(data, parent=self)
        self.timeline_widget.special_situations_widget = self # Direct reference for persistence
        self.tab_timeline_layout.addWidget(self.timeline_widget)

    def load_library_widget(self, data):
        """Load or reload the SituationLibraryWidget into the Documents tab with robust layout detection."""
        import datetime as _dt
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'debug_docs.log')
        
        def _log(msg):
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(f"{_dt.datetime.now()} | {msg}\n")
            except: pass
        
        _log(f"--- load_library_widget called for '{data.get('title')}' ---")
        
        # 1. Check container widget
        tab_doc = getattr(self, 'tab_documents', None)
        if tab_doc is None:
            _log("FATAL: tab_documents widget itself is missing!")
            return
            
        # 2. Get the layout (native find)
        layout = tab_doc.layout()
        if layout is None:
            _log("Layout was None on widget! Creating a fresh one now.")
            layout = QVBoxLayout(tab_doc)  # Auto-recreate
            self.tab_documents_layout = layout # Sync back
        else:
            _log(f"Layout detected: {type(layout).__name__} with {layout.count()} items.")
            
        try:
            # 3. Clear old widgets
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()
            
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            # 4. Create and add the new library widget
            _log(f"Creating SituationLibraryWidget for ID={data.get('id')}")
            lib_w = SituationLibraryWidget(data, compact=False, parent=self)
            lib_w.setMinimumHeight(400) # Ensure visibility
            layout.addWidget(lib_w)
            
            _log(f"OK: success loading Document tab. Library widget sizeHint={lib_w.sizeHint()}")
            
            # Save reference
            self.library_widget = lib_w
                
        except Exception as e:
            import traceback
            _log(f"EXCEPTION in Documents load: {e}\n{traceback.format_exc()}")

    def load_notes_widgets(self, data):
        # Helper to clear and add
        def load_msg_widget(layout, key):
             if layout.count() > 0:
                for i in reversed(range(layout.count())):
                     w = layout.itemAt(i).widget()
                     if w: w.deleteLater()
             
             w = SituationNotesWidget(data, storage_key=key, parent=self)
             # CRITICAL: Set direct reference to bypass Qt parent issues
             w.special_situations_widget = self  
             layout.addWidget(w)

        load_msg_widget(self.tab_risks_layout, 'risks_log')
        load_msg_widget(self.tab_shareholders_layout, 'shareholders_log')
        load_msg_widget(self.tab_notes_layout, 'notes_log')


    def open_prompt_manager(self):
        if not self.current_data: return
        dlg = SituationPromptManagerDialog(self.current_data, parent=self)
        dlg.exec()
        # Updates are handled via save_situation_specific_data callback if triggered

    def save_situation_specific_data(self, sit_id, new_specific_data):
        """
        Callback for child widgets (SituationNotesWidget) to save specific data.
        Updates database and syncs in-memory cache.
        """
        print(f"[DEBUG] Saving specific_data for situation {sit_id}")
        print(f"[DEBUG] Keys in specific_data: {list(new_specific_data.keys())}")
        
        success = self.manager.update_situation(sit_id, specific_data=new_specific_data)
        
        if success:
            print(f"[DEBUG] Successfully saved to database")
            # Update local current_data cache
            if self.current_data and self.current_data['id'] == sit_id:
                self.current_data['specific_data'] = new_specific_data
                print(f"[DEBUG] Updated in-memory cache")
                self.data_changed.emit() # Notify others (like Calendar)
        else:
            print(f"[ERROR] Failed to save specific_data for situation {sit_id}")
            QMessageBox.warning(self, "Error", "Failed to save specific data.")
        
        return success

    def select_situation(self, sit_id):
        # Helper to find and select
        def find_and_select():
            iterator = QTreeWidgetItemIterator(self.situations_list)
            while iterator.value():
                item = iterator.value()
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get('id') == sit_id:
                    self.situations_list.setCurrentItem(item)
                    self.on_situation_selected(item, 0) # Force selection logic
                    return True
                iterator += 1
            return False

        if not find_and_select():
            print(f"[NAV] Situation {sit_id} not found in sidebar. Reloading...")
            self.load_sidebar()
            if not find_and_select():
                 print(f"[NAV] Setup failed: Situation {sit_id} still not found after reload.")

    def on_situation_selected(self, item, column=0):
        from core.crash_logger import log
        log("SpecialSituationsWidget.on_situation_selected triggered.")
        
        self.flush_pending_saves()
        
        print(f"[SpecialSituations] on_situation_selected triggered.")
        try:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if not data: 
                log("SpecialSituationsWidget: No data (Header?). Returning.")
                print("[SpecialSituations] No data (Header?). Returning.")
                return 
            
            log(f"SpecialSituationsWidget: Loading Data for ID: {data.get('id')}")
            print(f"[SpecialSituations] Loading Data for ID: {data.get('id')}")
            self.current_situation_id = data['id']
            self.current_data = data
            
            self.empty_label.hide()
            self.content_container.show()
            
            # New Header Update (Initial)
            self.current_live_prices = {}
            self.header_widget.update_data(data)
            
            # Get Yahoo tickers for price fetching
            spec_data = data.get('specific_data', {})

            yahoo_tickers = spec_data.get('yahoo_tickers', {})

            

            # Fetch prices if we have yahoo tickers

            if yahoo_tickers:

                self.fetch_live_data(yahoo_tickers)

            
            # Load Link Configuration
            spec_data = data.get('specific_data', {})
            link_config = spec_data.get('link_bar_config', {})
            self.link_bar.load_config(link_config)
            
            self.render_dynamic_inputs(data.get('strategy_type'), data.get('specific_data', {}))
            self._load_inline_params(data)
            self.update_calculations()

            # --- Load Sub-Widgets ---
            self.load_timeline_widget(data)
            self.load_library_widget(data)
            self.load_notes_widgets(data)
            self.tab_checklist.load_data(data)

            # Update navigation combo
            self.header_widget.populate_nav_combo(
                [{'id': s['id'], 'title': s['title']} for s in self._all_situations],
                data['id']
            )


        except Exception as e:
            print(f"Error selecting situation: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Error loading situation: {str(e)}")




    def fetch_live_data(self, tickers):
        # Do not terminate existing worker as it's unsafe with imports/SSL
        # Instead use fetch_id to invalidate old results
        self.fetch_id += 1
        current_req = self.fetch_id
        
        # We start a NEW worker. The old one will die naturally.
        # Python's GC will clean up the thread object eventually, 
        # or we can rely on finished.connect(self.price_worker.deleteLater) if we kept ref locally inside function
        
        worker = PriceWorker(current_req, tickers, {}) 
        # Connect to slot
        worker.finished.connect(self.on_prices_loaded)
        # Ensure cleanup
        worker.finished.connect(worker.deleteLater)
        
        # Keep ref to prevent premature GC (though run loop typically keeps it alive)
        self.price_worker = worker 
        worker.start()
        
    def on_prices_loaded(self, req_id, updates, raw_prices):
        # Check if this is the latest request
        if req_id != self.fetch_id:
             return # Ignore old result
             
        if not self.current_data: return
        
        # Prevent modification of the same dict
        safe_raw_prices = dict(raw_prices)
        
        sdata = self.current_data.get('specific_data', {})
        currencies = sdata.get('currencies', {})
        tickers_dict = self.current_data.get('tickers_dict', {})
        yahoo_tickers = sdata.get('yahoo_tickers', {})
        
        # APPLY GLOBAL GBX to GBP FIX HERE
        # Convert pence to pounds *upfront* so calculations don't go crazy
        for role, ticker in tickers_dict.items():
            y_tick = yahoo_tickers.get(role, ticker)
            if y_tick in safe_raw_prices:
                c_code = currencies.get(role, 'USD').upper()
                if "GBP.X" in c_code or "GBX" in c_code or "PENCE" in c_code:
                    safe_raw_prices[y_tick] = safe_raw_prices[y_tick] / 100.0
                    
        # Merge new prices
        self.current_live_prices.update(safe_raw_prices)
        
        # Update specific_data logic (rights offering etc)
        if updates:
            changed = False
            for k, v in updates.items():
                if sdata.get(k, 0.0) == 0.0:
                    sdata[k] = v
                    changed = True
            
            # Additional logic for Rights Offering
            stype = self.current_data.get('strategy_type')
            if stype == "Rights Offerings":
                t_sym = tickers_dict.get('target')
                if t_sym and t_sym in safe_raw_prices:
                    if sdata.get('share_price', 0.0) == 0.0:
                        sdata['share_price'] = safe_raw_prices[t_sym]
                        changed = True
            
            if changed:
                self.current_data['specific_data'] = sdata
        
        # Update Header now that we have prices
        self.header_widget.update_data(self.current_data, self.current_live_prices)
        
        # Also refresh calculations panel if needed
        self.render_dynamic_inputs(self.current_data.get('strategy_type'), sdata)
        self.update_calculations()
        
        # Save fetched prices to database (V5.1)
        if self.current_situation_id and safe_raw_prices:
            prices_to_save = {}
            # Map roles to prices
            target_yahoo = yahoo_tickers.get('target')
            if target_yahoo and target_yahoo in safe_raw_prices:
                prices_to_save['target'] = safe_raw_prices[target_yahoo]

            acquirer_yahoo = yahoo_tickers.get('acquirer')
            if acquirer_yahoo and acquirer_yahoo in safe_raw_prices:
                prices_to_save['acquirer'] = safe_raw_prices[acquirer_yahoo]
            
            if prices_to_save:
                self.manager.update_situation_prices(self.current_situation_id, prices_to_save)
                print(f"[PRICE] Saved prices (converted if GBX) to DB: {prices_to_save}")



    def show_sidebar_context_menu(self, pos):
        item = self.situations_list.itemAt(pos)
        if not item: return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data: return # Header item
        menu = QMenu()
        edit_action = menu.addAction("Edit Situation")
        delete_action = menu.addAction("Delete Situation")
        
        action = menu.exec(self.situations_list.mapToGlobal(pos))
        
        if action == edit_action:
            self.open_edit_dialog(data)
        elif action == delete_action:
            self.delete_situation(data['id'])

    def on_time_logged(self, task_name):
        # Refresh current view if the pomodoro log matches the open situation
        if not self.current_data: return
        self.flush_pending_saves()
        if self.current_data.get('title') == task_name or str(self.current_data.get('id')) == str(task_name):
            # reload data for current situation
            fresh_data = self.manager.get_situation(self.current_situation_id)
            if fresh_data:
                self.current_data = fresh_data
                if hasattr(self, 'header_widget'):
                    self.header_widget.update_data(fresh_data, self.current_live_prices)
                self.data_changed.emit()

    def select_situation(self, sit_id):
        from core.crash_logger import log
        log(f"SpecialSituationsWidget.select_situation called for ID {sit_id}")

        """Programmatically select a situation by ID."""
        print(f"[SpecialSituations] Attempting to select ID: {sit_id}")
        try:
            iterator = QTreeWidgetItemIterator(self.situations_list)
            while iterator.value():
                item = iterator.value()
                data = item.data(0, Qt.ItemDataRole.UserRole)
                
                # Check if this item holds the situation Data
                if data and isinstance(data, dict) and str(data.get('id')) == str(sit_id):
                    log(f"SpecialSituationsWidget: Found item for ID {sit_id}")
                    print(f"[SpecialSituations] Found item for ID {sit_id}")
                    
                    # Expand Parent if needed
                    parent = item.parent()
                    if parent: parent.setExpanded(True)
                    
                    # Select
                    log("SpecialSituationsWidget: Setting current item...")
                    self.situations_list.setCurrentItem(item)
                    self.situations_list.scrollToItem(item)
                    log("SpecialSituationsWidget: Calling on_situation_selected...")
                    self.on_situation_selected(item, 0) # Force trigger
                    log("SpecialSituationsWidget: on_situation_selected returned.")
                    return
                
                iterator += 1
            print(f"[SpecialSituations] ID {sit_id} not found in sidebar.")
            log(f"SpecialSituationsWidget: ID {sit_id} not found.")
        except Exception as e:
            log(f"SpecialSituationsWidget: CRASH in select_situation: {e}")
            print(f"[CRASH PREVENTION] Error during select_situation: {e}")
            import traceback
            traceback.print_exc()

    def delete_situation(self, sit_id):
        confirm = QMessageBox.question(self, "Confirm Delete", 
                                       "Are you sure you want to delete this situation?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            if self.manager.delete_situation(sit_id):
                 self.load_sidebar()
            else:
                 QMessageBox.warning(self, "Error", "Failed to delete situation.")
            
    def open_add_dialog(self):
        wizard = AddSituationWizard(self)
        if wizard.exec():
            # SUCCESS
            new_id = getattr(wizard, 'created_id', None)
            new_status = getattr(wizard, 'created_status', "Pipeline") # We will also capture status
            
            # 1. Check Filter
            current_filter = self.filter_combo.currentText()
            if current_filter != "All Status" and current_filter != new_status:
                self.filter_combo.setCurrentText("All Status") # Force visibility
            
            self.load_sidebar()
            
            # 2. Select the new item
            if new_id:
                iterator = QTreeWidgetItemIterator(self.situations_list)
                while iterator.value():
                    item = iterator.value()
                    data = item.data(0, Qt.ItemDataRole.UserRole)
                    if data and data.get('id') == new_id:
                        self.situations_list.setCurrentItem(item)
                        self.on_situation_selected(item, 0)
                        break
                    iterator += 1
            
            self.data_changed.emit() # Notify other views

    def open_edit_dialog(self, data):
        wizard = AddSituationWizard(self, edit_data=data)
        if wizard.exec():
            self.load_sidebar()
            
            # REFRESH CURRENT VIEW IF EDITED
            if self.current_situation_id == data['id']:
                 # Re-fetch fresh data from manager
                 fresh_data = self.manager.get_situation(self.current_situation_id)
                 if fresh_data:
                     self.current_data = fresh_data
                     
                     # 1. Update Header
                     # prices might be empty if we don't refetch, but we should pass what we have or trigger fetch
                     self.header_widget.update_data(fresh_data, self.current_live_prices)
                     
                     # 2. Update Tickers (Live Fetch?)
                     new_tickers = fresh_data.get('tickers_dict', fresh_data.get('tickers', {}))
                     self.fetch_live_data(new_tickers)
                     
                     # 3. Update Inputs/Calculations
                     self.render_dynamic_inputs(fresh_data.get('strategy_type'), fresh_data.get('specific_data', {}))
                     self.update_calculations()
            
            self.data_changed.emit() # Notify other views

    # --- Calculation & Logic Sync (Same as previous step but adapted) ---
    def render_dynamic_inputs(self, strategy_type, specific_data):
        # Determine visibility of classic binary parameters
        is_ma = strategy_type in ["Merger Arbitrage (Cash)", "Merger Arbitrage (Stock)", "Going Private (LBO)", "Tender Offer / Dutch Auction"]
        if hasattr(self, 'grp_dp'):
            self.grp_dp.setVisible(is_ma)

        # 1. Clear existing inputs thoroughly
        while self.inputs_layout.count():
            item = self.inputs_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout:
                    while sub_layout.count():
                        sub_item = sub_layout.takeAt(0)
                        sub_widget = sub_item.widget()
                        if sub_widget: sub_widget.deleteLater()
                    sub_layout.deleteLater()

        self.dynamic_widgets = {}
        
        # 2. Get Custom Defs (User Added)
        custom_defs = specific_data.get('custom_attributes', [])
        
        row = 0
        if not custom_defs:
            self.inputs_layout.addWidget(QLabel("No specific attributes added."), row, 0, 1, 2)
            row += 1
        else:
            for attr in custom_defs:
                name = attr.get('name', '')
                # Handle legacy keys if they still exist
                if not name and 'label' in attr:
                    name = attr['label']
                    
                val = str(attr.get('value', specific_data.get(attr.get('key', ''), '')))
                
                lbl_name = QLabel(f"{name}:")
                lbl_name.setWordWrap(True)
                lbl_name.setStyleSheet(f"color: {COLORS['text_dim']}; font-weight: bold;")
                
                lbl_val = QLabel(val)
                lbl_val.setWordWrap(True)
                lbl_val.setStyleSheet(f"color: white;")
                
                self.inputs_layout.addWidget(lbl_name, row, 0)
                self.inputs_layout.addWidget(lbl_val, row, 1)
                row += 1
                
        # 3. Add Custom Attribute Button (At Bottom)
        btn_edit = QPushButton("✎ Edit Attributes")
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setStyleSheet(f"background-color: {COLORS['surface_light']}; border: 1px dashed {COLORS['primary']}; color: {COLORS['primary']}; padding: 6px; border-radius: 4px; font-weight: bold;")
        btn_edit.clicked.connect(self.edit_custom_attributes)
        self.inputs_layout.addWidget(btn_edit, row, 0, 1, 2)

    def on_input_changed(self):
        """Auto-save inputs and recalculate."""
        if not self.current_data: return

        new_data = self.current_data.get('specific_data', {}).copy()

        for key, widget in self.dynamic_widgets.items():
            if isinstance(widget, QDoubleSpinBox):
                new_data[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                new_data[key] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                new_data[key] = widget.text()
            elif isinstance(widget, QDateEdit):
                new_data[key] = widget.date().toString("yyyy-MM-dd")

        self.manager.update_situation(self.current_situation_id, specific_data=new_data)
        self.current_data['specific_data'] = new_data
        self.update_calculations()

    def _save_inline_params(self):
        """Auto-save the Timeline / Deal Parameters / Financials inline fields."""
        if not self.current_data:
            return

        sdata = self.current_data.get('specific_data', {}).copy()

        # Timeline
        sdata['start_date']    = self.ip_start_date.text().strip()
        sdata['target_date']   = self.ip_end_date.text().strip()

        # Deal Parameters
        sdata['outside_date']      = self.ip_outside_date.text().strip()
        sdata['close_probability'] = int(self.ip_close_prob.value())
        sdata['break_fee_pct']     = round(self.ip_break_fee.value(), 2)

        # Financials
        sdata['entry_price']    = round(self.ip_entry_price.value(), 2)
        sdata['deal_value']     = round(self.ip_deal_value.value(), 2)
        sdata['downside_price'] = round(self.ip_downside.value(), 2)
        sdata['capital']        = int(self.ip_capital.value())
        sdata['reinforce_price'] = round(self.ip_reinforce.value(), 2)
        sdata['reduce_price']    = round(self.ip_reduce.value(), 2)

        # Scenarios
        sdata['scenario_bear'] = {'price': self.scen_bear_price.value(), 'prob': self.scen_bear_prob.value()}
        sdata['scenario_base'] = {'price': self.scen_base_price.value(), 'prob': self.scen_base_prob.value()}
        sdata['scenario_bull'] = {'price': self.scen_bull_price.value(), 'prob': self.scen_bull_prob.value()}

        # Save to memory immediately for instant calculator reactions
        self.current_data['specific_data'] = sdata
        self.current_data['start_date'] = sdata['start_date']
        self.current_data['target_date'] = sdata['target_date']
        self.current_data['entry_price'] = float(sdata.get('entry_price', 0))
        self.current_data['deal_value'] = float(sdata.get('deal_value', 0))
        self.current_data['probability'] = float(sdata.get('close_probability', 0))
        self.current_data['capital_allocated'] = float(sdata.get('capital', 0))
        
        # Recalculate instantly
        self.update_calculations()
        
        # Debounce to database to avoid I/O freezing
        if hasattr(self, 'save_timer'):
            self.save_timer.start()

    def _save_inline_params_to_db(self):
        """Actual I/O saving triggered by debounce timer."""
        if not self.current_data or not self.current_situation_id:
            return
            
        sdata = self.current_data.get('specific_data', {})
        
        # Make sure top-level DB columns are also updated to stay synced
        entry_price = float(sdata.get('entry_price', 0))
        deal_value = float(sdata.get('deal_value', 0))
        probability = float(sdata.get('close_probability', 0))
        capital = float(sdata.get('capital', 0))
        start_date = sdata.get('start_date', '')
        target_date = sdata.get('target_date', '')

        self.manager.update_situation(self.current_situation_id, 
                                      specific_data=sdata,
                                      start_date=start_date,
                                      target_date=target_date,
                                      entry_price=entry_price,
                                      deal_value=deal_value,
                                      probability=probability,
                                      capital_allocated=capital)
                                      
        self.data_changed.emit() # Notify global UI when data is actually saved

    def flush_pending_saves(self):
        """Forces any pending timer writes to process instantly."""
        if hasattr(self, 'save_timer') and self.save_timer.isActive():
            self.save_timer.stop()
            self._save_inline_params_to_db()

    def hideEvent(self, event):
        super().hideEvent(event)
        # Force flush any pending saves when user leaves the tab
        self.flush_pending_saves()

    def _load_inline_params(self, data):
        """Populate Timeline / Deal / Financials inline fields from situation data."""
        sdata = data.get('specific_data', {})

        # Block signals while loading
        for w in [self.ip_close_prob, self.ip_break_fee, self.ip_entry_price,
                  self.ip_deal_value, self.ip_downside, self.ip_capital,
                  self.ip_reinforce, self.ip_reduce]:
            w.blockSignals(True)
        for w in [self.ip_start_date, self.ip_end_date, self.ip_outside_date]:
            w.blockSignals(True)

        # Timeline
        self.ip_start_date.setText(str(sdata.get('start_date', '') or ''))
        self.ip_end_date.setText(str(sdata.get('target_date', '') or ''))

        # Deal Parameters
        self.ip_outside_date.setText(str(sdata.get('outside_date', '') or ''))
        try:    self.ip_close_prob.setValue(float(sdata.get('close_probability', 90) or 90))
        except: self.ip_close_prob.setValue(90)
        try:    self.ip_break_fee.setValue(float(sdata.get('break_fee_pct', 0) or 0))
        except: self.ip_break_fee.setValue(0)

        # Financials
        try:    self.ip_entry_price.setValue(float(sdata.get('entry_price', 0) or 0))
        except: self.ip_entry_price.setValue(0)
        try:    self.ip_deal_value.setValue(float(sdata.get('deal_value', 0) or 0))
        except: self.ip_deal_value.setValue(0)
        try:    self.ip_downside.setValue(float(sdata.get('downside_price', 0) or 0))
        except: self.ip_downside.setValue(0)
        try:    self.ip_capital.setValue(float(sdata.get('capital', 0) or 0))
        except: self.ip_capital.setValue(0)
        try:    self.ip_reinforce.setValue(float(sdata.get('reinforce_price', 0) or 0))
        except: self.ip_reinforce.setValue(0)
        try:    self.ip_reduce.setValue(float(sdata.get('reduce_price', 0) or 0))
        except: self.ip_reduce.setValue(0)

        # Scenarios
        scen_widgets = [self.scen_bear_price, self.scen_bear_prob, 
                        self.scen_base_price, self.scen_base_prob, 
                        self.scen_bull_price, self.scen_bull_prob]
        
        for w in scen_widgets:
            w.blockSignals(True)

        scen_bear = sdata.get('scenario_bear', {})
        self.scen_bear_price.setValue(float(scen_bear.get('price', 0)))
        self.scen_bear_prob.setValue(float(scen_bear.get('prob', 20)))

        scen_base = sdata.get('scenario_base', {})
        self.scen_base_price.setValue(float(scen_base.get('price', 0)))
        self.scen_base_prob.setValue(float(scen_base.get('prob', 65)))

        scen_bull = sdata.get('scenario_bull', {})
        self.scen_bull_price.setValue(float(scen_bull.get('price', 0)))
        self.scen_bull_prob.setValue(float(scen_bull.get('prob', 15)))

        for w in scen_widgets:
            w.blockSignals(False)

        # Restore signals
        for w in [self.ip_close_prob, self.ip_break_fee, self.ip_entry_price,
                  self.ip_deal_value, self.ip_downside, self.ip_capital,
                  self.ip_reinforce, self.ip_reduce]:
            w.blockSignals(False)
        for w in [self.ip_start_date, self.ip_end_date, self.ip_outside_date]:
            w.blockSignals(False)

    def edit_custom_attributes(self):
        sdata = self.current_data.get('specific_data', {})
        customs = sdata.get('custom_attributes', [])
        
        # Legacy migration check
        migrated = []
        for c in customs:
            if 'label' in c and 'name' not in c:
                migrated.append({"name": c['label'], "value": sdata.get(c['key'], "")})
            else:
                migrated.append(c)
                
        dlg = EditAttributesDialog(migrated, self)
        if dlg.exec():
            new_attrs = dlg.get_data()
            sdata['custom_attributes'] = new_attrs
            
            # Persist immediately
            self.manager.update_situation(self.current_situation_id, specific_data=sdata)
            self.current_data['specific_data'] = sdata
            
            # Refresh
            self.render_dynamic_inputs(self.current_data.get('strategy_type'), sdata)

    def update_sensitivity(self):
        """Legacy compat: no-op now, kept because slots may reference it."""
        self.update_calculations()

    def update_scenario_irrs(self):
        """Recalculates IRR readouts for scenario spinboxes."""
        if not self.current_data:
            return
        current_market = self.current_data.get('entry_price', 0.0) or 0.0
        prices = getattr(self, 'current_live_prices', {})
        tickers = self.current_data.get('tickers_dict', {})
        main_ticker = tickers.get('target', '')
        if main_ticker and main_ticker in prices:
            current_market = prices[main_ticker]
        t_date = self.current_data.get('target_date')
        if not t_date:
            t_date = self.current_data.get('specific_data', {}).get('target_date')
            
        import datetime as _dt
        today = _dt.date.today()
        if isinstance(t_date, _dt.datetime):
            t_date = t_date.date()
        elif isinstance(t_date, str) and t_date:
            parsed = None
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    parsed = _dt.datetime.strptime(t_date, fmt).date()
                    break
                except ValueError:
                    pass
            t_date = parsed if parsed else today
        if not t_date:
            t_date = today
        days = (t_date - today).days

        for scen, lbl_attr in [("bear", "lbl_scen_bear_irr"),
                               ("base", "lbl_scen_base_irr"),
                               ("bull", "lbl_scen_bull_irr")]:
            price_w = getattr(self, f"scen_{scen}_price", None)
            lbl_w   = getattr(self, lbl_attr, None)
            if not price_w or not lbl_w:
                continue
            s_price = price_w.value()
            if current_market > 0 and s_price > 0:
                irr = calculate_scenario_irr(s_price, current_market, days)
                print(f"[DEBUG SCENARIO] {scen}: s_price={s_price}, current_market={current_market}, days={days}, t_date={t_date}, irr={irr}")
                lbl_w.setText(f"{irr:+.1f}%")
            else:
                lbl_w.setText("--")

    def _update_outside_date_bar(self, sdata, target_date):
        """Updates the outside date urgency bar in the Analysis tab."""
        od_str = sdata.get('outside_date', None)
        if not od_str:
            self.lbl_outside_date.setText("No definida")
            self.lbl_outside_days.setText("")
            self.od_bar.setStyleSheet("background-color:#555; border-radius:4px;")
            return
        import datetime as _dt
        today = _dt.date.today()
        try:
            od = _dt.datetime.strptime(str(od_str), "%Y-%m-%d").date()
        except:
            self.lbl_outside_date.setText(str(od_str))
            self.lbl_outside_days.setText("")
            return
        days_od = (od - today).days
        # Determine reference start (target_date or today)
        t_date = target_date
        if isinstance(t_date, _dt.datetime):
            t_date = t_date.date()
        elif isinstance(t_date, str) and t_date:
            parsed = None
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    parsed = _dt.datetime.strptime(t_date, fmt).date()
                    break
                except ValueError:
                    pass
            t_date = parsed if parsed else today
        total_window = max(1, (od - (t_date or today)).days)
        # Fraction elapsed = how much of the window has passed
        elapsed = max(0, (today - (t_date or today)).days)
        pct = min(100, int(elapsed / total_window * 100))
        # Color: green -> orange -> red as urgency grows
        if days_od > 90:
            bar_color = "#2ECC71"
        elif days_od > 30:
            bar_color = "#FF9800"
        else:
            bar_color = "#E74C3C"
        self.lbl_outside_date.setText(f"Outside Date: {od.strftime('%d-%m-%Y')}")
        if days_od >= 0:
            self.lbl_outside_days.setText(f"{days_od} dias restantes hasta el plazo limite")
        else:
            self.lbl_outside_days.setText(f"VENCIDA hace {abs(days_od)} dias")
            bar_color = "#E74C3C"
        fill_pct = max(4, min(100, pct))
        self.od_bar.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {bar_color}, stop:{fill_pct/100:.2f} {bar_color}, "
            f"stop:{min(fill_pct/100+0.01,1):.2f} #333, stop:1 #333);"
            f"border-radius:4px;"
        )

    def update_calculations(self):
        if not self.current_data:
            return

        prices = getattr(self, 'current_live_prices', {})
        core = self.service.calculate_metrics(self.current_data, prices)

        if 'error' in core:
            return
            
        target_implied = core.get('target_implied', 0.0)
        downside = core.get('downside', 0.0)
        sdata = self.current_data.get('specific_data', {})
        t_date = self.current_data.get('target_date')

        def _fmt_irr(v):
            color = "#2ECC71" if v >= 0 else "#E74C3C"
            return f"<span style='color:{color}'>{v:+.1f}%</span>"

        # Update 9 metric labels
        self.lbl_m_spread.setText(f"{core['spread_pct']:+.2f}%")
        self.lbl_m_irr_entry.setText(_fmt_irr(core['irr_entry']))
        self.lbl_m_irr_entry.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_m_irr_market.setText(_fmt_irr(core['irr_market']))
        self.lbl_m_irr_market.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_m_ev_pct.setText(f"{core['ev_weighted_pct']:+.2f}%")
        self.lbl_m_ev_price.setText(f"{core['ev_price']:.2f}")
        self.lbl_m_days.setText(str(core['days_to_close']))
        rr = core['risk_reward']
        self.lbl_m_rr.setText(f"{rr:.2f}x" if rr else "--")
        self.lbl_m_irr_nodeal.setText(_fmt_irr(core['irr_no_deal']))
        self.lbl_m_irr_nodeal.setTextFormat(Qt.TextFormat.RichText)
        bfs = core['break_fee_signal']
        self.lbl_m_breakfee.setText(f"{bfs:.2f}x" if bfs else "--")

        # Seed scenario spinboxes with deal price as base if they are 0
        if target_implied > 0:
            if self.scen_base_price.value() == 0:
                self.scen_base_price.setValue(round(target_implied, 2))
            if self.scen_bear_price.value() == 0 and downside > 0:
                self.scen_bear_price.setValue(round(downside, 2))
            if self.scen_bull_price.value() == 0:
                self.scen_bull_price.setValue(round(target_implied * 1.02, 2))
        self.update_scenario_irrs()

        # Outside Date bar
        self._update_outside_date_bar(sdata, t_date)

        # Update header
        spread_txt = f"{core['spread_pct']:+.2f}%"
        irr_txt = f"{core['irr_market']:+.1f}%"
        self.header_widget.update_data(self.current_data, prices, spread_txt, irr_txt)


    def save_link_config(self, full_config):
        if self.current_situation_id and self.current_data:
            spec_data = self.current_data.get('specific_data', {})
            spec_data['link_bar_config'] = full_config
            self.manager.update_situation(self.current_situation_id, specific_data=spec_data)
            self.current_data['specific_data'] = spec_data # Update local cache

    def open_local_folder(self):
        QMessageBox.information(self, "Info", "Folder integration pending.")
        
    
# --- HELPERS ---


# --- WIZARD ---
from PyQt6.QtWidgets import QFormLayout

