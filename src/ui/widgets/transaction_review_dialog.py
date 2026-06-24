from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QAbstractItemView)
from PyQt6.QtCore import Qt, QEvent
from ui.styles import COLORS

class TransactionReviewDialog(QDialog):
    def __init__(self, transactions, expected_cats, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Review Classifications")
        self.resize(800, 780)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['background']}; }}
            QLabel {{ color: {COLORS['text_main']}; font-size: 14px; font-weight: bold; }}
            QTableWidget {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_main']};
                gridline-color: {COLORS['border']};
                border: 1px solid {COLORS['border']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['text_main']};
                padding: 4px;
                border: 1px solid {COLORS['border']};
                font-weight: bold;
            }}
            QPushButton {{
                background-color: {COLORS['primary']};
                color: #000;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #45a049; }}
            QComboBox {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['text_main']};
                border: 1px solid {COLORS['border']};
                padding: 2px;
            }}
        """)
        
        
        self.layout = QVBoxLayout(self)
        
        lbl = QLabel("Review classifications.")
        self.layout.addWidget(lbl)
        
        self.cat_dict = expected_cats
        self.pending_key = ""
        
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Description", "Credit (+)", "Debit (-)", "Category"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 250) 
        self.layout.addWidget(self.table)
        
        # Install event filter to catch number keys
        self.table.installEventFilter(self)
        
        self.transactions = transactions
        self.combos = []
        
        self.populate_table()
        
        btn_layout = QHBoxLayout()
        self.lbl_balance = QLabel("")
        btn_layout.addWidget(self.lbl_balance)
        btn_layout.addStretch()
        
        self.btn_confirm = QPushButton("Confirm Classes")
        self.btn_confirm.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_confirm)
        self.layout.addLayout(btn_layout)

    def populate_table(self):
        self.table.setRowCount(len(self.transactions))
        for row, t in enumerate(self.transactions):
            self.table.setItem(row, 0, QTableWidgetItem(str(t.get('date', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(str(t.get('desc', ''))))
            
            c_val = f"£{t.get('credit', 0):.2f}" if t.get('credit', 0) > 0 else ""
            d_val = f"£{t.get('debit', 0):.2f}" if t.get('debit', 0) > 0 else ""
            
            self.table.setItem(row, 2, QTableWidgetItem(c_val))
            self.table.setItem(row, 3, QTableWidgetItem(d_val))
            
            combo = QComboBox()
            formatted_cats = [f"[{k}] {v}" for k, v in self.cat_dict.items()]
            combo.addItems(formatted_cats)
            
            # Set current text safely
            default_cat = t.get('category', 'Ignorado')
            idx = -1
            for c_idx, val in enumerate(self.cat_dict.values()):
                if val == default_cat or default_cat in val:
                    idx = c_idx
                    break
                    
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentText(default_cat)
                
            self.apply_combo_color(combo)
            combo.currentTextChanged.connect(lambda text, cb=combo: self.apply_combo_color(cb))
                
            self.table.setCellWidget(row, 4, combo)
            self.combos.append(combo)
            
    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress and source is self.table:
            key = event.text()
            if not key:
                return super().eventFilter(source, event)
                
            combined = self.pending_key + key
            
            # 1. Exact match
            if combined in self.cat_dict:
                self.pending_key = ""
                rows = set(item.row() for item in self.table.selectedItems())
                for row in rows:
                    cat_name = self.cat_dict[combined]
                    formatted_name = f"[{combined}] {cat_name}"
                    idx = self.combos[row].findText(formatted_name)
                    if idx >= 0:
                        self.combos[row].setCurrentIndex(idx)
                return True
                
            # 2. Prefix match
            has_prefixes = any(k.startswith(combined) and k != combined for k in self.cat_dict.keys())
            if has_prefixes:
                self.pending_key = combined
                return True
                
            # 3. No match -> Reset
            self.pending_key = ""
            
        return super().eventFilter(source, event)
            
    def apply_combo_color(self, combo):
        txt = combo.currentText()
        bg = COLORS['surface_light']
        col = COLORS['text_main']
        
        if "Ingreso" in txt or "Aportacion de Socio" in txt:
            bg = "#1B5E20" # Dark Green
            col = "#FFFFFF"
        elif "Gastos Fijos" in txt:
            bg = "#880E4F" # Dark Burgundy / Red
            col = "#FFFFFF"
        elif "Gastos Variables" in txt:
            bg = "#E65100" # Dark Orange
            col = "#FFFFFF"
        elif "Inversion" in txt or "Aportacion" in txt:
            bg = "#0D47A1" # Dark Blue
            col = "#FFFFFF"
        elif "Cuota" in txt:
            bg = "#37474F" # Blue Gray (for family transfers)
            col = "#FFFFFF"
        elif "Ignorad" in txt or "Transfer" in txt:
            bg = "#424242" # Dark Gray
            col = "#BDBDBD"
            
        combo.setStyleSheet(f"QComboBox {{ background-color: {bg}; color: {col}; border: 1px solid {COLORS['border']}; padding: 4px; border-radius: 4px; }} QComboBox::drop-down {{ border: 0px; }} QComboBox QAbstractItemView {{ background-color: {COLORS['surface']}; color: {COLORS['text_main']}; selection-background-color: {COLORS['primary']}; }}")

    def get_results(self):
        # Update self.transactions based on user choices
        for row, t in enumerate(self.transactions):
            txt = self.combos[row].currentText()
            # Strip the code e.g. "[51] Gastos Fijos: Hipoteca" -> "Gastos Fijos: Hipoteca"
            cat_only = txt.split('] ', 1)[-1] if '] ' in txt else txt
            t['category'] = cat_only
        return self.transactions
