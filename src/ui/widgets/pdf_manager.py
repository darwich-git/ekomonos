from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem, 
                             QSplitter, QHeaderView, QLabel, QMessageBox, QPushButton, 
                             QCheckBox, QDialog, QTextEdit, QProgressBar, QButtonGroup, QFrame, 
                             QRadioButton, QComboBox, QMenu, QGridLayout, QDoubleSpinBox, QDateEdit, QCompleter)
from PyQt6.QtCore import Qt, QSize, QDate, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QFont, QLinearGradient, QBrush, QAction
import os
import re
import shutil
from datetime import datetime

from ui.styles import COLORS
from core.library_manager import LibraryManager
from core.sne_manager import generate_sne_filename, SNE_PERIODS, SNE_TYPES

from config import LIBRARY_ROOT as _LIBRARY_ROOT_PATH
LIBRARY_ROOT = str(_LIBRARY_ROOT_PATH)

class NotesDialog(QDialog):
    def __init__(self, notes=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Document Notes")
        self.resize(520, 650) # 30% larger
        self.setStyleSheet("background-color: #FFF9C4; color: #000;") # Yellow Post-it style
        
        layout = QVBoxLayout(self)
        
        self.fields = []
        default_keys = ["Main Idea", "Focus", "Ajustes"]
        existing_notes = []
        
        if isinstance(notes, dict) and notes:
            for k, v in notes.items():
                existing_notes.append((k, v))
                
        for i in range(3):
            if i < len(existing_notes):
                title, content = existing_notes[i]
            else:
                if i < len(default_keys):
                    title = default_keys[i]
                    content = ""
                else:
                    title = f"Section {i+1}"
                    content = ""
                
            title_str = str(title) if title is not None else ""
            title_edit = QLineEdit(title_str)
            title_edit.setStyleSheet("font-weight: bold; background: transparent; border: 1px solid #E0E0E0; font-size: 14px; padding: 2px;")
            layout.addWidget(title_edit)
            
            content_str = str(content) if content is not None else ""
            content_edit = QTextEdit(content_str)
            content_edit.setAcceptRichText(False)
            content_edit.setPlaceholderText("Enter notes...")
            content_edit.setStyleSheet("background: transparent; border: 1px solid #E0E0E0; color: black;")
            layout.addWidget(content_edit)
            
            self.fields.append({'title': title_edit, 'content': content_edit})
        
        # Save Button
        btn_save = QPushButton("Save Note")
        btn_save.setStyleSheet(f"background-color: {COLORS['primary']}; color: black; font-weight: bold; border: none; padding: 8px;")
        btn_save.clicked.connect(self.accept)
        layout.addWidget(btn_save)

    def get_data(self):
        result = {}
        for field in self.fields:
            t = field['title'].text().strip()
            c = field['content'].toPlainText()
            if t:
                result[t] = c
        return result

class FileEditDialog(QDialog):
    def __init__(self, current_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Refactor / Rename File")
        self.resize(500, 420)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']};")
        
        self.data = current_data
        layout = QGridLayout(self)
        layout.setSpacing(10)
        
        filename = current_data.get("name", "")
        parts = filename.split('_')
        
        is_structured = False
        if len(parts) >= 5:
            last_part = os.path.splitext(parts[-1])[0]
            first_part_is_date = bool(re.match(r'^\d{4}-\d{2}-\d{2}$', parts[0]))
            last_part_is_date = bool(re.match(r'^\d{4}-\d{2}-\d{2}$', last_part))
            if first_part_is_date and last_part_is_date:
                is_structured = True

        if is_structured:
            period_end_val = parts[0]
            title_val = "_".join(parts[1:-3])
            form_val = parts[-3]
            lang_val = parts[-2].upper()
            release_val = os.path.splitext(parts[-1])[0]
        else:
            period_end_val = current_data.get("date_display", "")
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', period_end_val):
                period_end_val = datetime.now().strftime("%Y-12-31")
            
            title_val = os.path.splitext(filename)[0]
            form_val = "Full Year" if "reports" in current_data.get("category", "").lower() else "Transcript"
            lang_val = current_data.get("language", "EN").upper()
            release_val = period_end_val

        # Period End Date
        layout.addWidget(QLabel("Period End Date:"), 0, 0)
        self.period_end_edit = QDateEdit()
        self.period_end_edit.setCalendarPopup(True)
        self.period_end_edit.setDisplayFormat("yyyy-MM-dd")
        self.period_end_edit.setDate(QDate.fromString(period_end_val, "yyyy-MM-dd"))
        layout.addWidget(self.period_end_edit, 0, 1)
        
        # Document Title
        layout.addWidget(QLabel("Document Title:"), 1, 0)
        self.txt_title = QLineEdit(title_val)
        layout.addWidget(self.txt_title, 1, 1)
        
        # Form Name
        layout.addWidget(QLabel("Form Name:"), 2, 0)
        self.txt_form = QComboBox()
        self.txt_form.setEditable(True)
        standard_forms = ["Full Year", "Quarterly", "Interim Q1", "Interim Q2", "Interim Q3", "Interim Q4", "Interim H1", "Interim H2", "Transcript", "Excel", "Tesis", "Varios", "10-K", "10-Q", "20-F", "40-F", "6-K"]
        self.txt_form.addItems(standard_forms)
        self.txt_form.setCurrentText(form_val)
        layout.addWidget(self.txt_form, 2, 1)
        
        # Language
        layout.addWidget(QLabel("Language:"), 3, 0)
        self.txt_lang = QComboBox()
        self.txt_lang.setEditable(True)
        self.txt_lang.addItems(["EN", "ES", "DE", "FR"])
        self.txt_lang.setCurrentText(lang_val)
        layout.addWidget(self.txt_lang, 3, 1)

        # Release Date
        layout.addWidget(QLabel("Release Date:"), 4, 0)
        self.release_date_edit = QDateEdit()
        self.release_date_edit.setCalendarPopup(True)
        self.release_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.release_date_edit.setDate(QDate.fromString(release_val, "yyyy-MM-dd"))
        layout.addWidget(self.release_date_edit, 4, 1)
        
        # Current Name
        layout.addWidget(QLabel("Current Name:"), 5, 0)
        self.lbl_current_name = QLabel(filename)
        self.lbl_current_name.setWordWrap(True)
        self.lbl_current_name.setStyleSheet("font-size: 10px; color: gray;")
        layout.addWidget(self.lbl_current_name, 5, 1)
        
        # Preview
        layout.addWidget(QLabel("Preview Name:"), 6, 0)
        self.lbl_preview = QLabel()
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setStyleSheet(f"font-weight: bold; color: {COLORS['primary']};")
        layout.addWidget(self.lbl_preview, 6, 1)
        
        # Buttons
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Refactor & Save")
        btn_save.setStyleSheet(f"background-color: {COLORS['success']}; color: white; font-weight: bold; padding: 6px 12px;")
        btn_save.clicked.connect(self.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box, 7, 0, 1, 2)
        
        # Signals
        self.period_end_edit.dateChanged.connect(self.update_preview)
        self.txt_title.textChanged.connect(self.update_preview)
        self.txt_form.currentTextChanged.connect(self.update_preview)
        self.txt_lang.currentTextChanged.connect(self.update_preview)
        self.release_date_edit.dateChanged.connect(self.update_preview)
        
        self.update_preview()
        
    def update_preview(self):
        def clean_string(s):
            if not s: return "NA"
            cleaned = re.sub(r'[:\\/*?"<>|]', '', s)
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = re.sub(r'_+', '_', cleaned).strip()
            return cleaned

        period_end = self.period_end_edit.date().toString("yyyy-MM-dd")
        release = self.release_date_edit.date().toString("yyyy-MM-dd")
        title = self.txt_title.text().strip()
        form = self.txt_form.currentText()
        lang = self.txt_lang.currentText()
        
        clean_period_end = clean_string(period_end)
        clean_release = clean_string(release)
        clean_form = clean_string(form)
        clean_lang = clean_string(lang).upper()
        
        clean_title = clean_string(title)
        if len(clean_title) > 50:
            clean_title = clean_title[:50].strip()
            
        old_name = self.data.get("name", "")
        ext = os.path.splitext(old_name)[1] or ".pdf"
        
        new_name = f"{clean_period_end}_{clean_title}_{clean_form}_{clean_lang}_{clean_release}{ext}".upper()
        self.lbl_preview.setText(new_name)
        self.generated_filename = new_name
        
    def get_data(self):
        form_name = self.txt_form.currentText()
        form_lower = form_name.lower()
        date_str = self.period_end_edit.date().toString("yyyy-MM-dd")
        period = "NA"
        if "full year" in form_lower or "10-k" in form_lower or "20-f" in form_lower or "40-f" in form_lower or "annual" in form_lower:
            period = "FY"
        elif "interim h1" in form_lower or "h1" in form_lower or "half year" in form_lower or "half-year" in form_lower or "first half" in form_lower:
            period = "H1"
        elif "interim h2" in form_lower or "h2" in form_lower or "second half" in form_lower:
            period = "H2"
        elif "interim q1" in form_lower or "q1" in form_lower:
            period = "Q1"
        elif "interim q2" in form_lower or "q2" in form_lower:
            period = "Q2"
        elif "interim q3" in form_lower or "q3" in form_lower:
            period = "Q3"
        elif "interim q4" in form_lower or "q4" in form_lower:
            period = "Q4"
        elif "quarterly" in form_lower or "10-q" in form_lower or "6-k" in form_lower:
            month = date_str[5:7]
            if month == "03":
                period = "Q1"
            elif month == "06":
                period = "Q2"
            elif month == "09":
                period = "Q3"
            elif month == "12":
                period = "FY"

        return {
            "period_end_date": date_str,
            "year": str(self.period_end_edit.date().year()),
            "document_title": self.txt_title.text().strip(),
            "form_name": form_name,
            "language": self.txt_lang.currentText(),
            "release_date": self.release_date_edit.date().toString("yyyy-MM-dd"),
            "period": period,
            "new_name": self.generated_filename
        }

from PyQt6.QtGui import QIcon, QDesktopServices
from PyQt6.QtCore import QUrl
import subprocess

def open_url_in_chrome(url):
    """Attempts to open URL in Chrome, falls back to default browser."""
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME'))
    ]
    
    chrome_path = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_path = path
            break
            
    if chrome_path:
        try:
            subprocess.Popen([chrome_path, url])
            return
        except Exception:
            pass # Fallback
            
    QDesktopServices.openUrl(QUrl(url))

def open_pdf_in_foxit(file_path):
    """Attempts to open PDF in Foxit Reader, falls back to default."""
    foxit_paths = [
        r"C:\Program Files (x86)\Foxit Software\Foxit PDF Reader\FoxitPDFReader.exe",
        r"C:\Program Files\Foxit Software\Foxit PDF Reader\FoxitPDFReader.exe"
    ]
    
    foxit_path = None
    for path in foxit_paths:
        if os.path.exists(path):
            foxit_path = path
            break
            
    if foxit_path:
        try:
            subprocess.Popen([foxit_path, file_path])
            return
        except Exception:
            pass # Fallback
            
    try:
        os.startfile(file_path)
    except Exception as e:
         QMessageBox.critical(None, "Error", f"Could not open file: {e}")

class CompanyHeaderWidget(QWidget):
    def __init__(self):
        super().__init__()
        # Main Layout (Vertical: Top Group + Bottom Group)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # --- Top Group: Header Elements ---
        top_group = QWidget()
        top_layout = QHBoxLayout(top_group)
        top_layout.setContentsMargins(0,0,0,0)
        top_layout.setSpacing(20)
        
        # COL 1: Left (Logo + Combo)
        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        left_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        # 1. Logo
        self.lbl_logo = QLabel("TIKR")
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo.setFixedSize(100, 100)
        
        # Style: Round & Centered
        self.lbl_logo.setStyleSheet("""
            background-color: #424242; 
            color: #FBC02D; 
            border-radius: 50px; 
            font-weight: bold; 
            font-size: 30px;
            border: 3px solid #FBC02D;
        """)
        
        left_col.addWidget(self.lbl_logo, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # 2. Company Selector (White)
        self.combo_companies = QComboBox()
        self.combo_companies.setEditable(True) 
        self.combo_companies.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo_companies.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.combo_companies.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.combo_companies.setFixedSize(140, 30)
        
        # Install Event Filter to Clear on Click
        self.combo_companies.lineEdit().installEventFilter(self)
        
        self.combo_companies.setStyleSheet(f"""
            QComboBox {{
                background-color: white;
                color: #263238;
                border: 1px solid {COLORS['border']};
                padding: 4px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: darkgray;
                border-left-style: solid;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #263238;
                margin-right: 2px;
            }}
        """)
        left_col.addWidget(self.combo_companies)
        
        top_layout.addLayout(left_col)
        
        # COL 2: Middle (Stats: Time + Progress)
        mid_col = QVBoxLayout()
        mid_col.setSpacing(5) 
        mid_col.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignTop) 
        
        # Time
        self.lbl_hours = QLabel("00:00 h")
        self.lbl_hours.setStyleSheet(f"color: #FBC02D; font-family: 'Courier New', monospace; font-size: 28px; font-weight: bold;") 
        mid_col.addWidget(self.lbl_hours, 0, Qt.AlignmentFlag.AlignHCenter)
        
        from ui.widgets.progress_widget import ProgressWidget
        
        # Progress Bar (Custom)
        self.progress_bar = ProgressWidget()
        self.progress_bar.setFixedSize(450, 38) 
        mid_col.addWidget(self.progress_bar, 0, Qt.AlignmentFlag.AlignHCenter)
        
        top_layout.addLayout(mid_col)
        
        layout.addWidget(top_group)
        
        # --- Bottom Group: Buttons Grid ---
        # 3. Dynamic Links Container
        self.dynamic_links_widget = QWidget()
        self.dynamic_links_layout = QGridLayout(self.dynamic_links_widget) 
        self.dynamic_links_layout.setContentsMargins(0, 0, 0, 0)
        self.dynamic_links_layout.setSpacing(10)
        self.dynamic_links_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(self.dynamic_links_widget)
        layout.addStretch()
        
        # Store data
        self.excel_path = None
        
        # 1. The Valuator (Excel/Model)
        self.btn_valuator = QPushButton("EXCEL")
        self.btn_valuator.setFixedSize(60, 30)
        self.btn_valuator.setToolTip("The Valuator (Models/Excel)")
        self.btn_valuator.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_valuator.clicked.connect(self.open_excel)
        
        # 2. Edit
        self.btn_edit = QPushButton("EDIT")
        self.btn_edit.setFixedSize(60, 30)
        self.btn_edit.setToolTip("Edit Company Info")
        
    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj == self.combo_companies.lineEdit() and event.type() == QEvent.Type.MouseButtonPress:
            # Clear text on click to allow fresh search
            self.combo_companies.lineEdit().clear()
        return super().eventFilter(obj, event)

    def style_button(self, btn, active=False, color=None):
        # Larger buttons requested
        btn.setFixedSize(90, 35) 
        base_style = f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['text_dim']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """
        if active:
             c = color if color else COLORS['success']
             btn.setStyleSheet(f"background-color: {COLORS['surface_light']}; color: {c}; border: 2px solid {c}; border-radius: 6px; font-weight: bold; font-size: 11px;")
        else:
             btn.setStyleSheet(f"background-color: transparent; color: {COLORS['text_dim']}; border: 1px dashed {COLORS['border']}; border-radius: 6px; opacity: 0.3; font-size: 11px;")

    def update_info(self, ticker, pct, hours):
        self.lbl_logo.setText(ticker[:4]) 
        self.progress_bar.set_progress(pct / 100.0)
        
        h = int(hours)
        m = int((hours - h) * 60)
        self.lbl_hours.setText(f"{h:02d}:{m:02d} h")

    def update_links(self, excel_path, custom_links, **kwargs):
        self.excel_path = excel_path
        
        # Clear old grid
        while self.dynamic_links_layout.count():
            item = self.dynamic_links_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None) # Detach
                
        buttons = []
        
        # 1. THE VALUATOR (Excel)
        active_val = bool(excel_path and os.path.exists(excel_path))
        self.style_button(self.btn_valuator, active_val, COLORS['success'])
        self.btn_valuator.setEnabled(active_val)
        buttons.append(self.btn_valuator)
        
        # 2. EDIT
        self.style_button(self.btn_edit, True, COLORS['warning'])
        buttons.append(self.btn_edit)
        
        # 3. Dynamic Links
        for link in custom_links:
            title = link.get('title', 'Link').upper()
            url = link.get('url', '')
            color = link.get('color', COLORS['primary']) # Get color or default
            if not url: continue
            
            btn = QPushButton(title)
            self.style_button(btn, True, color) 
            btn.clicked.connect(lambda checked, u=url: open_url_in_chrome(u))
            buttons.append(btn)
            
        # Add to Grid (6 columns now as requested)
        for i, btn in enumerate(buttons):
            row = i // 6
            col = i % 6
            self.dynamic_links_layout.addWidget(btn, row, col)

    def open_excel(self):
        if self.excel_path:
            try:
                # Ensure absolute path
                abs_path = os.path.abspath(self.excel_path)
                # os.startfile(abs_path) 
                # Use QDesktopServices for better compatibility
                QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))
            except Exception as e:
                # Try explicit Excel opening if os.startfile fails or just print
                print(f"Error opening Excel: {e}") 
                QMessageBox.warning(self, "Error", f"Could not open Excel file:\n{self.excel_path}\nError: {e}")




class PdfManagerWidget(QWidget):
    file_data_changed = pyqtSignal()  # Emitted when file status/category changes

    def __init__(self, portfolio_path, embedded=False):
        super().__init__()
        self.portfolio_path = portfolio_path # Keep for scanning initial files
        self.library_manager = LibraryManager(LIBRARY_ROOT)
        self.current_filter = "All"
        self.current_year_filter = "All"
        self.embedded = embedded
        
        # Init Data Structures (Crucial for embedded mode)
        self.library_data = {}
        self.all_files_flat = []
        
        self.setup_ui()
        if not self.embedded:
            self.load_library()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Top Bar: Header & Search
        if not self.embedded:
            top_bar = QHBoxLayout()
            self.header_widget = CompanyHeaderWidget()
            top_bar.addWidget(self.header_widget, 1) # Stretch
            
            self.search_bar = QLineEdit()
            self.search_bar.setPlaceholderText("Search Library...")
            self.search_bar.setFixedWidth(250)
            self.search_bar.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; padding: 5px;")
            self.search_bar.textChanged.connect(self.filter_files)
            top_bar.addWidget(self.search_bar)
            
            layout.addLayout(top_bar)
        
        # Category Filters & Year Selector
        filter_layout = QHBoxLayout()
        self.filter_group = QButtonGroup(self)
        
        categories = ["All", "Annual Reports", "Reportes", "Transcript", "Excel", "Tesis", "Varios"]
        for cat in categories:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            if cat == "All": btn.setChecked(True)
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {COLORS['surface']}; color: {COLORS['text_dim']}; border: 1px solid {COLORS['border']}; padding: 5px 15px; }}
                QPushButton:checked {{ background-color: {COLORS['primary']}; color: black; border: none; }}
            """)
            btn.clicked.connect(lambda checked, c=cat: self.set_filter(c))
            self.filter_group.addButton(btn)
            filter_layout.addWidget(btn)
            
        # Year Selector
        filter_layout.addSpacing(10)
        filter_layout.addWidget(QLabel("Year:"))
        self.combo_year = QComboBox()
        self.combo_year.addItem("All")
        years = [str(y) for y in range(datetime.now().year, 2010, -1)]
        self.combo_year.addItems(years)
        self.combo_year.setMinimumWidth(100) 
        self.combo_year.currentTextChanged.connect(self.set_year_filter)
        self.combo_year.setStyleSheet(f"background-color: {COLORS['surface']}; padding: 5px;")
        filter_layout.addWidget(self.combo_year)
            
        filter_layout.addStretch()
        
        # --- NEW FOLDER BUTTON ---
        self.btn_open_folder = QPushButton("📁")
        self.btn_open_folder.setToolTip("Open Folder")
        self.btn_open_folder.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['surface']}; color: {COLORS['primary']}; border: 1px solid {COLORS['border']}; padding: 5px 10px; font-size: 16px; border-radius: 4px; }}
            QPushButton:hover {{ background-color: {COLORS['primary']}; color: black; }}
        """)
        self.btn_open_folder.clicked.connect(self.open_current_folder)
        filter_layout.addWidget(self.btn_open_folder)
        # -------------------------
        
        layout.addLayout(filter_layout)
        
        # Splitter or Just Table
        if self.embedded:
             # Just the table
             self.file_table = self.create_file_table()
             layout.addWidget(self.file_table)
        else:
            splitter = QSplitter(Qt.Orientation.Horizontal)
            # Left: Navigation Tree
            self.tree = QTreeWidget()
            self.tree.setHeaderLabel("Companies")
            self.tree.setFixedWidth(140)
            self.tree.setStyleSheet(f"background-color: {COLORS['surface']}; border: 1px solid {COLORS['border']};")
            self.tree.itemClicked.connect(self.on_tree_select)
            splitter.addWidget(self.tree)
            
            # Right: File List
            self.file_table = self.create_file_table()
            splitter.addWidget(self.file_table)
            splitter.setStretchFactor(0, 0) 
            splitter.setStretchFactor(1, 1) 
            layout.addWidget(splitter)
            
        self.library_data = {}
        self.all_files_flat = []
        self.current_ticker = None

    def create_file_table(self):
        table = QTableWidget()
        table.setColumnCount(7) 
        table.setHorizontalHeaderLabels(["Date", "Name", "Type", "Period", "Notes", "Status", ""])
        header = table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) 
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed) 
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed) 
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed) 
        table.setColumnWidth(4, 50) 
        table.setColumnWidth(5, 70) 
        table.setColumnWidth(6, 40) 
        table.setStyleSheet(f"background-color: {COLORS['surface']}; border: 1px solid {COLORS['border']}; gridline-color: {COLORS['border']};")
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.itemDoubleClicked.connect(self.open_file)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self.open_context_menu)
        table.setSortingEnabled(True) # 5.1 Enable Sorting
        return table

    def load_specific_company(self, ticker):
        """Used by embedded mode to load a single company"""
        self.current_ticker = ticker
        self.all_files_flat = [] # Clear list
        
        # Clear specific ticker data to avoid duplicates
        if ticker in self.library_data:
            del self.library_data[ticker]
        
        # Clear table immediately and force UI update to feel responsive
        if hasattr(self, 'file_table'):
            self.file_table.setRowCount(0)
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
        
        if not ticker:
            self.refresh_file_list()
            return
            
        # Fast path: Scan just this company folder
        stock_path = os.path.join(LIBRARY_ROOT, "STOCK", ticker)
        
        if os.path.exists(stock_path):
            # _scan_company_files modifies self.all_files_flat in place
            self._scan_company_files(ticker, stock_path)
            
        self.refresh_file_list()

    def load_custom_directory(self, path, name):
        """Loads files from a specific directory without assuming STOCK structure."""
        self.current_ticker = name # Use name as pseudo-ticker
        self.all_files_flat = []
        self.library_data = {}
        
        if hasattr(self, 'file_table'):
            self.file_table.setRowCount(0)
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
        if os.path.exists(path):
            self._scan_company_files(name, path)
            
        self.refresh_file_list()

    def open_current_folder(self):
        if not self.current_ticker:
            return
        
        path = os.path.join(LIBRARY_ROOT, "STOCK", self.current_ticker)
        # Check special situations if stock doesn't exist
        if not os.path.exists(path):
            path = os.path.join(LIBRARY_ROOT, "SITUACIONES ESPECIALES", self.current_ticker)
            
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def set_filter(self, category):
        self.current_filter = category
        self.refresh_file_list()

    def set_year_filter(self, year):
        self.current_year_filter = year
        self.refresh_file_list()

    def load_library(self):
        self.tree.clear()
        self.library_data = {}
        self.all_files_flat = []
        
        if not os.path.exists(self.portfolio_path):
            return

        # Scan Companies
        # New Structure: STOCK/<TICKER>
        for item in os.listdir(self.portfolio_path):
            company_path = os.path.join(self.portfolio_path, item)
            if os.path.isdir(company_path):
                ticker = item # Folder name is ticker
                self._scan_company_files(ticker, company_path)

        # Build Tree (Company Only)
        for ticker in sorted(self.library_data.keys()):
            ticker_item = QTreeWidgetItem(self.tree)
            ticker_item.setText(0, ticker)
            ticker_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "company", "ticker": ticker})

    def _scan_company_files(self, ticker, path):
        # Clear existing data to avoid duplicates upon rescan
        self.library_data[ticker] = {}
        self.all_files_flat = [f for f in self.all_files_flat if f.get("ticker") != ticker]

        for root, dirs, files in os.walk(path):
            for f in files:
                if f.lower().endswith(('.pdf', '.xlsx', '.xlsm', '.txt')):
                    full_path = os.path.join(root, f)
                    
                    year = "Uncategorized"
                    category = "Varios"
                    language = "EN"
                    period = "NA"
                    clean_name = f
                    date_str = ""

                    # Check folder structure for category
                    parent_folder = os.path.basename(root)
                    is_reports_folder = False
                    if "1 REPORTS" in parent_folder or "1 REPORTS" in root or "02.01_Reportes" in parent_folder or "02.01_Reportes" in root:
                        category = "Annual Reports" 
                        is_reports_folder = True
                    elif "2 TRANSCRIPTS" in parent_folder or "2 TRANSCRIPTS" in root or "02.02_Transcripciones" in parent_folder or "02.02_Transcripciones" in root:
                        category = "Transcript"
                    elif "3 EXCEL" in parent_folder or "3 EXCEL" in root or "03_Modelos_y_Datos" in parent_folder or "03_Modelos_y_Datos" in root:
                        category = "Excel"
                    elif "4 VARIOS" in parent_folder or "4 VARIOS" in root or "02.03_Articulos_y_Prensa" in parent_folder or "02.03_Articulos_y_Prensa" in root:
                        category = "Varios"

                    # Attempt Structured Parsing: YYYY-MM-DD_Title_FormName_Language_YYYY-MM-DD.pdf
                    parts = f.split('_')
                    is_structured = False
                    if len(parts) >= 5:
                        first_part_is_date = bool(re.match(r'^\d{4}-\d{2}-\d{2}$', parts[0]))
                        last_part = os.path.splitext(parts[-1])[0]
                        last_part_is_date = bool(re.match(r'^\d{4}-\d{2}-\d{2}$', last_part))
                        if first_part_is_date and last_part_is_date:
                            is_structured = True

                    if is_structured:
                        date_str = parts[0]
                        year = date_str[:4]
                        language = parts[-2].upper()
                        form_name = parts[-3]
                        clean_title = "_".join(parts[1:-3])
                        ext = os.path.splitext(f)[1]
                        clean_name = clean_title + ext

                        # Map period strictly using Form Name and Date
                        form_lower = form_name.lower()
                        if "full year" in form_lower or "10-k" in form_lower or "20-f" in form_lower or "40-f" in form_lower or "annual" in form_lower:
                            period = "FY"
                        elif "interim h1" in form_lower or "h1" in form_lower or "half year" in form_lower or "half-year" in form_lower or "first half" in form_lower:
                            period = "H1"
                        elif "interim h2" in form_lower or "h2" in form_lower or "second half" in form_lower:
                            period = "H2"
                        elif "interim q1" in form_lower or "q1" in form_lower:
                            period = "Q1"
                        elif "interim q2" in form_lower or "q2" in form_lower:
                            period = "Q2"
                        elif "interim q3" in form_lower or "q3" in form_lower:
                            period = "Q3"
                        elif "interim q4" in form_lower or "q4" in form_lower:
                            period = "Q4"
                        elif "quarterly" in form_lower or "10-q" in form_lower or "6-k" in form_lower:
                            # Deduce Q1/Q2/Q3 based on month of PeriodEndDate
                            month = date_str[5:7]
                            if month == "03":
                                period = "Q1"
                            elif month == "06":
                                period = "Q2"
                            elif month == "09":
                                period = "Q3"
                            elif month == "12":
                                period = "FY"
                            else:
                                period = "NA"
                        else:
                            period = "NA"
                            
                        # Refine category for reports folder based on period
                        if is_reports_folder:
                            category = "Annual Reports" if period == "FY" else "Reportes"
                    else:
                        # Fallback to legacy Heuristic Parsing
                        fname_lower = f.lower()
                        date_match = re.search(r'^(\d{4}-\d{2}-\d{2})', f)
                        if date_match:
                            date_str = date_match.group(1)
                            clean_name = f[len(date_str):].lstrip(" _-")
                            year = date_str[:4]
                        else:
                            year_match = re.search(r'(20\d{2})', f)
                            if year_match:
                                year = year_match.group(1)
                            date_str = year
                        
                        if is_reports_folder:
                            if "full_year" in fname_lower or "annual report" in fname_lower or "10-k" in fname_lower:
                                category = "Annual Reports"
                            else:
                                category = "Reportes"
                        elif category == "Varios":
                            if fname_lower.endswith('.xls') or fname_lower.endswith('.xlsx') or fname_lower.endswith('.xlsm'):
                                category = "Excel"
                            elif "full_year" in fname_lower or "annual report" in fname_lower:
                                category = "Annual Reports"
                            elif any(x in fname_lower for x in ["interim", "q1", "q2", "q3", "q4", "earning", "hy", "_rep", "-rep"]):
                                category = "Reportes"
                            elif "transcript" in fname_lower:
                                category = "Transcript"
                            elif "tesis" in fname_lower or "thesis" in fname_lower:
                                category = "Tesis"
                            elif any(x in fname_lower for x in ["notice", "press release"]):
                                category = "Varios"

                        if " es " in fname_lower or "_es_" in fname_lower or "spanish" in fname_lower:
                            language = "ES"

                        period = "FY" if category == "Annual Reports" else "NA"
                        if "q1" in fname_lower: period = "Q1"
                        elif "q2" in fname_lower: period = "Q2"
                        elif "q3" in fname_lower: period = "Q3"
                        elif "q4" in fname_lower: period = "Q4"
                        elif "h1" in fname_lower: period = "H1"
                        elif "h2" in fname_lower: period = "H2"
                        elif "9m" in fname_lower: period = "9M"
                    
                    if year not in self.library_data[ticker]:
                        self.library_data[ticker][year] = []
                        
                    file_obj = {
                        "path": full_path,
                        "name": f,
                        "clean_name": clean_name,
                        "date_display": date_str,
                        "ticker": ticker,
                        "year": year,
                        "period": period,
                        "category": category,
                        "language": language
                    }
                    
                    self.library_data[ticker][year].append(file_obj)
                    self.all_files_flat.append(file_obj)
                    
                    # Sync with DB
                    self.library_manager.update_file_metadata(full_path, ticker, category=category, year=year, language=language)

    def on_tree_select(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        self.current_ticker = data["ticker"]
        
        # Update Header
        pct, score = self.library_manager.get_company_progress(self.current_ticker)
        hours = self.library_manager.get_company_hours(self.current_ticker)
        self.header_widget.update_info(self.current_ticker, pct, hours)
        
        # Populate Year Combo
        self.combo_year.blockSignals(True)
        self.combo_year.clear()
        self.combo_year.addItem("All")
        years = sorted(self.library_data[self.current_ticker].keys(), reverse=True)
        self.combo_year.addItems(years)
        self.combo_year.blockSignals(False)
        self.combo_year.setCurrentIndex(0) # Default to All
        self.current_year_filter = "All"
        
        self.refresh_file_list()

    def refresh_file_list(self):
        if not self.current_ticker:
            return
            
        # Safety Check: Ticker must exist in data
        if self.current_ticker not in self.library_data:
            # If manually typed and not found, show nothing or clear
            self.file_table.setRowCount(0)
            return

        files_to_show = []
        years = self.library_data[self.current_ticker]
        
        if self.current_year_filter == "All":
            for y in years:
                files_to_show.extend(years[y])
        elif self.current_year_filter in years:
            files_to_show = years[self.current_year_filter]
            
        self.update_file_list(files_to_show)

    def update_file_list(self, files):
        self.file_table.setRowCount(0)
        
        # Filter by Category
        filtered_files = []
        for f in files:
            cat = f["category"] # Represents Folder/Heuristic Category
            period = f.get("period", "NA")
            lower_name = f.get('clean_name', '').lower()
            
            # --- Type Correction Logic ---
            # 1. Thesis Detection
            if cat == "Tesis" or "thesis" in lower_name or "tesis" in lower_name:
                f["type"] = "THESIS" # Force display type
                # Ensure it appears in Tesis tab
                if self.current_filter == "Tesis":
                    filtered_files.append(f)
                    continue

            # 2. Excel Detection
            if cat == "Excel" or f.get("name", "").lower().endswith(('.xlsx', '.xls', '.xlsm')):
                 f["type"] = "EXCEL" # Force display type
                 if self.current_filter == "Excel":
                     filtered_files.append(f)
                     continue

            # --- Standard Filtering ---
            if self.current_filter == "All":
                 filtered_files.append(f)
                 
            elif self.current_filter == "Annual Reports":
                 if (cat == "Annual Reports" or cat == "Reportes") and period == "FY":
                     filtered_files.append(f)
                     
            elif self.current_filter == "Reportes":
                 if (cat == "Annual Reports" or cat == "Reportes") and period != "FY":
                     filtered_files.append(f)
                     
            elif self.current_filter == "Tesis":
                 # Already handled above, but checks strictly category here if name check failed?
                 # If name check failed, it wouldn't be marked THESIS. 
                 # If folder is Tesis, we included it above.
                 if cat == "Tesis":
                     filtered_files.append(f)
            
            elif self.current_filter == "Transcript":
                 if cat == "Transcript":
                     filtered_files.append(f)
                     
            elif self.current_filter == "Excel":
                 if cat == "Excel":
                     filtered_files.append(f)
                     
            elif self.current_filter == "Varios":
                 if cat == "Varios":
                     filtered_files.append(f)
                
        # Sort: Date Descending
        filtered_files.sort(key=lambda x: x.get("date_display", "") or x["year"], reverse=True)
        
        self.file_table.setRowCount(len(filtered_files))
        
        # Find newest Excel for Header Button
        latest_excel = None
        # valid_excels = [x for x in files if x.get("category") == "Excel" or x.get("name", "").lower().endswith(tuple(['.xls', '.xlsx', '.xlsm']))]
        # if valid_excels:
        #      # Sort by date
        #      valid_excels.sort(key=lambda x: x.get("date_display", "") or "0000", reverse=True)
        #      latest_excel = valid_excels[0]["path"]
        
        # Actually proper place for this is when reloading library/scanning, 
        # but here we have the list. Let's do it here.
        all_excels = [x for x in files if x.get("category") == "Excel" or x.get("name", "").lower().endswith(('.xlsx', '.xls', '.xlsm'))]
        if all_excels:
             all_excels.sort(key=lambda x: os.path.getmtime(x["path"]) if os.path.exists(x["path"]) else 0, reverse=True)
             latest_excel = all_excels[0]["path"]

        # Update Header Button (Only if NOT embedded, as embedded uses parent header)
        if not self.embedded and hasattr(self, 'header_widget'):
            # self.header_widget.update_links(latest_excel, []) # Custom links? we need to fetch them
            # We need checking if we have custom links too. 
            # Ideally we fetch custom links from manager.
            custom_links = self.library_manager.get_company_links(self.current_ticker)
            self.header_widget.update_links(latest_excel, custom_links)

        self.file_table.setSortingEnabled(False) # Disable during insertion
        
        for i, f in enumerate(filtered_files):
            row = i
            # self.file_table.insertRow(row) # Not needed if setRowCount is used
            
            # Get DB Metadata
            meta = self.library_manager.get_file_metadata(f["path"])
            notes = meta["notes"] if meta else {}
            status = meta["status"] if meta else 0 # 0=New, 1=In Process, 2=Reviewed
            period = f.get("period", "NA") # Period is mostly file-based
            
            # Update category from DB if changed
            category = meta["category"] if meta else f["category"]
            f["category"] = category 
            
            # 5.2 Type Acronym
            type_acronym = f.get("type_code", "") # If we parsed it
            if not type_acronym:
                 # Heuristic mapping
                 if category == "Annual Reports": type_acronym = "REP"
                 elif category == "Reportes": type_acronym = "REP" # Qs are REPs too
                 elif category == "Transcript": type_acronym = "TRANS"
                 elif category == "Excel": type_acronym = "EXCEL"
                 elif category == "Tesis": type_acronym = "TESIS"
                 elif category == "Varios": type_acronym = "VAR"
                 else: type_acronym = "DOC"
            
            # Date (Full Date)
            date_item = QTableWidgetItem(f.get("date_display", f["year"]))
            self.file_table.setItem(row, 0, date_item)
            
            # Name (Cleaned)
            clean_name = f.get("clean_name", f["name"])
            name_item = QTableWidgetItem(clean_name)
            name_item.setData(Qt.ItemDataRole.UserRole, f["path"]) # Store full path invisible
            self.file_table.setItem(row, 1, name_item)
            
            # Type Acronym
            self.file_table.setItem(row, 2, QTableWidgetItem(type_acronym))
            
            # Period
            self.file_table.setItem(row, 3, QTableWidgetItem(period))

            # Row Color Logic (Dark Theme Compatible)
            row_brush = None
            if status == 2: # Reviewed - Light/Dark Grey
                row_brush = QBrush(QColor("#2d2d2d")) 
            elif status == 1: # In Process - Light/Dark Yellow
                row_brush = QBrush(QColor("#403d21")) 
            
            # Notes Button
            btn_notes = QPushButton()
            btn_notes.setFixedSize(24, 24)
            btn_notes.setCursor(Qt.CursorShape.PointingHandCursor)
            
            has_notes = False
            if isinstance(notes, dict):
                has_notes = any(bool(v.strip()) for v in notes.values())
            elif notes:
                has_notes = True

            if has_notes:
                btn_notes.setText("📝")
                btn_notes.setToolTip("Ver notas (Activas)")
                btn_notes.setStyleSheet(f"background-color: #FF9800; border: none; border-radius: 12px; font-size: 11px; color: white;")
            else:
                btn_notes.setText("+")
                btn_notes.setToolTip("Añadir notas")
                btn_notes.setStyleSheet(f"background-color: transparent; border: 2px dashed #555555; border-radius: 12px; font-size: 11px; color: {COLORS['text_dim']};")
            
            btn_notes.clicked.connect(lambda checked, p=f["path"], t=f["ticker"]: self.open_notes(p, t))
            widget_notes = QWidget()
            layout_notes = QHBoxLayout(widget_notes)
            layout_notes.setContentsMargins(0,0,0,0)
            layout_notes.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout_notes.addWidget(btn_notes)
            self.file_table.setCellWidget(row, 4, widget_notes)
            
            # Status Widget (Compact Dot buttons: In Progress / Reviewed)
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(0,0,0,0)
            status_layout.setSpacing(8)
            status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_widget.setStyleSheet("background-color: transparent;")
            
            # In Progress Dot (Yellow)
            btn_process = QPushButton()
            btn_process.setFixedSize(14, 14)
            btn_process.setCursor(Qt.CursorShape.PointingHandCursor)
            if status == 1:
                btn_process.setToolTip("In Progress (Activo)")
                btn_process.setStyleSheet("background-color: #f1c40f; border: none; border-radius: 7px;")
            else:
                btn_process.setToolTip("Marcar como En Proceso")
                btn_process.setStyleSheet("background-color: transparent; border: 2px solid #555555; border-radius: 7px;")
            btn_process.clicked.connect(lambda checked, p=f["path"], t=f["ticker"], cur=status: self.set_status(p, t, 0 if cur == 1 else 1))
            status_layout.addWidget(btn_process)
            
            # Reviewed Dot (Green)
            btn_reviewed = QPushButton()
            btn_reviewed.setFixedSize(14, 14)
            btn_reviewed.setCursor(Qt.CursorShape.PointingHandCursor)
            if status == 2:
                btn_reviewed.setToolTip("Reviewed (Activo)")
                btn_reviewed.setStyleSheet("background-color: #2ecc71; border: none; border-radius: 7px;")
            else:
                btn_reviewed.setToolTip("Marcar como Revisado")
                btn_reviewed.setStyleSheet("background-color: transparent; border: 2px solid #555555; border-radius: 7px;")
            btn_reviewed.clicked.connect(lambda checked, p=f["path"], t=f["ticker"], cur=status: self.set_status(p, t, 0 if cur == 2 else 2))
            status_layout.addWidget(btn_reviewed)
            
            self.file_table.setCellWidget(row, 5, status_widget)
            
            # Delete Button (Centered)
            btn_delete = QPushButton()
            btn_delete.setIcon(QIcon("assets/icon_delete.svg"))
            btn_delete.setIconSize(QSize(18, 18))
            btn_delete.setFixedSize(24, 24)
            btn_delete.setStyleSheet("background-color: transparent; border: none;")
            btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_delete.clicked.connect(lambda checked, p=f["path"], t=f["ticker"]: self.delete_file(p, t))
            widget_delete = QWidget()
            layout_delete = QHBoxLayout(widget_delete)
            layout_delete.setContentsMargins(0,0,0,0)
            layout_delete.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout_delete.addWidget(btn_delete)
            self.file_table.setCellWidget(row, 6, widget_delete)
            
            # Apply Row Color
            if row_brush:
                for c in range(self.file_table.columnCount()):
                    item = self.file_table.item(row, c)
                    if item:
                        item.setBackground(row_brush)

        self.file_table.setSortingEnabled(True) # Re-enable sorting

    def open_context_menu(self, position):
        index = self.file_table.indexAt(position)
        if not index.isValid():
            return
            
        row = index.row()
        path_item = self.file_table.item(row, 1)
        path = path_item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu()
        cat_menu = menu.addMenu("Categorize as...")
        
        categories = ["Annual Reports", "Reportes", "Transcript", "Excel", "Varios"]
        for cat in categories:
            action = QAction(cat, self)
            action.triggered.connect(lambda checked, c=cat, p=path: self.change_category(p, c))
            cat_menu.addAction(action)

        # Edit / Rename Option
        edit_action = QAction("Edit Metadata / Rename", self)
        edit_action.triggered.connect(lambda checked, p=path, t=self.current_ticker: self.edit_file(p, t))
        menu.addAction(edit_action)

        menu.exec(self.file_table.viewport().mapToGlobal(position))

    def change_category(self, path, new_category):
        if not self.current_ticker:
            return
            
        self.library_manager.update_file_metadata(path, self.current_ticker, category=new_category)
        
        # Update Header (Score might change) - only in standalone mode
        pct, score = self.library_manager.get_company_progress(self.current_ticker)
        hours = self.library_manager.get_company_hours(self.current_ticker)
        
        if hasattr(self, 'header_widget'):
            self.header_widget.update_info(self.current_ticker, pct, hours)
        
        # Notify parent (InputStockWidget) to refresh progress bar in embedded mode
        self.file_data_changed.emit()
        
        self.refresh_file_list()

    def open_notes(self, path, ticker):
        meta = self.library_manager.get_file_metadata(path)
        notes = meta["notes"] if meta else {}
        
        dialog = NotesDialog(notes, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_notes = dialog.get_data()
            self.library_manager.update_file_metadata(path, ticker, notes=new_notes)
            self.refresh_file_list()

    def set_status(self, path, ticker, status):
        self.library_manager.update_file_metadata(path, ticker, status=status)
        
        # Update Header (standalone mode)
        pct, score = self.library_manager.get_company_progress(ticker)
        hours = self.library_manager.get_company_hours(ticker)
        
        if hasattr(self, 'header_widget'):
            self.header_widget.update_info(ticker, pct, hours)
        
        # Notify parent (InputStockWidget) to refresh progress bar in embedded mode
        self.file_data_changed.emit()
        
        self.refresh_file_list()

    def filter_files(self, text):
        self.current_filter_text = text # Store logic
        if not text:
            self.refresh_file_list()
            return

        text = text.lower()
        matches = [f for f in self.all_files_flat if text in f["name"].lower()]
        self.update_file_list(matches)

    def delete_file(self, path, ticker):
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"Are you sure you want to delete this file?\n{os.path.basename(path)}",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(path):
                    import shutil
                    from datetime import datetime
                    trash_path = os.path.join(LIBRARY_ROOT, "_Trash")
                    if not os.path.exists(trash_path):
                        os.makedirs(trash_path)
                    
                    file_name = os.path.basename(path)
                    name, ext = os.path.splitext(file_name)
                    dest = os.path.join(trash_path, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
                    
                    shutil.move(path, dest)
                    
                    # Also try to remove parent dir if empty
                    parent_dir = os.path.dirname(path)
                    if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                        try:
                            os.rmdir(parent_dir)
                        except: pass
                
                # Also remove from DB if needed, but scanning handles it usually. 
                # Explicitly removing from DB is better practice if we track history, 
                # but here we just sync with FS.
                self.library_manager.update_file_metadata(path, ticker, status=0) # Reset or delete entry? 
                # Actually, if file is gone, it won't show up in scan.
                
                # Refresh using QTimer to avoid segfault when destroying the widget that triggered this
                from PyQt6.QtCore import QTimer
                if self.embedded:
                     QTimer.singleShot(0, lambda: self.load_specific_company(ticker))
                else:
                     QTimer.singleShot(0, lambda: (self._scan_company_files(ticker, os.path.join(LIBRARY_ROOT, "STOCK", ticker)), self.refresh_file_list()))


                # Update Header if needed
                pct, score = self.library_manager.get_company_progress(ticker or self.current_ticker)
                hours = self.library_manager.get_company_hours(ticker or self.current_ticker)
                if hasattr(self, 'header_widget'):
                    self.header_widget.update_info(ticker or self.current_ticker, pct, hours)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete file: {e}")

    def edit_file(self, path, ticker):
        if not path or not os.path.exists(path):
             return
             
        file_obj = next((f for f in self.all_files_flat if f["path"] == path), {})
        if not file_obj:
             file_obj = {"path": path, "name": os.path.basename(path), "ticker": ticker}
             
        dialog = FileEditDialog(file_obj, self)
        if dialog.exec():
            new_data = dialog.get_data()
            new_name = new_data['new_name']
            
            dir_name = os.path.dirname(path)
            new_path = os.path.join(dir_name, new_name)
            
            try:
                # Rename File
                os.rename(path, new_path)
                
                # Update Metadata based on Form Name
                form_lower = new_data['form_name'].lower()
                cat = "Varios"
                if "full year" in form_lower or "quarterly" in form_lower or "interim" in form_lower or "10-k" in form_lower or "10-q" in form_lower or "20-f" in form_lower or "40-f" in form_lower or "6-k" in form_lower:
                    if "1 REPORTS" in path or "1 REPORTS" in new_path or "02.01_Reportes" in path or "02.01_Reportes" in new_path:
                        cat = "Annual Reports" if new_data['period'] == "FY" else "Reportes"
                    else:
                        cat = "Annual Reports" if new_data['period'] == "FY" else "Reportes"
                elif "transcript" in form_lower:
                    cat = "Transcript"
                elif "excel" in form_lower:
                    cat = "Excel"
                elif "tesis" in form_lower or "thesis" in form_lower:
                    cat = "Tesis"
                elif "varios" in form_lower:
                    cat = "Varios"
                else:
                    if "1 REPORTS" in new_path or "02.01_Reportes" in new_path:
                        cat = "Annual Reports" if new_data['period'] == "FY" else "Reportes"
                    elif "2 TRANSCRIPTS" in new_path or "02.02_Transcripciones" in new_path:
                        cat = "Transcript"
                    elif "3 EXCEL" in new_path or "03_Modelos_y_Datos" in new_path:
                        cat = "Excel"
                    else:
                        cat = "Varios"
                
                self.library_manager.update_file_metadata(
                    new_path, 
                    ticker,
                    category=cat,
                    year=new_data['year'],
                    quarter=new_data['period'],
                    language=new_data['language']
                )
                
                # Refresh
                if self.embedded:
                     self.load_specific_company(ticker)
                else:
                    self._scan_company_files(ticker, os.path.join(LIBRARY_ROOT, "STOCK", ticker))
                    self.refresh_file_list()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename file: {e}")

    def open_file(self, item):
        row = item.row()
        path_item = self.file_table.item(row, 1) # Name is now col 1
        path = path_item.data(Qt.ItemDataRole.UserRole)
        
        # Update Access Time
        if self.current_ticker:
             self.library_manager.update_file_metadata(path, self.current_ticker, last_accessed=datetime.now().isoformat())
        
        try:
            if path.lower().endswith(".pdf"):
                open_pdf_in_foxit(path)
            else:
                os.startfile(path) # Excel etc.
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file: {e}")
