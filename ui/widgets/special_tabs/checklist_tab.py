from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, QGroupBox, QCheckBox, QTextEdit, QLabel
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import pyqtSignal
from ui.styles import COLORS
from core.special_definitions import CHECKLIST_GLOBAL, CHECKLIST_BY_TYPE, resolve_type

class SituationChecklistWidget(QWidget):
    checklist_updated = pyqtSignal(str) # Emits the tab label text

    def __init__(self, parent_special=None, parent=None):
        super().__init__(parent)
        self.parent_special = parent_special
        self.current_situation_id = None
        self.current_data = None
        self._checklist_widgets = {}
        
        self.init_ui()

    def init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        self._checklist_container = QWidget()
        self._checklist_container.setStyleSheet("background: transparent;")
        
        self._checklist_main_layout = QVBoxLayout(self._checklist_container)
        self._checklist_main_layout.setSpacing(4)
        self._checklist_main_layout.setContentsMargins(8, 8, 8, 8)
        
        scroll.setWidget(self._checklist_container)
        outer.addWidget(scroll)

    def load_data(self, situation_data):
        self.current_data = situation_data
        self.current_situation_id = situation_data.get('id')

        # Clean old
        while self._checklist_main_layout.count():
            item = self._checklist_main_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
                
        self._checklist_widgets = {}

        sdata  = situation_data.get('specific_data', {})
        stype  = resolve_type(situation_data.get('strategy_type', 'Generic'))
        saved_global   = sdata.get('checklist_global',   {})
        saved_specific = sdata.get('checklist_specific', {})

        _grp_style = (
            f"QGroupBox {{ font-weight: bold; color: {COLORS['primary']};"
            f" border: 1px solid {COLORS['border']}; border-radius:6px;"
            f" margin-top:12px; padding-top:12px; background:{COLORS['surface']}; }}"
            f" QGroupBox::title {{ subcontrol-origin: margin; left:10px; padding: 0 4px; }}"
        )

        def _build_check_section(title, items, saved_data, section_key):
            if not items: return
            
            grp = QGroupBox(title)
            grp.setStyleSheet(_grp_style)
            grp_layout = QVBoxLayout(grp)
            grp_layout.setSpacing(2)
            
            for key, label_text in items:
                item_state = saved_data.get(key, {})
                checked    = bool(item_state.get('checked', False))
                note_txt   = str(item_state.get('notes', ''))
                
                row_w = QWidget()
                row_w.setStyleSheet("background:transparent;")
                row_layout = QVBoxLayout(row_w)
                row_layout.setContentsMargins(0, 2, 0, 2)
                row_layout.setSpacing(2)
                
                chk = QCheckBox(label_text)
                chk.setChecked(checked)
                c = "#2ECC71" if checked else COLORS['text_main']
                chk.setStyleSheet(
                    f"QCheckBox {{ color: {c}; font-size:13px; background:transparent; spacing:8px; }}"
                    f" QCheckBox::indicator {{ width:16px; height:16px; border-radius:3px; border:1px solid {COLORS['border']}; }}"
                    f" QCheckBox::indicator:checked {{ background:#2ECC71; border-color:#2ECC71; }}"
                )
                
                notes_edit = QTextEdit()
                notes_edit.setPlaceholderText("Añade notas o evidencia aquí...")
                notes_edit.setPlainText(note_txt)
                notes_edit.setFixedHeight(60)
                notes_edit.setVisible(bool(note_txt) or checked)
                notes_edit.setStyleSheet(
                    f"background:{COLORS['surface_light']}; color:{COLORS['text_dim']};"
                    f" border:none; border-left:2px solid {COLORS['border']};"
                    f" padding:3px 8px; font-size:11px; margin-left:24px;"
                )
                
                full_key = f"{section_key}::{key}"
                
                chk.stateChanged.connect(
                    lambda state, k=key, sk=section_key, c=chk, n=notes_edit:
                    self._on_check_changed(k, sk, c, n)
                )
                
                notes_edit.textChanged.connect(
                    lambda k=key, sk=section_key, n=notes_edit:
                    self._on_note_changed(k, sk, n.toPlainText())
                )
                
                row_layout.addWidget(chk)
                row_layout.addWidget(notes_edit)
                grp_layout.addWidget(row_w)
                self._checklist_widgets[full_key] = (chk, notes_edit)
                
            self._checklist_main_layout.addWidget(grp)

        _build_check_section("Checks Globales Hielco", CHECKLIST_GLOBAL, saved_global, "global")
        
        type_checks = CHECKLIST_BY_TYPE.get(stype, [])
        if type_checks:
            _build_check_section(f"Checks Especificos: {stype}", type_checks, saved_specific, "specific")
        else:
            lbl = QLabel(f"Sin checks especificos para: {stype}")
            lbl.setStyleSheet(f"color:{COLORS['text_dim']}; padding:8px; background:transparent;")
            self._checklist_main_layout.addWidget(lbl)

        self._checklist_main_layout.addStretch()
        self._update_checklist_tab_label()

    def _on_check_changed(self, key, section_key, chk_widget, notes_widget):
        is_checked = chk_widget.isChecked()
        color = "#2ECC71" if is_checked else COLORS['text_main']
        chk_widget.setStyleSheet(
            f"QCheckBox {{ color:{color}; font-size:13px; background:transparent; spacing:8px; }}"
            f" QCheckBox::indicator {{ width:16px; height:16px; border-radius:3px; border:1px solid {COLORS['border']}; }}"
            f" QCheckBox::indicator:checked {{ background:#2ECC71; border-color:#2ECC71; }}"
        )
        notes_widget.setVisible(is_checked or bool(notes_widget.toPlainText()))
        self._save_checklist_state(key, section_key)
        self._update_checklist_tab_label()

    def _on_note_changed(self, key, section_key, text):
        self._save_checklist_state(key, section_key)

    def _save_checklist_state(self, changed_key, section_key):
        if not self.current_situation_id or not self.current_data or not self.parent_special:
            return
            
        sdata = self.current_data.get('specific_data', {}).copy()
        
        for full_key, (chk, notes_edit) in self._checklist_widgets.items():
            sk, k = full_key.split("::", 1)
            dict_key = 'checklist_global' if sk == 'global' else 'checklist_specific'
            if dict_key not in sdata:
                sdata[dict_key] = {}
            sdata[dict_key][k] = {'checked': chk.isChecked(), 'notes': notes_edit.toPlainText()}
            
        # Llamar al callback de SpecialSituationsWidget para persistir
        self.parent_special.service.update(self.current_situation_id, specific_data=sdata)
        self.current_data['specific_data'] = sdata

    def _update_checklist_tab_label(self):
        total   = len(self._checklist_widgets)
        checked = sum(1 for chk, _ in self._checklist_widgets.values() if chk.isChecked())
        if total == 0:
            label = "Checklist [---]"
        else:
            pct = int(checked / total * 100)
            label = f"Checklist [{pct}%]"
            
        self.checklist_updated.emit(label)
