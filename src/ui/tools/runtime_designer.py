from PyQt6.QtWidgets import (QWidget, QFrame, QApplication, QMessageBox, 
                             QHBoxLayout, QVBoxLayout, QGridLayout, QPushButton, QLabel,
                             QLineEdit, QComboBox, QAbstractItemView, QTextEdit, QMenu, QInputDialog, QSizePolicy, QMainWindow)
from PyQt6.QtCore import Qt, QPoint, QRect, QEvent, QTimer, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor, QFont
import json
import os
from datetime import datetime

class OverlayControls(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 220);
                border-radius: 12px;
                border: 1px solid #555;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14px; 
                padding: 4px 6px;
                color: #DDD;
            }
            QPushButton:hover {
                background-color: #555;
                border-radius: 6px;
                color: white;
            }
        """)
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(6, 2, 6, 2)
        c_layout.setSpacing(8)
        
        # Save (Checkmark)
        self.btn_save = QPushButton("✅")
        self.btn_save.setToolTip("Generate Report")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Visibility (Eye)
        self.btn_hide = QPushButton("👁")
        self.btn_hide.setToolTip("Toggle Preview (Hide/Show Wrappers)")
        self.btn_hide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hide.setCheckable(True)

        # Close (Cross)
        self.btn_close = QPushButton("❌")
        self.btn_close.setToolTip("Close Designer")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        
        c_layout.addWidget(self.btn_save)
        c_layout.addWidget(self.btn_hide)
        c_layout.addWidget(self.btn_close)
        
        layout.addWidget(container)
        
        # Drag state
        self.dragging = False
        self.drag_pos = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def show_centered(self, parent_rect):
        self.adjustSize()
        w = self.width()
        h = self.height()
        # Top-Center, slightly down
        x = parent_rect.center().x() - w // 2
        y = parent_rect.top() + 60
        self.move(x, y)
        self.show()

class MovableProxy(QFrame):
    """
    Independent floating box representing a UI element.
    Can be moved and resized freely.
    """
    def __init__(self, parent, original_widget, original_rect):
        super().__init__(parent)
        self.original_widget = original_widget
        self.original_rect = original_rect # Global coordinates
        
        # Set geometry relative to parent (Overlay)
        local_rect = parent.mapFromGlobal(original_rect.topLeft())
        self.setGeometry(QRect(local_rect, original_rect.size()))
        
        self.show()
        self.setMouseTracking(True)
        
        # Style
        self.is_selected = False
        self.hovered = False
        
        # Smart Labeling
        name = self.generate_smart_name(original_widget)
        
        self.label = QLabel(name, self)
        # Style will be set in paintEvent
        self.label.setStyleSheet("color: #FFFFFF; background-color: rgba(0,0,0,180); font-weight: bold; font-size: 10px; padding: 1px; border-radius: 2px;")
        self.label.move(0, 0)
        self.label.adjustSize()
        self.label.show()

        # State
        self.dragging = False
        self.resizing = False
        self.drag_start_pos = QPoint()
        self.resize_handle = None
        
        # Behavior
        self.behavior_mode = "Responsive" 
        self.scope_mode = "Local" # "Local" (Green) vs "Global" (Orange)
        self.font_change = None

    def generate_smart_name(self, w):
        try:
            if w.objectName(): return w.objectName()
            
            text = ""
            if hasattr(w, 'text'):
                t = w.text
                if callable(t): text = t()
                else: text = str(t)
            
            cls = w.__class__.__name__.replace("QT", "").replace("Widget", "").replace("Button", "Btn").replace("Label", "Lbl").replace("Frame", "Frm")
            
            if text:
                text = text.strip().replace("\n", " ")
                if len(text) > 15: text = text[:12] + "..."
                return f"{cls}: {text}"
                
            return cls
        except: return "Widget"

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
        
        title = menu.addAction(f"🔧 {self.label.text()}")
        title.setEnabled(False)
        menu.addSeparator()
        
        a_front = menu.addAction("Bring to Front")
        a_back = menu.addAction("Send to Back")
        menu.addSeparator()
        
        a_font = menu.addAction("🔠 Font Size...")
        menu.addSeparator()
        
        # Scope (Colors)
        a_local = menu.addAction("Scope: Local (Green - This Page)")
        a_local.setCheckable(True)
        a_local.setChecked(self.scope_mode == "Local")
        
        a_global = menu.addAction("Scope: Global (Orange - All Pages)")
        a_global.setCheckable(True)
        a_global.setChecked(self.scope_mode == "Global")
        
        menu.addSeparator()
        
        a_abs = menu.addAction("Behavior: Absolute (Float)")
        a_abs.setCheckable(True)
        a_abs.setChecked(self.behavior_mode == "Absolute")
        
        action = menu.exec(event.globalPos())
        
        if action == a_front: self.raise_()
        elif action == a_back: self.lower_()
        elif action == a_font: self.change_font_size()
        elif action == a_local: self.scope_mode = "Local"
        elif action == a_global: self.scope_mode = "Global"
        elif action == a_abs: self.behavior_mode = "Absolute"
        
        self.update()

    def change_font_size(self):
        current = 10
        try:
            f = self.original_widget.font()
            pt = f.pointSize()
            if pt > 0: current = pt
        except: pass
        
        val, ok = QInputDialog.getInt(self, "Font Size", "Points:", current, 5, 72)
        if ok:
            try:
                # Update Font Object
                f = self.original_widget.font()
                f.setPointSize(val)
                self.original_widget.setFont(f)
                
                # Update Stylesheet
                old_ss = self.original_widget.styleSheet() or ""
                new_rule = f"font-size: {val}pt;"
                self.original_widget.setStyleSheet(old_ss + " " + new_rule)
                
                self.font_change = val
            except Exception as e:
                pass

    def paintEvent(self, event):
        try:
            if not self.original_widget or not self.original_widget.isVisible():
                self.hide()
                return
                
            painter = QPainter(self)
            
            # DEFAULT: LOCAL = GREEN
            color = QColor(0, 200, 50, 5) # Greenish tint
            stroke = QColor(0, 255, 100, 150) # Green border
            
            # GLOBAL = ORANGE
            if self.scope_mode == "Global":
                color = QColor(255, 140, 0, 5)
                stroke = QColor(255, 140, 0, 150)
            
            if self.hovered: 
                stroke.setAlpha(255)
                color.setAlpha(30)
            
            if self.is_selected:
                stroke = QColor(255, 255, 255, 255) # White glow for selection
                if self.scope_mode == "Global": stroke = QColor(255, 0, 0, 255) # Red for global select
                color.setAlpha(20)

            painter.fillRect(self.rect(), color)
            
            pen = QPen(stroke, 1)
            pen.setStyle(Qt.PenStyle.DashLine) 
            if self.is_selected: 
                pen.setStyle(Qt.PenStyle.SolidLine)
                pen.setWidth(2)
            
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(0,0,-1,-1))
            
            if self.is_selected:
                self.draw_handles(painter)
                
        except RuntimeError:
            self.hide()
            self.deleteLater()
        except Exception as e:
            pass 


    def draw_handles(self, painter):
        hw = 6
        w, h = self.width(), self.height()
        coords = [
            (0, 0), (w//2, 0), (w-hw, 0),
            (0, h//2), (w-hw, h//2),
            (0, h-hw), (w//2, h-hw), (w-hw, h-hw)
        ]
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        for x, y in coords:
            painter.drawRect(x, y, hw, hw)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent().select_proxy(self)
            
            handle = self.hit_test_handles(event.pos())
            if handle:
                self.resizing = True
                self.resize_handle = handle
            else:
                self.dragging = True
            
            self.drag_start_pos = event.globalPosition().toPoint()
            self.start_geo = self.geometry()
            self.parent().setFocus() 

    def mouseMoveEvent(self, event):
        handle = self.hit_test_handles(event.pos())
        if handle:
            self.set_cursor_for_handle(handle)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor if self.rect().contains(event.pos()) else Qt.CursorShape.ArrowCursor)

        if self.dragging:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            old_pos = self.pos()
            new_pos = self.start_geo.topLeft() + delta
            self.move(new_pos)
            
            frame_delta = new_pos - old_pos
            self.move_children_proxies(frame_delta)
            
            self.parent().calculate_guides(self)
            
        elif self.resizing and self.resize_handle:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            self.apply_resize(self.resize_handle, delta)
            self.parent().calculate_guides(self)

    def move_children_proxies(self, delta):
        my_w = self.original_widget
        overlay = self.parent()
        for p in overlay.proxies:
            if p == self: continue
            w = p.original_widget
            if self.is_ancestor(my_w, w):
                p.move(p.pos() + delta)
                # p.start_geo was crashing because it's not set for children not being dragged
                # p.start_geo.moveTopLeft(p.start_geo.topLeft() + delta) 
                
    def is_ancestor(self, possible_parent, child):
        curr = child.parent()
        while curr:
            if curr == possible_parent: return True
            curr = curr.parent()
        return False

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False
        self.parent().clear_guides()
        self.parent().enforce_z_order()

    def enterEvent(self, event):
        self.label.raise_()
        self.hovered = True
        self.update()
        
    def leaveEvent(self, event):
        self.hovered = False
        self.update()

    def hit_test_handles(self, pos):
        if not self.is_selected: return None
        hw = 10 
        w, h = self.width(), self.height()
        rects = {
            'TL': QRect(0, 0, hw, hw), 'T': QRect(w//2-hw//2, 0, hw, hw), 'TR': QRect(w-hw, 0, hw, hw),
            'L': QRect(0, h//2-hw//2, hw, hw), 'R': QRect(w-hw, h//2-hw//2, hw, hw),
            'BL': QRect(0, h-hw, hw, hw), 'B': QRect(w//2-hw//2, h-hw, hw, hw), 'BR': QRect(w-hw, h-hw, hw, hw)
        }
        for name, r in rects.items():
            if r.contains(pos): return name
        return None

    def set_cursor_for_handle(self, handle):
        cursors = {
            'T': Qt.CursorShape.SizeVerCursor, 'B': Qt.CursorShape.SizeVerCursor,
            'L': Qt.CursorShape.SizeHorCursor, 'R': Qt.CursorShape.SizeHorCursor,
            'TL': Qt.CursorShape.SizeFDiagCursor, 'BR': Qt.CursorShape.SizeFDiagCursor,
            'TR': Qt.CursorShape.SizeBDiagCursor, 'BL': Qt.CursorShape.SizeBDiagCursor
        }
        self.setCursor(cursors.get(handle, Qt.CursorShape.ArrowCursor))

    def apply_resize(self, handle, delta):
        geo = self.start_geo
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        dx, dy = delta.x(), delta.y()
        if 'R' in handle: w += dx
        if 'L' in handle: x += dx; w -= dx
        if 'B' in handle: h += dy
        if 'T' in handle: y += dy; h -= dy
        if w < 10: w = 10
        if h < 10: h = 10
        self.setGeometry(x, y, w, h)


class DesignerOverlay(QWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus) 
        
        self.bg_color = "rgba(0, 0, 0, 150)"
        self.setStyleSheet(f"background-color: {self.bg_color};")
        
        self.resize(main_window.size())
        self.show()
        
        self.proxies = []
        self.selection = None
        self.proxies_visible = True
        self.guides = [] 
        
        self.controls = OverlayControls(self)
        self.controls.btn_save.clicked.connect(self.save_and_close)
        self.controls.btn_hide.clicked.connect(self.toggle_visibility)
        self.controls.btn_close.clicked.connect(self.close_overlay)
        self.controls.show_centered(self.rect())
        
        # --- LOCK WINDOW SIZE ---
        # Cache Original Constraints
        self.orig_min_size = self.main_window.minimumSize()
        self.orig_max_size = self.main_window.maximumSize()
        
        # Lock to Current Size
        curr_size = self.main_window.size()
        self.main_window.setFixedSize(curr_size)
        # ------------------------
        
        QTimer.singleShot(100, self.spawn_proxies)

    def keyPressEvent(self, event):
        if not self.selection: return
        step = 10 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1
        pos = self.selection.pos()
        if event.key() == Qt.Key.Key_Left: pos.setX(pos.x() - step)
        elif event.key() == Qt.Key.Key_Right: pos.setX(pos.x() + step)
        elif event.key() == Qt.Key.Key_Up: pos.setY(pos.y() - step)
        elif event.key() == Qt.Key.Key_Down: pos.setY(pos.y() + step)
        else: return
        self.selection.move(pos)
        self.calculate_guides(self.selection)

    def calculate_guides(self, target):
        self.guides = []
        if not target: return
        tr = target.geometry()
        t_center = tr.center()
        nearest = None
        min_d = 9999
        for p in self.proxies:
            if p == target or not p.isVisible(): continue
            d = (p.geometry().center() - t_center).manhattanLength()
            if d < min_d:
                min_d = d
                nearest = p
        if nearest:
            self.guides.append({
                "line": (t_center, nearest.geometry().center()),
                "text": f"{int(min_d)}px"
            })
        self.update()

    def clear_guides(self):
        self.guides = []
        self.update()

    def paintEvent(self, event):
        if self.guides:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor(255, 100, 200), 1)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            for g in self.guides:
                p1, p2 = g["line"]
                painter.drawLine(p1, p2)
                mid = (p1 + p2) / 2
                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(mid, g["text"])

    def toggle_visibility(self):
        self.proxies_visible = not self.proxies_visible
        if self.proxies_visible:
            self.setStyleSheet(f"background-color: {self.bg_color};")
            self.controls.btn_hide.setText("👁")
        else:
            self.setStyleSheet("background-color: transparent;")
            self.controls.btn_hide.setText("🙈")
        for p in self.proxies:
            p.setVisible(self.proxies_visible)
    
    def enforce_z_order(self):
        self.proxies.sort(key=lambda p: p.width() * p.height(), reverse=True)
        for p in self.proxies:
            p.raise_()
        self.controls.raise_()

    def spawn_proxies(self):
        self.scan_recursive(self.main_window)
        self.enforce_z_order()

    def scan_recursive(self, widget):
        if not widget.isVisible(): return
        if widget == self or widget == self.controls: return
        if widget.parent() == self: return
        if widget.window() != self.main_window.window(): return

        # Explicitly ignore QMainWindow (The Root)
        if isinstance(widget, QMainWindow): 
            # But DO Scan children
            children = widget.children()
            for child in children:
                if isinstance(child, QWidget):
                    self.scan_recursive(child)
            return

        is_relevant = isinstance(widget, (QFrame, QPushButton, QLabel, QLineEdit, QComboBox, QAbstractItemView, QTextEdit))
        if widget.layout() is not None and widget.layout().count() > 0: is_relevant = True
        
        if is_relevant:
            try:
                global_pos = widget.mapToGlobal(QPoint(0, 0))
                global_rect = QRect(global_pos, widget.size())
                
                # Removed the Size Check (95%) so Page Frames reappear
                if global_rect.width() > 10 and global_rect.height() > 10:
                    proxy = MovableProxy(self, widget, global_rect)
                    self.proxies.append(proxy)
                    proxy.show()
            except: pass
            
        children = widget.children()
        for child in children:
            if isinstance(child, QWidget):
                self.scan_recursive(child)
                
    def select_proxy(self, proxy):
        if self.selection:
            self.selection.is_selected = False
            self.selection.update()
        self.selection = proxy
        self.selection.is_selected = True
        self.controls.raise_() 
        self.selection.update()

    def save_and_close(self):
        self.save_report()
        self.close_overlay()
        
    def close_overlay(self):
        self.proxies.clear()
        
        # --- RESTORE WINDOW SIZE ---
        if hasattr(self, 'orig_min_size'):
            self.main_window.setMinimumSize(self.orig_min_size)
        else:
            self.main_window.setMinimumSize(QSize(0,0))

        if hasattr(self, 'orig_max_size'):
            self.main_window.setMaximumSize(self.orig_max_size)
        else:
            self.main_window.setMaximumSize(QSize(16777215, 16777215))
        # ---------------------------

        self.close()
        self.deleteLater()
        if hasattr(self.main_window, 'designer_overlay'):
             self.main_window.designer_overlay = None

    def save_report(self):
        log = []
        for p in self.proxies:
            try:
                if not p.original_widget: continue
                w_class = p.original_widget.__class__.__name__
            except RuntimeError: continue
            
            final_geo = p.geometry()
            final_global_tl = self.mapToGlobal(final_geo.topLeft())
            orig_tl = p.original_rect.topLeft()
            
            dx = final_global_tl.x() - orig_tl.x()
            dy = final_global_tl.y() - orig_tl.y()
            dw = final_geo.width() - p.original_rect.width()
            dh = final_geo.height() - p.original_rect.height()
            
            # LIVE SIZE ONLY
            try:
                if (abs(dw) > 2 or abs(dh) > 2) and p.original_widget:
                    p.original_widget.setFixedSize(final_geo.size())
                    p.original_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except: pass
            
            if abs(dx) > 2 or abs(dy) > 2 or abs(dw) > 2 or abs(dh) > 2 or p.behavior_mode != "Absolute" or p.font_change or p.scope_mode == "Global":
                entry = {
                    "widget": p.label.text(),
                    "class": w_class,
                    "behavior": p.behavior_mode,
                    "scope": p.scope_mode,
                    "font_pt": p.font_change,
                    "delta_pos": [dx, dy],
                    "delta_size": [dw, dh],
                    "final_rect": [final_global_tl.x(), final_global_tl.y(), final_geo.width(), final_geo.height()]
                }
                log.append(entry)
                
        if not log:
            QMessageBox.information(self, "No Changes", "No significant layout changes detected.")
            return

        filename = "layout_design_report.json"
        with open(filename, 'w') as f:
            json.dump(log, f, indent=4)
            
        QMessageBox.information(self, "Report Saved", 
                                f"Design persisted to {filename}.\n\nSize changes applied to view.\nPosition changes saved for coding.")
