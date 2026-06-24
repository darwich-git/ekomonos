import json
import os
import uuid
import random
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QMenu, QMessageBox, QWidget, QFrame, QApplication, QFormLayout, 
    QComboBox, QListWidget, QListWidgetItem, QInputDialog, QStackedWidget,
    QColorDialog, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QSize, QEvent
from PyQt6.QtGui import QFont, QColor, QCursor, QPainter, QIcon

DEFAULT_COLORS = ["#FF5722", "#4CAF50", "#2196F3", "#9C27B0", "#E91E63", "#00BCD4", "#FFC107", "#8BC34A"]

class PromptManager:
    def __init__(self, data_path="data/prompts.json"):
        self.data_path = data_path
        self.data = {"categories": [], "prompts": []}
        self.load()

    def load(self):
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        cats = set([p.get('category') for p in content if p.get('category')])
                        self.data = {
                            "categories": [{"name": c, "color": random.choice(DEFAULT_COLORS)} for c in sorted(list(cats))],
                            "prompts": content
                        }
                        self.save()
                    else:
                        self.data = content
                        if "categories" not in self.data:
                            self.data["categories"] = []
                        else:
                            new_cats = []
                            for c in self.data["categories"]:
                                if isinstance(c, str):
                                    new_cats.append({"name": c, "color": random.choice(DEFAULT_COLORS)})
                                else:
                                    new_cats.append(c)
                            self.data["categories"] = new_cats

                        if "prompts" not in self.data:
                            self.data["prompts"] = []
            except Exception as e:
                print(f"Error loading prompts: {e}")
                self.data = {"categories": [], "prompts": []}
        else:
            self.data = {"categories": [], "prompts": []}

    def save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        try:
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving prompts: {e}")

    @property
    def prompts(self):
        return self.data["prompts"]

    def add_prompt(self, title, category, text):
        new_p = {
            "id": str(uuid.uuid4()),
            "title": title,
            "category": category,
            "text": text,
            "created_at": str(os.path.getmtime(self.data_path) if os.path.exists(self.data_path) else 0)
        }
        self.data["prompts"].append(new_p)
        self._ensure_category_exists(category)
        self.save()
        return new_p

    def update_prompt(self, pid, title, category, text):
        for p in self.data["prompts"]:
            if p['id'] == pid:
                p['title'] = title
                p['category'] = category
                p['text'] = text
                self._ensure_category_exists(category)
                self.save()
                return True
        return False

    def _ensure_category_exists(self, category_name):
        if not category_name: return
        for c in self.data["categories"]:
            if c["name"] == category_name:
                return
        self.data["categories"].append({"name": category_name, "color": random.choice(DEFAULT_COLORS)})
        
    def delete_prompt(self, pid):
        self.data["prompts"] = [p for p in self.data["prompts"] if p['id'] != pid]
        self.save()

    def get_categories(self):
        return self.data.get("categories", [])

    def add_category(self, name, color=None):
        if not color: color = random.choice(DEFAULT_COLORS)
        for c in self.data["categories"]:
            if c["name"] == name:
                return False
        self.data["categories"].append({"name": name, "color": color})
        self.save()
        return True

    def rename_category(self, old_name, new_name):
        for c in self.data["categories"]:
            if c["name"] == old_name:
                c["name"] = new_name
                for p in self.data["prompts"]:
                    if p.get('category') == old_name:
                        p['category'] = new_name
                self.save()
                return True
        return False

    def change_category_color(self, name, new_color):
        for c in self.data["categories"]:
            if c["name"] == name:
                c["color"] = new_color
                self.save()
                return True
        return False

    def delete_category(self, name):
        for c in self.data["categories"]:
            if c["name"] == name:
                self.data["categories"].remove(c)
                for p in self.data["prompts"]:
                    if p.get('category') == name:
                        p['category'] = ""
                self.save()
                return True
        return False

    def reorder_categories(self, new_order_names):
        name_to_cat = {c['name']: c for c in self.data["categories"]}
        ordered_cats = []
        for name in new_order_names:
            if name in name_to_cat:
                ordered_cats.append(name_to_cat[name])
                del name_to_cat[name]
        for cat in name_to_cat.values():
            ordered_cats.append(cat)
        self.data["categories"] = ordered_cats
        self.save()

    def reorder_prompts(self, new_order_ids):
        id_to_prompt = {p['id']: p for p in self.data["prompts"]}
        ordered_prompts = []
        for pid in new_order_ids:
            if pid in id_to_prompt:
                ordered_prompts.append(id_to_prompt[pid])
                del id_to_prompt[pid]
        for p in id_to_prompt.values():
            ordered_prompts.append(p)
        self.data["prompts"] = ordered_prompts
        self.save()

class PromptEditDialog(QDialog):
    def __init__(self, parent=None, title="", category="", text="", existing_categories=None):
        super().__init__(parent)
        self.setWindowTitle("Legacy Prompt Editor")
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel("This dialog is obsolete. Please use the Notion-like editor."))
    def get_data(self): return "", "", ""

class PromptLibraryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gemini Prompt Library")
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel("Legacy Dialog. Please use the embedded view."))


# ──────────────────────────────────────────────────────────────────────────────
#  NOTION-STYLE UI
# ──────────────────────────────────────────────────────────────────────────────

class ClickableSearch(QLineEdit):
    """A search bar that detects clicks to reset category selection."""
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if hasattr(self, 'on_click') and self.on_click:
            self.on_click()

class ReorderableListWidget(QListWidget):
    """QListWidget that supports drag & drop reordering and notifies on drop."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        
    def dropEvent(self, event):
        super().dropEvent(event)
        if hasattr(self, 'on_order_changed') and self.on_order_changed:
            self.on_order_changed()

class CategoryCreationDialog(QDialog):
    """Custom dialog to select a folder name and color."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva Carpeta")
        self.setFixedSize(300, 200)
        self.setStyleSheet("QDialog { background: #1E1E1E; color: #EEE; } QLabel { color: #BBB; } QLineEdit { background: #121212; color: #FFF; border: 1px solid #333; padding: 6px; border-radius: 4px; }")
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Nombre:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        layout.addSpacing(10)
        layout.addWidget(QLabel("Color:"))
        
        color_lay = QHBoxLayout()
        self.selected_color = DEFAULT_COLORS[0]
        self.color_btns = []
        for c in DEFAULT_COLORS:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            border = "2px solid #FFF" if c == self.selected_color else "none"
            btn.setStyleSheet(f"QPushButton {{ background: {c}; border-radius: 12px; border: {border}; }}")
            btn.clicked.connect(lambda checked, col=c, b=btn: self._select_color(col, b))
            self.color_btns.append(btn)
            color_lay.addWidget(btn)
        color_lay.addStretch()
        layout.addLayout(color_lay)
        
        layout.addSpacing(15)
        btns = QHBoxLayout()
        btns.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("QPushButton { background: #333; color: #FFF; border: none; padding: 6px 12px; border-radius: 4px; } QPushButton:hover { background: #444; }")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Crear")
        btn_save.setStyleSheet("QPushButton { background: #FF9800; color: #111; border: none; padding: 6px 12px; border-radius: 4px; font-weight: bold; } QPushButton:hover { background: #FFB74D; }")
        btn_save.clicked.connect(self.accept)
        
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)
        
    def _select_color(self, color, button):
        self.selected_color = color
        for b in self.color_btns:
            col = b.styleSheet().split("background: ")[1].split(";")[0]
            b.setStyleSheet(f"QPushButton {{ background: {col}; border-radius: 12px; border: none; }}")
        button.setStyleSheet(f"QPushButton {{ background: {color}; border-radius: 12px; border: 2px solid #FFF; }}")
        
    def get_data(self):
        return self.name_edit.text().strip(), self.selected_color

class PromptListItemWidget(QFrame):
    """Clean row item for a prompt, with hover copy button."""
    def __init__(self, prompt_data, parent_list, parent=None):
        super().__init__(parent)
        self.prompt_data = prompt_data
        self.parent_list = parent_list
        
        self.setFixedHeight(44)
        self.setStyleSheet("""
            QFrame { background: transparent; border-bottom: 1px solid #1A1A1A; border-radius: 6px; }
            QFrame:hover { background: #222222; border-bottom: none; }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        cat_name = prompt_data.get('category', '')
        dot_color = "#999999" # Light grey default
        for c in self.parent_list.manager.get_categories():
            if c['name'] == cat_name:
                dot_color = c.get('color', '#999999')
                break
                
        icon_lbl = QLabel("●")
        icon_lbl.setStyleSheet(f"color: {dot_color}; border: none; background: transparent; font-size: 18px;")
        layout.addWidget(icon_lbl)
        
        self.title_lbl = QLabel(prompt_data['title'])
        self.title_lbl.setStyleSheet("color: #EAEAEA; font-size: 15px; font-weight: 500; border: none; background: transparent;")
        layout.addWidget(self.title_lbl, stretch=1)
        
        self.actions_widget = QWidget()
        self.actions_widget.setStyleSheet("background: transparent; border: none;")
        actions_lay = QHBoxLayout(self.actions_widget)
        actions_lay.setContentsMargins(0,0,0,0)
        actions_lay.setSpacing(8)
        
        self.btn_copy = QPushButton("Copiar")
        self.btn_copy.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_copy.setFixedSize(60, 28)
        self.btn_copy.setStyleSheet("""
            QPushButton { background: #333333; color: #FFFFFF; border: 1px solid #444; border-radius: 6px; font-size: 12px; }
            QPushButton:hover { background: #FF9800; color: #111; border: 1px solid #FF9800; }
        """)
        self.btn_copy.clicked.connect(self._copy_content)
        actions_lay.addWidget(self.btn_copy)
        
        layout.addWidget(self.actions_widget)
        self.actions_widget.hide()

    def enterEvent(self, event):
        self.actions_widget.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.actions_widget.hide()
        super().leaveEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_list._open_editor(self.prompt_data)
        super().mouseDoubleClickEvent(event)
        
    def _copy_content(self):
        QApplication.clipboard().setText(self.prompt_data['text'])
        self.btn_copy.setText("✓")
        self.btn_copy.setStyleSheet("QPushButton { background: #4CAF50; color: #FFFFFF; border: none; border-radius: 6px; font-size: 12px; }")
        QTimer.singleShot(1500, self._reset_copy_btn)
        
    def _reset_copy_btn(self):
        self.btn_copy.setText("Copiar")
        self.btn_copy.setStyleSheet("""
            QPushButton { background: #333333; color: #FFFFFF; border: 1px solid #444; border-radius: 6px; font-size: 12px; }
            QPushButton:hover { background: #FF9800; color: #111; border: 1px solid #FF9800; }
        """)

class FolderListWidgetItem(QFrame):
    def __init__(self, cat_dict, parent=None):
        super().__init__(parent)
        self.cat_name = cat_dict['name']
        self.cat_color = cat_dict.get('color', '#999999')
        
        self.setFixedHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {self.cat_color}; font-size: 18px; background: transparent;")
        layout.addWidget(self.dot)
        
        self.lbl = QLabel(self.cat_name)
        self.lbl.setStyleSheet("color: #DDDDDD; font-size: 15px; background: transparent;")
        layout.addWidget(self.lbl, stretch=1)
        self.setStyleSheet("QFrame { background: transparent; border: none; }")

class PromptLibraryWidget(QWidget):
    """Notion-style 2-panel prompt library."""

    _CAT_ALL = "Todos los Prompts"
    _CAT_UNCATEGORIZED = "Inbox (Sin Carpeta)"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = PromptManager()
        self._current_category_val = self._CAT_ALL
        self._selected_prompt = None   
        self._init_ui()
        self._reload_sidebar()

    def _init_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── PANEL 1: SIDEBAR (Folders) ────────────────────────────────────────
        left = QFrame()
        left.setFixedWidth(260)
        left.setStyleSheet("background:#121212; border-right: 1px solid #222;")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(15, 25, 15, 20)
        left_lay.setSpacing(15)

        self.sidebar_search = ClickableSearch()
        self.sidebar_search.setPlaceholderText("🔍 Todos los Prompts")
        self.sidebar_search.on_click = self._on_search_clicked
        self.sidebar_search.textChanged.connect(self._on_global_search)
        left_lay.addWidget(self.sidebar_search)

        hdr_folders_lay = QHBoxLayout()
        hdr_folders_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        hdr_folders = QLabel("CARPETAS")
        hdr_folders.setStyleSheet("color: #666666; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        hdr_folders_lay.addWidget(hdr_folders)
        
        hdr_folders_lay.addStretch()
        
        btn_add_cat = QPushButton("+")
        btn_add_cat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_add_cat.setFixedSize(28, 28)
        btn_add_cat.setStyleSheet("""
            QPushButton { background: #333333; color: #FF9800; font-size: 22px; border: none; border-radius: 6px; font-weight: bold; padding: 0; margin: 0; } 
            QPushButton:hover { background: #444444; color: #FFB74D; }
        """)
        btn_add_cat.clicked.connect(self._add_category)
        hdr_folders_lay.addWidget(btn_add_cat)
        left_lay.addLayout(hdr_folders_lay)

        self._cat_list = ReorderableListWidget()
        self._cat_list.setSpacing(4)
        self._cat_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._cat_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._cat_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item { border: none; padding: 0px; margin: 0px; border-radius: 6px; }
            QListWidget::item:selected { background: #262626; }
            QListWidget::item:hover:!selected { background: #1C1C1C; }
        """)
        self._cat_list.currentRowChanged.connect(self._on_cat_list_changed)
        self._cat_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._cat_list.customContextMenuRequested.connect(self._cat_context_menu)
        self._cat_list.on_order_changed = self._save_category_order
        left_lay.addWidget(self._cat_list)
        root.addWidget(left)

        # ── PANEL 2: MAIN AREA (Stacked) ──────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: #181818;")
        root.addWidget(self.stack, stretch=1)
        
        self.page_folder = QWidget()
        folder_lay = QVBoxLayout(self.page_folder)
        folder_lay.setContentsMargins(60, 50, 60, 40)
        folder_lay.setSpacing(20)
        
        header_row = QHBoxLayout()
        self.lbl_folder_title = QLabel("Todos los Prompts")
        self.lbl_folder_title.setStyleSheet("color: #FFFFFF; font-size: 28px; font-weight: bold;")
        header_row.addWidget(self.lbl_folder_title)
        
        header_row.addStretch()
        
        btn_new_prompt = QPushButton("Nuevo")
        btn_new_prompt.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_new_prompt.setFixedSize(80, 32)
        btn_new_prompt.setStyleSheet("QPushButton { background: #FF9800; color: #111; border: none; border-radius: 16px; font-weight: bold; font-size: 13px; } QPushButton:hover { background: #FFB74D; }")
        btn_new_prompt.clicked.connect(self._create_new_prompt)
        header_row.addWidget(btn_new_prompt)
        
        folder_lay.addLayout(header_row)
        
        folder_lay.addSpacing(10)
        
        self._prompt_list = ReorderableListWidget()
        self._prompt_list.setSpacing(4)
        self._prompt_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._prompt_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._prompt_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item { padding: 0px; margin: 0px; border: none; }
            QListWidget::item:selected { background: transparent; }
        """)
        self._prompt_list._open_editor = self._open_editor
        self._prompt_list.on_order_changed = self._save_prompt_order
        folder_lay.addWidget(self._prompt_list, stretch=1)
        
        self.stack.addWidget(self.page_folder)

        self.page_editor = QWidget()
        editor_lay = QVBoxLayout(self.page_editor)
        editor_lay.setContentsMargins(60, 30, 60, 40)
        editor_lay.setSpacing(15)
        
        top_bar = QHBoxLayout()
        btn_back = QPushButton("← Volver")
        btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_back.setFixedSize(90, 32)
        btn_back.setStyleSheet("QPushButton { background: transparent; color: #A0A0A0; font-size: 14px; border: none; text-align: left; } QPushButton:hover { color: #FFFFFF; }")
        btn_back.clicked.connect(self._close_editor)
        top_bar.addWidget(btn_back)
        top_bar.addStretch()
        
        btn_del_prompt = QPushButton("Eliminar")
        btn_del_prompt.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_del_prompt.setFixedSize(80, 32)
        btn_del_prompt.setStyleSheet("QPushButton { background: transparent; color: #E53935; font-size: 13px; border: 1px solid #333; border-radius: 6px; } QPushButton:hover { border: 1px solid #E53935; }")
        btn_del_prompt.clicked.connect(self._delete_current_prompt)
        top_bar.addWidget(btn_del_prompt)
        editor_lay.addLayout(top_bar)
        
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("Título sin nombre")
        self.edit_title.setStyleSheet("""
            QLineEdit { background: transparent; color: #FFFFFF; border: none; font-size: 32px; font-weight: bold; padding: 0; }
            QLineEdit:focus { border-bottom: 1px solid #333; }
        """)
        editor_lay.addWidget(self.edit_title)
        
        cat_row = QHBoxLayout()
        cat_icon = QLabel("📁")
        cat_icon.setStyleSheet("color: #888; font-size: 14px; background: transparent;")
        cat_row.addWidget(cat_icon)
        
        self.edit_cat = QComboBox()
        self.edit_cat.setEditable(True)
        self.edit_cat.setStyleSheet("""
            QComboBox { background: transparent; color: #888; border: none; font-size: 14px; padding: 0; }
            QComboBox::drop-down { border: none; }
            QComboBox:focus { border: 1px solid #333; border-radius: 4px; padding: 2px 6px; background: #121212; }
        """)
        self.edit_cat.setMinimumWidth(200)
        cat_row.addWidget(self.edit_cat)
        cat_row.addStretch()
        editor_lay.addLayout(cat_row)
        
        editor_lay.addSpacing(10)
        
        self.edit_text = QTextEdit()
        self.edit_text.setPlaceholderText("Empieza a escribir aquí...")
        self.edit_text.setStyleSheet("""
            QTextEdit { background: transparent; color: #DDDDDD; border: none; font-size: 15px; line-height: 1.6; font-family: 'Segoe UI', Arial, sans-serif; }
            QTextEdit:focus { background: #1C1C1C; border-radius: 8px; padding: 10px; }
        """)
        editor_lay.addWidget(self.edit_text, stretch=1)
        
        self.stack.addWidget(self.page_editor)

    def _on_search_clicked(self):
        if self._current_category_val != self._CAT_ALL:
            self._current_category_val = self._CAT_ALL
            self._cat_list.blockSignals(True)
            self._cat_list.clearSelection()
            self._cat_list.blockSignals(False)
            self.lbl_folder_title.setText(self._CAT_ALL)
            self.sidebar_search.setText("")
            self._update_search_style()
            self._load_prompts()
            self.stack.setCurrentIndex(0)

    def _on_global_search(self, text):
        if text.strip() and self._current_category_val != self._CAT_ALL:
            self._current_category_val = self._CAT_ALL
            self._cat_list.blockSignals(True)
            self._cat_list.clearSelection()
            self._cat_list.blockSignals(False)
            self.lbl_folder_title.setText("Resultados de Búsqueda")
            self._update_search_style()
        elif not text.strip() and self._current_category_val == self._CAT_ALL:
            self.lbl_folder_title.setText(self._CAT_ALL)
            
        self._load_prompts()

    # ── Drag and Drop Ordering ────────────────────────────────────────────────
    def _save_category_order(self):
        new_order = []
        for i in range(self._cat_list.count()):
            cat_name = self._cat_list.item(i).data(Qt.ItemDataRole.UserRole)
            if cat_name != self._CAT_UNCATEGORIZED:
                new_order.append(cat_name)
        self.manager.reorder_categories(new_order)
        self._reload_sidebar()

    def _save_prompt_order(self):
        new_order = []
        for i in range(self._prompt_list.count()):
            p = self._prompt_list.item(i).data(Qt.ItemDataRole.UserRole)
            if p: new_order.append(p['id'])
        
        all_ids = [p['id'] for p in self.manager.prompts]
        displayed_ids_set = set(new_order)
        
        final_order = []
        new_order_idx = 0
        for pid in all_ids:
            if pid in displayed_ids_set:
                final_order.append(new_order[new_order_idx])
                new_order_idx += 1
            else:
                final_order.append(pid)
                
        self.manager.reorder_prompts(final_order)
        self._load_prompts()

    # ── Sidebar & Navigation ──────────────────────────────────────────────────
    def _reload_sidebar(self):
        self._cat_list.blockSignals(True)
        self._cat_list.clear()
        
        cats = self.manager.get_categories()
        for c in cats:
            item = QListWidgetItem(self._cat_list)
            widget = FolderListWidgetItem(c)
            item.setSizeHint(QSize(200, 40))
            item.setData(Qt.ItemDataRole.UserRole, c['name'])
            self._cat_list.addItem(item)
            self._cat_list.setItemWidget(item, widget)
            
        item_inbox = QListWidgetItem(self._cat_list)
        widget_inbox = FolderListWidgetItem({"name": self._CAT_UNCATEGORIZED, "color": "#999999"})
        item_inbox.setSizeHint(QSize(200, 40))
        item_inbox.setData(Qt.ItemDataRole.UserRole, self._CAT_UNCATEGORIZED)
        item_inbox.setFlags(item_inbox.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
        self._cat_list.addItem(item_inbox)
        self._cat_list.setItemWidget(item_inbox, widget_inbox)
                
        self._restore_cat_selection()
        self._cat_list.blockSignals(False)
        self._update_search_style()

    def _restore_cat_selection(self):
        if self._current_category_val == self._CAT_ALL:
            self._cat_list.clearSelection()
            return
            
        found = False
        for i in range(self._cat_list.count()):
            cat_name = self._cat_list.item(i).data(Qt.ItemDataRole.UserRole)
            if cat_name == self._current_category_val:
                self._cat_list.setCurrentRow(i)
                found = True
                break
        if not found:
            self._current_category_val = self._CAT_ALL
            self._cat_list.clearSelection()

    def _update_search_style(self):
        if self._current_category_val == self._CAT_ALL:
            self.sidebar_search.setStyleSheet("""
                QLineEdit { background: #222; color: #FFF; border: 1px solid #555; border-radius: 18px; padding: 0 15px; font-size: 14px; font-weight: bold; height: 36px; }
                QLineEdit:focus { border: 1px solid #FF9800; }
            """)
        else:
            self.sidebar_search.setStyleSheet("""
                QLineEdit { background: transparent; color: #A0A0A0; border: 1px solid #333; border-radius: 18px; padding: 0 15px; font-size: 14px; font-weight: bold; height: 36px; }
                QLineEdit:focus { border: 1px solid #FF9800; color: #FFF; }
            """)

    def _select_category(self, cat_name):
        self._current_category_val = cat_name
        
        if cat_name == self._CAT_ALL:
            self._cat_list.blockSignals(True)
            self._cat_list.clearSelection()
            self._cat_list.blockSignals(False)
            self.lbl_folder_title.setText(self._CAT_ALL)
        else:
            self.lbl_folder_title.setText(cat_name)
            
        self._update_search_style()
        self.sidebar_search.blockSignals(True)
        self.sidebar_search.clear()
        self.sidebar_search.blockSignals(False)
        
        self._load_prompts()
        self.stack.setCurrentIndex(0)

    def _on_cat_list_changed(self, row):
        item = self._cat_list.item(row)
        if item:
            cat_name = item.data(Qt.ItemDataRole.UserRole)
            self._select_category(cat_name)

    def _load_prompts(self):
        self._prompt_list.blockSignals(True)
        self._prompt_list.clear()
        
        cat = self._current_category_val
        q = self.sidebar_search.text().lower()
        
        for p in self.manager.prompts:
            p_cat = p.get('category', '').strip()
            
            if cat == self._CAT_UNCATEGORIZED:
                if p_cat != "": continue
            elif cat != self._CAT_ALL:
                if p_cat != cat: continue
                
            if q and q not in p['title'].lower() and q not in p['text'].lower():
                continue
                
            item = QListWidgetItem(self._prompt_list)
            widget = PromptListItemWidget(p, self)
            item.setSizeHint(QSize(300, 44))
            item.setData(Qt.ItemDataRole.UserRole, p)
            self._prompt_list.addItem(item)
            self._prompt_list.setItemWidget(item, widget)
            
        self._prompt_list.blockSignals(False)

    # ── Category Context Menu ─────────────────────────────────────────────────
    def _cat_context_menu(self, pos):
        item = self._cat_list.itemAt(pos)
        if not item: return
        cat_name = item.data(Qt.ItemDataRole.UserRole)
        if cat_name == self._CAT_UNCATEGORIZED: return
            
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background:#1E1E1E; color:#FFFFFF; border: 1px solid #333333; border-radius: 4px; padding: 4px; } 
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background:#2A2A2A; color:#FFFFFF; }
        """)
        ren_action = menu.addAction("Renombrar")
        color_action = menu.addAction("Cambiar Color")
        del_action = menu.addAction("Eliminar")
        
        action = menu.exec(self._cat_list.mapToGlobal(pos))
        if action == ren_action:
            new_name, ok = QInputDialog.getText(self, "Renombrar Carpeta", "Nuevo nombre:", text=cat_name)
            if ok and new_name.strip() and new_name.strip() != cat_name:
                self.manager.rename_category(cat_name, new_name.strip())
                if self._current_category_val == cat_name:
                    self._current_category_val = new_name.strip()
                self._reload_sidebar()
        elif action == color_action:
            color = QColorDialog.getColor(Qt.GlobalColor.white, self, "Elige un color para el icono")
            if color.isValid():
                self.manager.change_category_color(cat_name, color.name())
                self._reload_sidebar()
        elif action == del_action:
            confirm = QMessageBox.question(self, "Eliminar", f"¿Eliminar carpeta '{cat_name}'?\nLos prompts no se borrarán, irán a Inbox.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                self.manager.delete_category(cat_name)
                if self._current_category_val == cat_name:
                    self._current_category_val = self._CAT_ALL
                self._reload_sidebar()

    def _add_category(self):
        dialog = CategoryCreationDialog(self)
        if dialog.exec():
            name, color = dialog.get_data()
            if name:
                self.manager.add_category(name, color)
                self._reload_sidebar()
                self._select_category(name)

    # ── Editor View ───────────────────────────────────────────────────────────
    def _create_new_prompt(self):
        self._selected_prompt = None
        self.edit_title.setText("")
        self.edit_text.setPlainText("")
        
        self.edit_cat.clear()
        self.edit_cat.addItems([c['name'] for c in self.manager.get_categories()])
        
        if self._current_category_val != self._CAT_ALL and self._current_category_val != self._CAT_UNCATEGORIZED:
            self.edit_cat.setCurrentText(self._current_category_val)
        else:
            self.edit_cat.setCurrentText("")
            
        self.stack.setCurrentIndex(1)
        self.edit_text.setFocus()

    def _open_editor(self, prompt_data):
        self._selected_prompt = prompt_data
        self.edit_title.setText(prompt_data['title'])
        self.edit_text.setPlainText(prompt_data['text'])
        
        self.edit_cat.clear()
        self.edit_cat.addItems([c['name'] for c in self.manager.get_categories()])
        self.edit_cat.setCurrentText(prompt_data.get('category', ''))
        
        self.stack.setCurrentIndex(1)

    def _close_editor(self):
        new_title = self.edit_title.text().strip()
        new_text = self.edit_text.toPlainText().strip()
        new_cat = self.edit_cat.currentText().strip()
        
        if not new_title and not new_text:
            self.stack.setCurrentIndex(0)
            return
            
        if not new_title: new_title = "Sin Título"
        
        if self._selected_prompt:
            self.manager.update_prompt(self._selected_prompt['id'], new_title, new_cat, new_text)
        else:
            self.manager.add_prompt(new_title, new_cat, new_text)
            
        self._reload_sidebar()
        self.stack.setCurrentIndex(0)

    def _delete_current_prompt(self):
        if self._selected_prompt:
            confirm = QMessageBox.question(self, "Eliminar", "¿Estás seguro de eliminar este prompt?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                self.manager.delete_prompt(self._selected_prompt['id'])
                self._selected_prompt = None
                self._reload_sidebar()
                self.stack.setCurrentIndex(0)
        else:
            self.stack.setCurrentIndex(0)
