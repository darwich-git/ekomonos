from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QDialogButtonBox)
from ui.styles import COLORS

class EditAttributesDialog(QDialog):
    def __init__(self, attributes_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Attributes")
        self.resize(400, 300)
        self.attributes_list = attributes_list if attributes_list else []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Table
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Name", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: {COLORS['surface_light']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; }}
            QHeaderView::section {{ background-color: {COLORS['surface']}; color: {COLORS['text_dim']}; font-weight: bold; border: 1px solid {COLORS['border']}; }}
            QTableWidget::item {{ border-bottom: 1px solid {COLORS['border']}; }}
        """)
        layout.addWidget(self.table)
        
        # Add/Remove buttons
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("+ Add Row")
        btn_remove = QPushButton("- Remove Selected")
        for btn in [btn_add, btn_remove]:
            btn.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['primary']}; border: 1px solid {COLORS['primary']}; padding: 4px; border-radius: 4px;")
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)
        
        btn_add.clicked.connect(self.add_row)
        btn_remove.clicked.connect(self.remove_row)
        
        # Dialog buttons
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(len(self.attributes_list))
        for row, attr in enumerate(self.attributes_list):
            name_item = QTableWidgetItem(attr.get("name", ""))
            value_item = QTableWidgetItem(str(attr.get("value", "")))
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, value_item)

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))

    def remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def get_data(self):
        data = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            name = name_item.text().strip() if name_item else ""
            value = value_item.text().strip() if value_item else ""
            if name or value:
                data.append({"name": name, "value": value})
        return data
