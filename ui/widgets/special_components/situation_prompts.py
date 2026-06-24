import json
import uuid
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTextEdit, QWidget, QScrollArea, QFrame, QApplication, QMessageBox,
    QToolBox, QMenu, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QIcon, QAction
from ui.styles import COLORS
from ui.widgets.prompt_library import PromptManager # Reuse existing manager for General prompts

class CopyButton(QPushButton):
    def __init__(self, text_to_copy, parent=None):
        super().__init__("Copy", parent)
        self.text_to_copy = text_to_copy
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(60, 25)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['text_dim']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary']};
                color: black;
            }}
        """)
        self.clicked.connect(self.copy_to_clipboard)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_to_copy)
        self.setText("Copied!")
        self.setStyleSheet(f"background-color: {COLORS['success']}; color: white; border: none; border-radius: 4px; font-size: 11px;")

class ExpandButton(QPushButton):
    toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__("▼", parent) # Down arrow initially
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(25, 25)
        self.setCheckable(True)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_dim']};
                border: none;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {COLORS['primary']};
            }}
            QPushButton:checked {{
                color: {COLORS['accent']};
            }}
        """)
        self.clicked.connect(self.on_click)
        
    def on_click(self):
        is_expanded = self.isChecked()
        self.setText("▲" if is_expanded else "▼")
        self.toggled.emit(is_expanded)

class PromptItemWidget(QFrame):
    delete_requested = pyqtSignal(str) # prompt_id
    
    def __init__(self, p_id, title, text, read_only=False):
        super().__init__()
        self.p_id = p_id
        self.title = title
        self.text = text
        self.read_only = read_only 
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-bottom: 5px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Header: Title + Copy + Actions
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {COLORS['primary']}; font-weight: bold; font-size: 13px; border: none; background: transparent;")
        header_layout.addWidget(lbl_title)
        
        header_layout.addStretch()
        
        btn_copy = CopyButton(text)
        header_layout.addWidget(btn_copy)
        
        self.btn_expand = ExpandButton()
        self.btn_expand.toggled.connect(self.toggle_content)
        header_layout.addWidget(self.btn_expand)

        layout.addLayout(header_layout)
        
        # Content Display
        # 1. Preview (First 10 words)
        words = text.split()
        preview_text = " ".join(words[:10])
        if len(words) > 10:
            preview_text += "..."
            
        self.lbl_preview = QLabel(preview_text)
        self.lbl_preview.setStyleSheet(f"color: {COLORS['text_main']}; font-size: 12px; border: none; background: transparent;")
        self.lbl_preview.setWordWrap(True)
        layout.addWidget(self.lbl_preview)
        
        # 2. Full Content (Hidden initially)
        self.txt_content = QTextEdit()
        self.txt_content.setReadOnly(True)
        self.txt_content.setPlainText(text)
        # Calculate roughly needed height or fixed max
        self.txt_content.setFixedHeight(120) 
        self.txt_content.setStyleSheet(f"background-color: {COLORS['surface_light']}; color: {COLORS['text_main']}; border: none; font-size: 12px; padding: 5px;")
        self.txt_content.hide()
        layout.addWidget(self.txt_content)

    def toggle_content(self, expanded):
        if expanded:
            self.lbl_preview.hide()
            self.txt_content.show()
        else:
            self.txt_content.hide()
            self.lbl_preview.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and not self.read_only:
            menu = QMenu(self)
            del_action = menu.addAction("Delete Prompt")
            action = menu.exec(event.globalPosition().toPoint())
            if action == del_action:
                self.delete_requested.emit(self.p_id)
        super().mousePressEvent(event)

class SituationPromptManagerDialog(QDialog):
    def __init__(self, situation_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prompt Manager - " + situation_data.get('title', 'Unknown'))
        # User requested wider
        self.resize(900, 700) 
        self.setStyleSheet(f"background-color: #1E1E1E; color: {COLORS['text_main']};")
        
        self.situation_data = situation_data
        self.specific_prompts = situation_data.get('specific_data', {}).get('prompts', []) 
        self.general_manager = PromptManager() 
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QFrame()
        header.setStyleSheet(f"background-color: {COLORS['surface']}; border-bottom: 1px solid {COLORS['border']};")
        header.setFixedHeight(60)
        h_layout = QHBoxLayout(header)
        title = QLabel("Situation Prompt Manager")
        title.setStyleSheet(f"color: {COLORS['primary']}; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        h_layout.addWidget(title)
        layout.addWidget(header)
        
        # ToolBox
        self.toolbox = QToolBox()
        self.toolbox.setStyleSheet(f"""
            QToolBox::tab {{
                background: {COLORS['surface_light']};
                color: {COLORS['text_main']};
                border-radius: 4px;
                padding-left: 10px;
                font-weight: bold;
            }}
            QToolBox::tab:selected {{
                color: {COLORS['accent']};
                background: {COLORS['surface']};
            }}
        """)
        
        # 1. Specific Prompts
        self.page_specific = QWidget()
        self.layout_specific = QVBoxLayout(self.page_specific)
        
        # Add Input Area (Top)
        input_frame = QFrame()
        input_frame.setStyleSheet(f"background-color: {COLORS['surface_light']}; border-radius: 6px; padding: 2px;")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setSpacing(2)
        
        row1 = QHBoxLayout()
        self.inp_spec_title = QLineEdit()
        self.inp_spec_title.setPlaceholderText("New Prompt Title...")
        self.inp_spec_title.setStyleSheet(f"padding: 4px; background-color: {COLORS['surface_light']}; border: 1px solid {COLORS['border']}; font-size: 11px;")
        btn_add_spec = QPushButton("Add")
        btn_add_spec.setFixedSize(60, 25)
        btn_add_spec.setStyleSheet(f"background-color: {COLORS['success']}; padding: 0px; border-radius: 4px; font-weight: bold; color: white; font-size: 11px;")
        btn_add_spec.clicked.connect(self.add_specific_prompt)
        row1.addWidget(self.inp_spec_title)
        row1.addWidget(btn_add_spec)
        
        self.inp_spec_text = QTextEdit()
        self.inp_spec_text.setPlaceholderText("Paste prompt content here...")
        self.inp_spec_text.setFixedHeight(35)
        self.inp_spec_text.setStyleSheet(f"padding: 4px; background-color: {COLORS['surface_light']}; border: 1px solid {COLORS['border']}; font-size: 11px;")
        
        input_layout.addLayout(row1)
        input_layout.addWidget(self.inp_spec_text)
        
        self.layout_specific.addWidget(input_frame)
        
        # Scroll List
        scroll_spec = QScrollArea()
        scroll_spec.setWidgetResizable(True)
        scroll_spec.setFrameShape(QFrame.Shape.NoFrame)
        self.container_specific = QWidget()
        self.vbox_specific = QVBoxLayout(self.container_specific)
        self.vbox_specific.addStretch()
        self.vbox_specific.setSpacing(0)
        scroll_spec.setWidget(self.container_specific)
        self.layout_specific.addWidget(scroll_spec)
        
        self.toolbox.addItem(self.page_specific, "Situation Specific Prompts")
        
        # 2. General Prompts
        self.page_general = QWidget()
        layout_gen = QVBoxLayout(self.page_general)
        
        scroll_gen = QScrollArea()
        scroll_gen.setWidgetResizable(True)
        scroll_gen.setFrameShape(QFrame.Shape.NoFrame)
        self.container_general = QWidget()
        self.vbox_general = QVBoxLayout(self.container_general)
        self.vbox_general.addStretch()
        self.vbox_general.setSpacing(0)
        scroll_gen.setWidget(self.container_general)
        layout_gen.addWidget(scroll_gen)
        
        self.toolbox.addItem(self.page_general, "General Prompts (Global)")
        
        layout.addWidget(self.toolbox)
        
        self.refresh_specific()
        self.refresh_general()

    def refresh_specific(self):
        # Clear (Keep stretch at end)
        while self.vbox_specific.count() > 1:
            item = self.vbox_specific.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        for p in self.specific_prompts:
            w = PromptItemWidget(p['id'], p['title'], p['text'])
            w.delete_requested.connect(self.delete_specific_prompt)
            self.vbox_specific.insertWidget(0, w) # Insert at top

    def refresh_general(self):
        while self.vbox_general.count() > 1:
            item = self.vbox_general.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        for p in self.general_manager.prompts:
            t_display = f"[{p.get('category','Global')}] {p['title']}"
            w = PromptItemWidget(p['id'], t_display, p['text'], read_only=True)
            self.vbox_general.insertWidget(0, w)

    def add_specific_prompt(self):
        t = self.inp_spec_title.text().strip()
        txt = self.inp_spec_text.toPlainText().strip()
        if not t or not txt:
            return
            
        new_p = {
            "id": str(uuid.uuid4()),
            "title": t,
            "text": txt
        }
        self.specific_prompts.append(new_p)
        self.refresh_specific()
        self.inp_spec_title.clear()
        self.inp_spec_text.clear()
        self.save_data()

    def delete_specific_prompt(self, pid):
        self.specific_prompts = [p for p in self.specific_prompts if p['id'] != pid]
        self.refresh_specific()
        self.save_data()

    def save_data(self):
        if 'specific_data' not in self.situation_data:
            self.situation_data['specific_data'] = {}
            
        self.situation_data['specific_data']['prompts'] = self.specific_prompts
        
        if self.parent() and hasattr(self.parent(), 'save_situation_specific_data'):
            self.parent().save_situation_specific_data(self.situation_data['id'], self.situation_data['specific_data'])
