import os
import shutil
import datetime
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QLineEdit, QMessageBox, QFileDialog,
    QFrame
)
from PyQt6.QtCore import Qt, QDate
from ui.styles import COLORS
from ui.widgets.input_stock import FileDropArea, SmartDateEdit
from ui.widgets.pdf_manager import PdfManagerWidget

from config import LIBRARY_ROOT as _LIBRARY_ROOT_PATH
LIBRARY_ROOT = str(_LIBRARY_ROOT_PATH)
SPECIAL_ROOT = os.path.join(LIBRARY_ROOT, "SITUACIONES ESPECIALES")

# File categories aligned with situation types
FILE_CATEGORIES = [
    ("1 INFORMES",   [".pdf", ".doc", ".docx", ".txt", ".ppt", ".pptx"]),
    ("2 EXCEL",      [".xls", ".xlsx", ".xlsm", ".csv"]),
    ("3 PRESENTACIONES", [".ppt", ".pptx", ".key"]),
    ("4 IMAGENES",   [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"]),
    ("5 LEGALES",    [".pdf", ".doc", ".docx"]),
    ("6 OTROS",      []),  # catch-all
]

CATEGORY_NAMES = [c[0] for c in FILE_CATEGORIES]


def _detect_category(ext):
    """Return the best-fit category folder for a file extension."""
    ext = ext.lower()
    # Specific priority checks
    if ext in [".xls", ".xlsx", ".xlsm", ".csv"]:
        return "2 EXCEL"
    if ext in [".ppt", ".pptx", ".key"]:
        return "3 PRESENTACIONES"
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"]:
        return "4 IMAGENES"
    if ext in [".pdf", ".doc", ".docx", ".txt"]:
        return "1 INFORMES"
    return "6 OTROS"


class SituationLibraryWidget(QWidget):
    def __init__(self, situation_data, compact=False, parent=None):
        super().__init__(parent)
        self.situation_data = situation_data
        self.compact = compact

        title = situation_data.get('title', 'Untitled').strip()
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title).strip()
        self.base_folder = os.path.join(SPECIAL_ROOT, safe_title)
        os.makedirs(self.base_folder, exist_ok=True)

        # Create all category folders
        for cat in CATEGORY_NAMES:
            os.makedirs(os.path.join(self.base_folder, cat), exist_ok=True)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # ── Upload toolbar ─────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setStyleSheet(
            f"background:{COLORS['surface']}; border:1px solid {COLORS['border']}; border-radius:6px;"
        )
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(10, 4, 10, 4)
        tb_lay.setSpacing(15)

        # 1. Left Spacer (25% of total width - Black area in diagram)
        tb_lay.addStretch(25)

        # 2. Drop zone (Green area in diagram)
        self.drop_area = FileDropArea(self)
        self.drop_area.placeholder_text = f"<html><body style='text-align:center;'><p style='color:#FF9800; font-size:13px; font-weight:bold; margin:0;'>Drop Files</p><p style='color:#A0A0A0; font-size:10px; margin:0;'>Click to browse</p></body></html>"
        self.drop_area.setText(self.drop_area.placeholder_text)
        self.drop_area.setFixedSize(140, 65) # Made it taller (was 50)
        tb_lay.addWidget(self.drop_area)

        # Inputs column
        inp_lay = QVBoxLayout()
        inp_lay.setSpacing(2)

        # Date row — SmartDateEdit for typing
        date_row = QHBoxLayout()
        lbl_date = QLabel("Date:")
        lbl_date.setFixedWidth(50)
        lbl_date.setStyleSheet(f"color:{COLORS['text_dim']}; font-size:11px;")
        self.date_edit = SmartDateEdit(self)
        # Removed fixed width to allow expansion
        self.date_edit.set_from_db(datetime.date.today().strftime("%Y-%m-%d"))
        self.date_edit.setStyleSheet(
            f"background:{COLORS['surface_light']}; color:white;"
            f" border:1px solid {COLORS['border']}; padding:3px; border-radius:3px; font-size:11px;"
        )
        date_row.addWidget(lbl_date)
        date_row.addWidget(self.date_edit)
        inp_lay.addLayout(date_row)

        # Category combo
        cat_row = QHBoxLayout()
        lbl_cat = QLabel("Category:")
        lbl_cat.setFixedWidth(50)
        lbl_cat.setStyleSheet(f"color:{COLORS['text_dim']}; font-size:11px;")
        self.cat_combo = QComboBox(self)
        # self.cat_combo.addItem("Auto-detect") # Removed as requested
        for cat in CATEGORY_NAMES:
            self.cat_combo.addItem(cat)
        # Removed fixed width to allow expansion
        self.cat_combo.setStyleSheet(
            f"background:{COLORS['surface_light']}; color:white;"
            f" border:1px solid {COLORS['border']}; border-radius:3px; padding:3px; font-size:11px;"
        )
        cat_row.addWidget(lbl_cat)
        cat_row.addWidget(self.cat_combo)
        inp_lay.addLayout(cat_row)

        # Optional tag / note
        tag_row = QHBoxLayout()
        lbl_tag = QLabel("Note:")
        lbl_tag.setFixedWidth(50)
        lbl_tag.setStyleSheet(f"color:{COLORS['text_dim']}; font-size:11px;")
        self.txt_tag = QLineEdit(self)
        self.txt_tag.setPlaceholderText("Optional note")
        # Removed fixed width to allow expansion into 75% area
        self.txt_tag.setStyleSheet(
            f"background:{COLORS['surface_light']}; color:white;"
            f" border:1px solid {COLORS['border']}; border-radius:3px; padding:3px; font-size:11px;"
        )
        tag_row.addWidget(lbl_tag)
        tag_row.addWidget(self.txt_tag)
        inp_lay.addLayout(tag_row)

        # 3. Inputs Section (Takes the rest of the 75% - Red area in diagram)
        tb_lay.addLayout(inp_lay, 75)

        # Buttons column
        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        btn_upload = QPushButton("⬆ Upload")
        btn_upload.setFixedHeight(26)
        btn_upload.setStyleSheet(
            f"background:{COLORS.get('success','#2ECC71')}; color:#000; border:none;"
            f" border-radius:4px; font-weight:bold; padding:0 10px; font-size:11px;"
        )
        btn_upload.clicked.connect(self.process_file)

        btn_open = QPushButton("📂 Open")
        btn_open.setFixedHeight(22)
        btn_open.setStyleSheet(
            f"background:transparent; color:{COLORS['text_dim']}; border:1px solid {COLORS['border']};"
            f" border-radius:4px; padding:0 8px; font-size:11px;"
        )
        btn_open.clicked.connect(self._open_folder)

        btn_col.addWidget(btn_upload)
        btn_col.addWidget(btn_open)
        # No stretch needed if we want it tight
        tb_lay.addLayout(btn_col)

        main_layout.addWidget(toolbar)
        
        # Reduced spacing before library
        main_layout.setSpacing(2)

        if not self.compact:
            # ── Divider ────────────────────────────────────────────────────────
            div = QFrame()
            div.setFixedHeight(1)
            div.setStyleSheet(f"background:{COLORS['border']};")
            main_layout.addWidget(div)

            # ── Library view ───────────────────────────────────────────────────
            lbl_files = QLabel("📁  Situation Files")
            lbl_files.setStyleSheet(
                f"color:{COLORS['primary']}; font-weight:bold; font-size:14px; margin-top:4px;"
            )
            main_layout.addWidget(lbl_files)

            self.library_widget = PdfManagerWidget(self.base_folder, embedded=True, parent=self)
            self.library_widget.load_custom_directory(
                self.base_folder, self.situation_data.get('title', 'Situation')
            )
            main_layout.addWidget(self.library_widget)
        else:
            self.library_widget = None

    def _open_folder(self):
        import subprocess
        if os.path.exists(self.base_folder):
            subprocess.Popen(["explorer", self.base_folder])

    def on_file_dropped(self):
        pass

    def process_file(self):
        if not self.drop_area.current_files:
            QMessageBox.warning(self, "No File", "Please drop or add a file first.")
            return

        src_path = self.drop_area.current_files[0]
        if not os.path.exists(src_path):
            return

        base_name = os.path.basename(src_path)
        name, ext = os.path.splitext(base_name)
        ext_lower = ext.lower()

        # Category selection
        cat_choice = self.cat_combo.currentText()
        if cat_choice == "Auto-detect":
            subfolder = _detect_category(ext_lower)
        else:
            subfolder = cat_choice

        dest_folder = os.path.join(self.base_folder, subfolder)
        os.makedirs(dest_folder, exist_ok=True)

        # Build filename: YYYY-MM-DD_note_original.ext
        date_obj = self.date_edit.date().toPyDate()
        tag = self.txt_tag.text().strip()
        tag_str = f"_{tag}" if tag else ""
        new_name = f"{date_obj.strftime('%Y-%m-%d')}{tag_str}_{name}{ext}"
        dest_path = os.path.join(dest_folder, new_name)

        try:
            shutil.copy2(src_path, dest_path)
            self.drop_area.clear_files()
            self.txt_tag.clear()
            self.cat_combo.setCurrentIndex(0)
            QMessageBox.information(self, "Success", f"File saved to  {subfolder}.")
            if self.library_widget:
                self.library_widget.load_custom_directory(
                    self.base_folder, self.situation_data.get('title', 'Situation')
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to copy file: {e}")
