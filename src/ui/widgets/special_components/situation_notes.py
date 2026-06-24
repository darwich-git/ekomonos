import datetime
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QLineEdit, QPushButton, 
    QScrollArea, QFrame, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QAction
from ui.styles import COLORS

class NoteEntryWidget(QFrame):
    delete_requested = pyqtSignal(str) # note_id
    edit_requested = pyqtSignal(str, str, str) # note_id, new_title, new_body
    
    def __init__(self, n_id, date_str, title, body, parent=None):
        super().__init__(parent)
        self.n_id = n_id
        self.title_text = title
        self.body_text = body
        self.is_expanded = False  # Track expansion state for long notes
        self.is_long = False  # Will be set to True if body > 200 chars
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-bottom: 8px;
            }}
            QFrame:hover {{
                border: 1px solid {COLORS['primary']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(5)
        
        # Header: Title (Bold) + Date (Right aligned, Dim)
        header_layout = QHBoxLayout()
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"color: {COLORS['primary']}; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        self.lbl_title.setWordWrap(True)
        # Don't set TextInteractionFlags - let frame handle double-click
        
        lbl_date = QLabel(date_str)
        lbl_date.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; border: none; background: transparent;")
        lbl_date.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        header_layout.addWidget(self.lbl_title, 1) # Stretch title
        header_layout.addWidget(lbl_date, 0)
        
        layout.addLayout(header_layout)
        
        # Body
        if body:
            self.lbl_body = QLabel()
            self.lbl_body.setStyleSheet(f"color: {COLORS['text_main']}; font-size: 13px; border: none; background: transparent;")
            self.lbl_body.setWordWrap(True)
            self.lbl_body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            self.lbl_body.setMinimumWidth(1) # crucial for wrapping in some layouts
            
            # Check if body is long (more than 200 characters)
            if len(body) > 200:
                self.is_long = True
                # Show truncated initially
                truncated = body[:200] + "..."
                self.lbl_body.setText(truncated)
                layout.addWidget(self.lbl_body)
            else:
                self.lbl_body.setText(body)
                layout.addWidget(self.lbl_body)
        else:
            self.lbl_body = None

    def mouseDoubleClickEvent(self, event):
        """Double-click ANYWHERE on note to expand/collapse long notes or edit short notes"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_long:
                # Toggle expand/collapse for long notes
                self.is_expanded = not self.is_expanded
                if self.is_expanded:
                    # Show full text
                    self.lbl_body.setText(self.body_text)
                else:
                    # Show truncated text
                    truncated = self.body_text[:200] + "..."
                    self.lbl_body.setText(truncated)
            else:
                # For short notes, open edit dialog directly
                self.open_edit_dialog()
            event.accept()  # Mark event as handled
            return
        super().mouseDoubleClickEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            from PyQt6.QtWidgets import QApplication
            menu = QMenu(self)
            
            # Copy options
            copy_title_action = menu.addAction("Copy Title")
            copy_body_action = None
            if self.lbl_body:
                copy_body_action = menu.addAction("Copy Body")
            
            menu.addSeparator()
            edit_action = menu.addAction("Edit Entry")
            del_action = menu.addAction("Delete Entry")
            
            action = menu.exec(event.globalPosition().toPoint())
            
            if action == copy_title_action:
                QApplication.clipboard().setText(self.title_text)
            elif copy_body_action and action == copy_body_action:
                QApplication.clipboard().setText(self.body_text)
            elif action == del_action:
                self.delete_requested.emit(self.n_id)
            elif action == edit_action:
                self.open_edit_dialog()
        super().mousePressEvent(event)
    
    def open_edit_dialog(self):
        """Open dialog to edit note"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox
        
        dialog = QDialog(None)  # Use None as parent to avoid issues with parent widget lifecycle
        dialog.setWindowTitle("Edit Note")
        dialog.resize(500, 400)
        dialog.setStyleSheet(f"background-color: {COLORS['surface']}; color: white;")
        
        layout = QVBoxLayout(dialog)
        
        # Title input
        title_label = QLabel("Title:")
        title_label.setStyleSheet("color: white;")
        title_input = QLineEdit(self.title_text)
        title_input.setStyleSheet(f"background-color: {COLORS['surface']}; color: white; padding: 6px; border: 1px solid {COLORS['border']}; font-weight: bold;")
        
        # Body input
        body_label = QLabel("Body:")
        body_label.setStyleSheet("color: white;")
        body_input = QTextEdit(self.body_text)
        body_input.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']}; padding: 6px; border: 1px solid {COLORS['border']};")
        
        layout.addWidget(title_label)
        layout.addWidget(title_input)
        layout.addWidget(body_label)
        layout.addWidget(body_input)
        
        # Buttons - use Ok instead of Save to guarantee accepted signal fires in PyQt6
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        try:
            if dialog.exec():
                new_title = title_input.text().strip()
                new_body = body_input.toPlainText().strip()
                
                # Update display
                self.title_text = new_title or "Note"
                self.body_text = new_body
                self.lbl_title.setText(self.title_text)
                if self.lbl_body:
                    self.lbl_body.setText(self.body_text)
                
                # Emit signal to parent
                self.edit_requested.emit(self.n_id, new_title or "Note", new_body)
        except Exception as e:
            print(f"[EDIT_DIALOG] Error: {e}")
            import traceback
            traceback.print_exc()


class SituationNotesWidget(QWidget):
    """
    Generic widget for Notes, Risks, Shareholders.
    Storage Key determines where in specific_data it saves.
    """
    def __init__(self, situation_data, storage_key="notes_log", parent=None):
        super().__init__(parent)
        self.situation_data = situation_data
        self.storage_key = storage_key
        self.special_situations_widget = None  # Direct reference - set by load_notes_widgets
        
        # Load existing
        self.entries = self.situation_data.get('specific_data', {}).get(self.storage_key, [])
        if not isinstance(self.entries, list): self.entries = []
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Scroll Area for Entries
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(f"background: {COLORS['background']};")
        
        self.container = QWidget()
        self.vbox_entries = QVBoxLayout(self.container)
        self.vbox_entries.addStretch() # Push items up
        self.vbox_entries.setSpacing(0)
        self.scroll.setWidget(self.container)
        
        layout.addWidget(self.scroll, 1) # Expand
        
        # 2. Input Area
        input_frame = QFrame()
        input_frame.setStyleSheet(f"background-color: {COLORS['surface_light']}; border-top: 1px solid {COLORS['border']};")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title Input
        self.inp_title = QLineEdit()
        self.inp_title.setPlaceholderText("Title / Topic...")
        self.inp_title.setStyleSheet(f"background-color: {COLORS['surface']}; color: white; padding: 6px; border: 1px solid {COLORS['border']}; font-weight: bold;")
        
        # Body Input
        self.inp_body = QTextEdit()
        self.inp_body.setPlaceholderText("Paste content or type details here...")
        self.inp_body.setFixedHeight(80)
        self.inp_body.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']}; padding: 6px; border: 1px solid {COLORS['border']};")
        
        # Toolbar / Buttons
        btn_layout = QHBoxLayout()
        
        # Helpers (Symbols)
        symbols = ["★", "⚠", "➜", "✔", "❌"]
        for s in symbols:
            btn = QPushButton(s)
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['accent']}; border: none; font-size: 14px;")
            btn.clicked.connect(lambda checked, sym=s: self.insert_symbol(sym))
            btn_layout.addWidget(btn)
            
        btn_layout.addStretch()
        
        self.btn_add = QPushButton("Add Entry")
        self.btn_add.setStyleSheet(f"background-color: {COLORS['success']}; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        self.btn_add.clicked.connect(self.add_entry)
        btn_layout.addWidget(self.btn_add)
        
        input_layout.addWidget(self.inp_title)
        input_layout.addWidget(self.inp_body)
        input_layout.addLayout(btn_layout)
        
        layout.addWidget(input_frame)
        
        self.refresh_entries()

    def insert_symbol(self, symbol):
        self.inp_body.insertPlainText(symbol + " ")
        self.inp_body.setFocus()

    def refresh_entries(self):
        # Clear (keep stretch)
        while self.vbox_entries.count() > 1:
            item = self.vbox_entries.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        # Sort by date desc (newest first)? User said "me vaya insertando y separando las fechas"
        # Usually scrolling down -> Oldest to Newest? Or Blog style (Newest top)?
        # Let's do Newest Top (insert at 0)
        sorted_entries = sorted(self.entries, key=lambda x: x['date'], reverse=True) # Newest first

        
        # Wait, if I use addStretch at TOP, then elements are pushed down.
        # If I use addStretch at BOTTOM, elements push up.
        # Current layout: addStretch() is last item.
        # So inserting at 0 puts it at Top.
        # If I want chronological (Old -> New), I should iterate chronologically and insert at 0? No that reverses it.
        # I want:
        # [Log 1]
        # [Log 2]
        # [Log 3]
        # <Input>
        
        # So I should Append widgets before the stretch?
        # Actually, let's remove stretch and use top-alignment via layout?
        # If I want items to start at Top, just addWidget sequentially. 
        # If I addStretch at the end, they stack top-down.
        
        self.vbox_entries.removeItem(self.vbox_entries.itemAt(self.vbox_entries.count()-1)) # Remove stretch temporarily
        
        for entry in sorted_entries:
            w = NoteEntryWidget(entry['id'], entry['date'], entry['title'], entry['body'])
            w.delete_requested.connect(self.delete_entry)
            w.edit_requested.connect(self.edit_entry)  # CRITICAL: Connect edit signal!
            self.vbox_entries.addWidget(w)

            
        self.vbox_entries.addStretch() # Re-add stretch at bottom

    def add_entry(self):
        title = self.inp_title.text().strip()
        body = self.inp_body.toPlainText().strip()
        
        if not title and not body: return
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        new_entry = {
            "id": str(uuid.uuid4()),
            "date": now_str,
            "title": title or "Note",
            "body": body
        }
        
        self.entries.append(new_entry)
        self.save_data()
        self.refresh_entries()
        
        # Scroll to top so the new entry is visible
        self.scroll.verticalScrollBar().setValue(0)

        
        self.inp_title.clear()
        self.inp_body.clear()

    def delete_entry(self, nid):
        print(f"[DELETE_ENTRY] Deleting entry {nid}")
        self.entries = [e for e in self.entries if e['id'] != nid]
        self.save_data()
        self.refresh_entries()
    
    def edit_entry(self, entry_id, new_title, new_body):
        """Handle editing an existing entry"""
        print(f"[EDIT_ENTRY] Editing entry {entry_id}")
        print(f"[EDIT_ENTRY] New title: {new_title}")
        print(f"[EDIT_ENTRY] New body length: {len(new_body)}")
        
        # Find and update the entry
        for entry in self.entries:
            if entry['id'] == entry_id:
                entry['title'] = new_title
                entry['body'] = new_body
                print(f"[EDIT_ENTRY] Updated entry in memory")
                break
        
        # Save changes to database
        self.save_data()
        print(f"[EDIT_ENTRY] Saved to database")

    def save_data(self):
        print(f"\n[SAVE_DATA] Called for storage_key: {self.storage_key}")
        print(f"[SAVE_DATA] Entries to save: {len(self.entries)}")
        
        if 'specific_data' not in self.situation_data:
            self.situation_data['specific_data'] = {}
            print(f"[SAVE_DATA] Created new specific_data dict")
            
        self.situation_data['specific_data'][self.storage_key] = self.entries
        print(f"[SAVE_DATA] Updated situation_data[specific_data][{self.storage_key}]")
        
        # CRITICAL FIX: Use direct reference first, fallback to parent walking
        save_widget = None
        
        if self.special_situations_widget:
            print(f"[SAVE_DATA] Using direct reference to SpecialSituationsWidget")
            save_widget = self.special_situations_widget
        else:
            # Fallback: Walk parent tree
            print(f"[SAVE_DATA] No direct reference, walking parent tree...")
            parent = self.parent()
            print(f"[SAVE_DATA] Parent: {type(parent).__name__ if parent else 'None'}")
            print(f"[SAVE_DATA] Has save method: {hasattr(parent, 'save_situation_specific_data') if parent else False}")
            
            if parent and hasattr(parent, 'save_situation_specific_data'):
                p = parent 
                level = 0
                while p:
                    print(f"[SAVE_DATA]   L{level}: {type(p).__name__} -> has_method={hasattr(p, 'save_situation_specific_data')}")
                    if hasattr(p, 'save_situation_specific_data'):
                        save_widget = p
                        break
                    p = p.parent()
                    level += 1
                    if level > 20:
                        print(f"[SAVE_DATA] Stopped at level 20")
                        break
        
        if save_widget:
            print(f"[SAVE_DATA] Found save widget: {type(save_widget).__name__}")
            print(f"[SAVE_DATA] Calling save_situation_specific_data...")
            try:
                result = save_widget.save_situation_specific_data(self.situation_data['id'], self.situation_data['specific_data'])
                print(f"[SAVE_DATA] Save returned: {result}")
                
                if not result:
                     from PyQt6.QtWidgets import QMessageBox
                     QMessageBox.warning(self, "Save Error", "Failed to save notes to database. Please check logs.")
                     
            except Exception as e:
                print(f"[SAVE_DATA] ERROR: {e}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Save Error", f"Error saving notes:\n{str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[SAVE_DATA] *** WARNING: No save widget found! Data NOT saved! ***")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Save Error", "Could not find parent widget to save data. Notes will be lost on exit.")
