from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox)
from PyQt6.QtCore import Qt
from ui.styles import COLORS
from core.category_manager import get_categories, save_categories

class CategoryManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Custom Categories")
        self.resize(600, 600)
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
            QPushButton#btnDanger {{
                background-color: #f44336;
                color: white;
            }}
            QPushButton:hover {{ background-color: #45a049; }}
            QPushButton#btnDanger:hover {{ background-color: #d32f2f; }}
        """)
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Añade, elimina o renombra tus categorías.\nUsa códigos numéricos para asignación rápida.")
        layout.addWidget(lbl)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Key (Code)", "Category Name"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        self.load_table()
        
        btn_layout = QHBoxLayout()
        
        btn_add = QPushButton("+ Añadir Fila")
        btn_add.clicked.connect(self.add_row)
        btn_layout.addWidget(btn_add)
        
        btn_del = QPushButton("- Borrar Seleccion")
        btn_del.setObjectName("btnDanger")
        btn_del.clicked.connect(self.del_row)
        btn_layout.addWidget(btn_del)
        
        btn_layout.addStretch()
        
        btn_save = QPushButton("Guardar Cambios")
        btn_save.clicked.connect(self.save_and_close)
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)

    def load_table(self):
        cats = get_categories()
        # Sort by key numerically if possible, else alphabetically
        def sort_key(k):
            try: return int(k)
            except: return 99999
        
        sorted_keys = sorted(cats.keys(), key=sort_key)
        
        self.table.setRowCount(len(sorted_keys))
        for row, k in enumerate(sorted_keys):
            self.table.setItem(row, 0, QTableWidgetItem(k))
            self.table.setItem(row, 1, QTableWidgetItem(cats[k]))

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))

    def del_row(self):
        rows = set([item.row() for item in self.table.selectedItems()])
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)

    def save_and_close(self):
        new_cats = {}
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            val_item = self.table.item(row, 1)
            
            if key_item and val_item:
                k = key_item.text().strip()
                v = val_item.text().strip()
                if k and v:
                    new_cats[k] = v
        
        if not new_cats:
            QMessageBox.warning(self, "Error", "Debes tener al menos una categoría válida.")
            return
            
        save_categories(new_cats)
        self.accept()
