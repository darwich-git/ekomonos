from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox,
    QVBoxLayout, QScrollArea, QWidget, QGroupBox, QDoubleSpinBox,
    QPushButton, QMessageBox, QHBoxLayout, QSlider, QLabel, QFrame, QCompleter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from ui.styles import COLORS
from core.services import SpecialService
from core.special_definitions import SITUATION_CATEGORIES, resolve_type
from core.price_fetcher import EXCHANGE_SUFFIXES

class NoScrollComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        event.ignore()
class SituationSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Special Situations Settings")
        self.resize(350, 200)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']};")
        
        layout = QFormLayout(self)
        
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(5, 30) # 0.5x to 3.0x
        self.sensitivity_slider.setValue(10) # 1.0x
        self.lbl_sens = QLabel("1.0x")
        self.sensitivity_slider.valueChanged.connect(lambda v: self.lbl_sens.setText(f"{v/10:.1f}x"))
        
        layout.addRow("Prob. Sensitivity:", self.lbl_sens)
        layout.addRow(self.sensitivity_slider)
        
        self.base_prob_edit = QLineEdit("92")
        layout.addRow("Base Prob (Merger) %:", self.base_prob_edit)
        
        btn_box = QHBoxLayout()
        btn_save = QPushButton("Save Settings")
        btn_save.setStyleSheet(f"background-color: {COLORS['primary']}; color: black;")
        btn_save.clicked.connect(self.accept)
        btn_box.addWidget(btn_save)
        layout.addRow(btn_box)

# Removed redundant SituationHeaderWidget (moved to components)
# --- Link Bar Widget ---
class AddAttributeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Strategy Attribute")
        self.resize(300, 200)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.inp_label = QLineEdit()
        self.inp_key = QLineEdit()
        self.inp_type = QComboBox()
        self.inp_type.addItems(["double", "bool", "text"]) # Simple types
        
        self.inp_label.textChanged.connect(self.auto_key)
        
        layout.addRow("Label Name:", self.inp_label)
        layout.addRow("Internal Key:", self.inp_key)
        layout.addRow("Data Type:", self.inp_type)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)
        
    def auto_key(self, text):
        # slugify
        key = text.lower().replace(" ", "_").replace("-", "_")
        key = "".join([c for c in key if c.isalnum() or c == "_"])
        self.inp_key.setText(key)

    def get_data(self):
        return {
            'label': self.inp_label.text(),
            'key': self.inp_key.text(),
            'type': self.inp_type.currentText()
        }

class AddSituationWizard(QDialog):
    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.edit_data = edit_data
        self.setWindowTitle("New Special Situation" if not edit_data else f"Edit Situation: {edit_data.get('title', '')}")
        # Standardized Size (Matches Company Wizard)
        self.resize(750, 850)
        self.setMinimumWidth(750)
        self.manager = SpecialService()
        self.created_id = None 
        self.created_status = None 
        
        self.setup_ui()
        if edit_data:
            self.load_data(edit_data)

    def setup_ui(self):
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['surface']}; color: {COLORS['text_main']}; font-family: 'Segoe UI', sans-serif; }}
            QGroupBox {{ 
                font-weight: bold; 
                color: {COLORS['primary']}; 
                border: 1px solid {COLORS['border']}; 
                margin-top: 15px; 
                padding-top: 15px; 
                border-radius: 6px; 
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px; }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button, 
            QSpinBox::up-button, QSpinBox::down-button {{ width: 0px; height: 0px; border: none; background: transparent; }}
            QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit {{ 
                background-color: {COLORS['surface_light']}; 
                border: 1px solid {COLORS['border']}; 
                border-radius: 4px; 
                padding: 6px; 
                color: {COLORS['text_main']}; 
            }}
            QLabel {{ font-size: 13px; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        layout.addWidget(scroll)
        
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setSpacing(15)
        scroll.setWidget(content)

        # Section 1: Classification
        grp_class = QGroupBox("Classification")
        form_class = QFormLayout(grp_class)
        form_class.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. Microsoft - Activision acquisition")
        form_class.addRow("Title:", self.title_edit)
        
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(SITUATION_CATEGORIES.keys())
        self.cat_combo.currentTextChanged.connect(self.on_category_changed)
        form_class.addRow("Category:", self.cat_combo)
        
        self.type_combo = QComboBox()
        self.type_combo.currentTextChanged.connect(self.on_subtype_changed)
        form_class.addRow("Subtype:", self.type_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Pipeline", "Active", "Closed"])
        form_class.addRow("Status:", self.status_combo)
        
        # New Field for Manual Hours
        self.hours_spin = QDoubleSpinBox()
        self.hours_spin.setRange(0, 999999)
        self.hours_spin.setDecimals(1)
        self.hours_spin.setSuffix(" h")
        form_class.addRow("Total Time Logged:", self.hours_spin)

        self.main_layout.addWidget(grp_class)
        
        # Section 2: Tickers (Logic)
        self.tickers_group = QGroupBox("Configuration (Internal Logic)")
        self.form_tickers = QFormLayout(self.tickers_group)
        self.main_layout.addWidget(self.tickers_group)
        self.ticker_inputs = {}
        # Section 3: Yahoo Finance (FETCHING)
        grp_yahoo = QGroupBox("Yahoo Finance (Price Fetching)")
        self.form_yahoo = QFormLayout(grp_yahoo)
        self.form_yahoo.setSpacing(8)
        
        # Lists for Searchable Combos
        exchanges = sorted(list(EXCHANGE_SUFFIXES.keys()))
        currencies = sorted([
            "USD - US Dollar", "EUR - Euro", "GBP - British Pound", "GBP.X - British Pence", "CAD - Canadian Dollar",
            "AUD - Australian Dollar", "JPY - Japanese Yen", "CHF - Swiss Franc",
            "CNY - Chinese Yuan", "HKD - HK Dollar", "SGD - Singapore Dollar",
            "INR - Indian Rupee", "BRL - Brazilian Real", "MXN - Mexican Peso",
            "PLN - Polish Zloty", "SEK - Swedish Krona", "NOK - Norwegian Krone",
            "DKK - Danish Krone", "ZAR - South African Rand", "TRY - Turkish Lira",
            "ILS - Israeli Shekel", "RUB - Russian Ruble", "KRW - South Korean Won",
            "TWD - New Taiwan Dollar", "SAR - Saudi Riyal", "AED - UAE Dirham"
        ])

        def create_searchable_combo(items):
            cb = NoScrollComboBox()
            cb.setEditable(True)
            cb.addItems(items)
            cb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            cb.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            cb.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            cb.setCurrentIndex(-1)
            return cb

        self.yahoo_target_edit = QLineEdit()
        self.yahoo_target_edit.setPlaceholderText("e.g. MSFT")
        self.exchange_target_combo = create_searchable_combo(exchanges)
        self.currency_target_combo = create_searchable_combo(currencies)
        self.currency_target_combo.currentTextChanged.connect(self.update_currency_symbols)
        
        self.form_yahoo.addRow("Target Yahoo Ticker:", self.yahoo_target_edit)
        self.form_yahoo.addRow("Target Exchange:", self.exchange_target_combo)
        self.form_yahoo.addRow("Target Currency:", self.currency_target_combo)
        
        # Acquirer Row
        self.yahoo_acquirer_edit = QLineEdit()
        self.yahoo_acquirer_edit.setPlaceholderText("Optional")
        self.exchange_acquirer_combo = create_searchable_combo(exchanges)
        self.currency_acquirer_combo = create_searchable_combo(currencies)
        
        self.form_yahoo.addRow("Acquirer Yahoo Ticker:", self.yahoo_acquirer_edit)
        self.form_yahoo.addRow("Acquirer Exchange:", self.exchange_acquirer_combo)
        self.form_yahoo.addRow("Acquirer Currency:", self.currency_acquirer_combo)
        
        self.main_layout.addWidget(grp_yahoo)

        

        
        # Initial Currency Sync (no financials section — all inline in Analysis tab)
        self.update_currency_symbols(self.currency_target_combo.currentText())
        
        # Final Buttons (Bottom)
        self.btn_save = QPushButton("Save Situation" if not self.edit_data else "Save Changes")
        self.btn_save.setMinimumHeight(45)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']}; 
                color: black; 
                font-weight: bold; 
                border-radius: 6px; 
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {QColor(COLORS['primary']).lighter(110).name()}; }}
        """)
        self.btn_save.clicked.connect(self.save)
        layout.addWidget(self.btn_save)

        # DELETE Button (Initially Hidden for Create, shown for Edit)
        self.btn_delete = QPushButton("DELETE SITUATION")
        self.btn_delete.setMinimumHeight(45)
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']}; 
                color: white; 
                font-weight: bold; 
                border-radius: 6px; 
                font-size: 14px;
                margin-top: 5px;
            }}
            QPushButton:hover {{ background-color: #c0392b; }}
        """)
        self.btn_delete.clicked.connect(self.delete_situation)
        if not self.edit_data:
            self.btn_delete.hide()
        layout.addWidget(self.btn_delete)

        # Cancel Button (Optional or small)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFlat(True)
        self.btn_cancel.setStyleSheet(f"color: {COLORS['text_dim']};")
        self.btn_cancel.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancel, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Initial Trigger
        self.on_category_changed(self.cat_combo.currentText())

    def on_category_changed(self, category):
        types = SITUATION_CATEGORIES.get(category, ["Generic"])
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        self.type_combo.addItems(types)
        self.type_combo.blockSignals(False)
        if types: self.on_subtype_changed(types[0])

    def on_subtype_changed(self, subtype):
        if not subtype: subtype = ""
        # Clear Layout
        while self.form_tickers.rowCount():
            self.form_tickers.removeRow(0)
        self.ticker_inputs = {}
        
        # Field Logic
        cat = self.cat_combo.currentText()
        fields = []
        
        # Matches based on Subtype analysis or Category
        if "Merger" in subtype or "M&A" in cat: 
            if "CVR" in subtype:
                 fields = [("Target Ticker", "target"), ("CVR Ticker (Opt)", "cvr")]
            else:
                 fields = [("Acquirer Ticker", "acquirer"), ("Target Ticker", "target")]
        
        elif "Special Dividend" in subtype:
             fields = [("Ticker Symbol", "target")]

        elif "Liquidations" in subtype:
             fields = [("Ticker Symbol", "target")]

        elif "Spin" in subtype or "Split" in subtype or "Spinoffs" in cat:
             fields = [("Parent Ticker", "parent"), ("SpinCo Ticker", "spinco")]
             
        elif "Arbitrage" in subtype:
             fields = [("Long Ticker", "long"), ("Short Ticker", "short")]
             
        else:
             fields = [("Ticker Symbol", "target")]
        
        for label, key in fields:
            inp = QLineEdit()
            self.form_tickers.addRow(label + ":", inp)
            self.ticker_inputs[key] = inp

        # Toggle Visibility
        show_acquirer = ("Merger" in subtype or "M&A" in cat)
        for w in [self.yahoo_acquirer_edit, self.exchange_acquirer_combo, self.currency_acquirer_combo]:
            self.form_yahoo.setRowVisible(w, show_acquirer)

    def load_data(self, data):
        self.title_edit.setText(data['title'])
        self.status_combo.setCurrentText(data.get('status', 'Pipeline'))
        
        # Load total hours
        total_seconds = data.get('total_seconds', 0)
        self.hours_spin.setValue(total_seconds / 3600.0)
        # Keep track of originally loaded seconds to compute difference on save
        self.original_seconds = total_seconds

        subtype = resolve_type(data.get('strategy_type', 'Generic'))
        found_cat = "Other"
        for cat, types in SITUATION_CATEGORIES.items():
            if subtype in types:
                found_cat = cat
                break
        self.cat_combo.setCurrentText(found_cat)
        self.type_combo.setCurrentText(subtype)

        tickers = data.get('tickers', {})
        for key, widget in self.ticker_inputs.items():
            if key in tickers:
                widget.setText(tickers[key])

        # Load Yahoo Finance data
        spec_data = data.get('specific_data', {})
        yt = spec_data.get('yahoo_tickers', {})
        ex = spec_data.get('exchanges', {})
        cu = spec_data.get('currencies', {})

        if 'target' in yt:   self.yahoo_target_edit.setText(yt['target'])
        if 'target' in ex:   self.exchange_target_combo.setCurrentText(ex['target'])
        if 'target' in cu:   self.currency_target_combo.setCurrentText(cu['target'])
        if 'acquirer' in yt: self.yahoo_acquirer_edit.setText(yt['acquirer'])
        if 'acquirer' in ex: self.exchange_acquirer_combo.setCurrentText(ex['acquirer'])
        if 'acquirer' in cu: self.currency_acquirer_combo.setCurrentText(cu['acquirer'])


    def update_currency_symbols(self, text=""):
        pass  # Financials now live in Analysis tab inline section

    def delete_situation(self):
        if not self.edit_data: return
        
        confirm = QMessageBox.question(self, "Risk of Data Loss", 
             f"Are you sure you want to PERMANENTLY DELETE current situation?\n\nThis action cannot be undone.",
             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
             
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                success = self.manager.delete_situation(self.edit_data['id'])
                if success:
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", "Could not delete situation.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Crash during delete: {e}")

    def save(self):
        try:
            tickers_data = {k: v.text() for k, v in self.ticker_inputs.items()}
            subtype = self.type_combo.currentText()
            status = self.status_combo.currentText()

            # --- 1. Prepare Base Params ---
            params = {
                "title": self.title_edit.text(),
                "strategy_type": subtype,
                "tickers": tickers_data,
                "status": status,
            }

            # --- 2. Preserve Existing Specific Data (do NOT overwrite inline params) ---
            current_specific = {}
            if self.edit_data:
                current_specific = self.edit_data.get('specific_data', {}).copy()

            # Yahoo Finance data
            yahoo_tickers = current_specific.get('yahoo_tickers', {})
            exchanges     = current_specific.get('exchanges', {})
            currencies    = current_specific.get('currencies', {})

            t_tick = self.yahoo_target_edit.text().strip()
            if t_tick:
                yahoo_tickers['target'] = t_tick
            else:
                yahoo_tickers.pop('target', None)

            exchanges['target']  = self.exchange_target_combo.currentText()
            currencies['target'] = self.currency_target_combo.currentText()

            a_tick = self.yahoo_acquirer_edit.text().strip()
            if a_tick:
                yahoo_tickers['acquirer'] = a_tick
            else:
                yahoo_tickers.pop('acquirer', None)

            exchanges['acquirer']  = self.exchange_acquirer_combo.currentText()
            currencies['acquirer'] = self.currency_acquirer_combo.currentText()

            current_specific['yahoo_tickers'] = yahoo_tickers
            current_specific['exchanges']     = exchanges
            current_specific['currencies']    = currencies
            params['specific_data'] = current_specific

            
            if self.edit_data:
                # Update
                self.manager.update_situation(self.edit_data['id'], **params)
                target_id = self.edit_data['id']
            else:
                # Create: Exploded args
                self.created_id = self.manager.add_situation(
                    title=params['title'],
                    event_type=status,
                    tickers_dict=params['tickers'],
                    strategy_type=params['strategy_type'],
                    status=status,
                    specific_data=params['specific_data']
                )
                self.created_status = status
                target_id = self.created_id

            # Handle Manual Hours Update (Log the difference)
            target_hours = self.hours_spin.value()
            target_secs = target_hours * 3600
            current_secs = getattr(self, 'original_seconds', 0)
            diff = target_secs - current_secs
            if abs(diff) > 10 and target_id:
                self.manager.log_time(target_id, int(diff))

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error Saving", f"Could not save situation:\n{str(e)}")
            print(f"Save Error: {e}")


