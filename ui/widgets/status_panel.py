from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame, QSizePolicy, QMessageBox, QToolTip)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from ui.styles import COLORS
from datetime import datetime
import os

# --- 2. MILESTONES WIDGET ---
class BadgeLabel(QLabel):
    def __init__(self, key, icon, parent=None):
        super().__init__(icon, parent)
        self.key = key
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"font-size: 22px; color: {COLORS['text_dim']}; background: transparent;") # Reduced size
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Show tooltip immediately on click (or could be a popup)
            # For now re-using tooltip mechanism or a QMessageBox if preferred, 
            # but user said "aparezca tambien lo que tengo", tooltip is standard for this.
            # Force show tooltip
            QToolTip.showText(event.globalPosition().toPoint(), self.toolTip(), self)

class MilestoneWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50) # Adjusted height
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        
        self.badges = {
            "historian": "🏛️",
            "reader": "👓",
            "valuator": "Σ",
            "skeptic": "⚖️",
            "thesis": "🗡️"
        }
        
        self.badge_labels = {}
        
        for key, icon in self.badges.items():
            lbl = BadgeLabel(key, icon)
            lbl.setToolTip(key.title())
            layout.addWidget(lbl)
            self.badge_labels[key] = lbl
            
    def set_badges(self, active_badges: list):
        for key, lbl in self.badge_labels.items():
            if key in active_badges:
                # Active: Highlighted with border/glow and full color
                lbl.setStyleSheet(f"font-size: 24px; color: {COLORS['primary']}; font-weight: bold; border: 2px solid {COLORS['primary']}; border-radius: 20px; background-color: rgba(255, 214, 0, 0.1);") 
            else:
                # Inactive: Dimmed
                lbl.setStyleSheet(f"font-size: 22px; color: {COLORS['text_dim']}; opacity: 0.3; border: none;") 

    def update_tooltips(self, stats: dict):
        # Helper for HTML formatting
        def fmt_tooltip(title, subtitle, progress_text):
            return f"<div style='margin:0; padding:0; line-height:1.0'><b><span style='font-size:12px'>{title}</span></b> <span style='font-size:10px; color:gray'>({subtitle})</span><br><span style='font-size:10px'>{progress_text}</span></div>"

        # Historian: 5 Reports + 5 Transcripts needed
        ar = stats.get('count_ar', 0)

        tr = stats.get('count_trans', 0)
        tr = stats.get('count_trans', 0)
        self.badge_labels['historian'].setToolTip(fmt_tooltip("The historian", "FY report", f"➖ {ar}/5"))
        
        # Reader
        score_read = stats.get('score_reading', 0) 
        # Assuming score_read is a score out of X, but prompt wants simple format?
        # Let's show % as user had it, or raw? User asked for "like The historian... FY repor".
        # Let's try to match: "Read [Have]/[Total]?"
        # The reader logic isn't fully clear on "Total". Let's stick to % but cleaner format.
        pct_read = int((score_read/35)*100) if score_read else 0
        pct_read = int((score_read/35)*100) if score_read else 0
        self.badge_labels['reader'].setToolTip(fmt_tooltip("The reader", "Reading", f"➖ {pct_read}%"))
        
        # Valuator
        has_excel = "YES" if stats.get('has_excel') else "NO"
        has_excel = "YES" if stats.get('has_excel') else "NO"
        self.badge_labels['valuator'].setToolTip(fmt_tooltip("The valuator", "Model", f"➖ {has_excel}"))
        
        # Skeptic
        # Simplified logic
        # Simplified logic
        self.badge_labels['skeptic'].setToolTip(fmt_tooltip("The skeptic", "External Sources", "➖ Check"))
        
        # Thesis
        has_thesis = "YES" if stats.get('has_thesis') else "NO"
        has_thesis = "YES" if stats.get('has_thesis') else "NO"
        self.badge_labels['thesis'].setToolTip(fmt_tooltip("The thesis", "Conclusion", f"➖ {has_thesis}"))

# --- 3. STATUS PANEL (CONTAINER) ---
class StatusPanel(QFrame):
    request_open_document = pyqtSignal(str) # Filename or Path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.setFixedWidth(300) # Removed fixed width as requested to extend
        # self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"background-color: {COLORS['surface_light']}; border-radius: 10px; border: 1px solid {COLORS['border']};")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        lbl_status = QLabel("MILESTONES") # Renamed
        lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_status.setStyleSheet(f"font-weight: bold; color: {COLORS['text_dim']}; font-size: 12px; letter-spacing: 1px;")
        layout.addWidget(lbl_status)
        
        # Milestones (Now clearer/larger)
        self.milestones = MilestoneWidget()
        layout.addWidget(self.milestones)
        
        # Smart Resume Button
        self.btn_resume = QPushButton("Continue Research")
        self.btn_resume.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_resume.setFixedHeight(40)
        self.btn_resume.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']}; 
                color: black; 
                font-weight: bold; 
                font-size: 14px;
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FFD600;
            }}
        """)
        self.btn_resume.clicked.connect(self.on_resume_clicked)
        layout.addWidget(self.btn_resume)
        
        # DB connection
        # Adapting to use LibraryManager directly to share same DB as PdfManager
        from core.library_manager import LibraryManager
        from config import LIBRARY_ROOT
        self.library_manager = LibraryManager(str(LIBRARY_ROOT))
        self.current_ticker = None

    def update_status(self, ticker):
        self.current_ticker = ticker
        if not ticker:
            # self.progress_bar.set_progress(0)
            # self.lbl_percent.setText("Select Company")
            self.milestones.set_badges([])
            self.btn_resume.setEnabled(False)
            return
            
        self.btn_resume.setEnabled(True)
        
        # Calculate Logic
        pct, stats = self.library_manager.get_company_progress(ticker)
        
        # self.progress_bar.set_progress(pct / 100.0) # Removed
        # self.lbl_percent.setText(f"{pct}% Complete") # Removed
        
        # Badges Logic (Mock visual for now or implement full logic? User asked for visual strictness)
        # Let's simple check points or files?
        # Implementing badges logic based on files count requires data we have in LibraryManager
        # But `get_company_progress` is simple. 
        # Let's derive badges from simple heuristics for now to satisfy UI.
        
        # To do real badges we'd need methods like `has_valuation(ticker)`, `valid_history(ticker)`
        # Assuming for now we just show visual feedback.
        active_badges = []
        if pct > 10: active_badges.append("historian")
        if pct > 40: active_badges.append("reader")
        if stats.get('has_excel'): active_badges.append("valuator")
        if pct > 80: active_badges.append("skeptic")
        if stats.get('has_thesis'): active_badges.append("thesis")
        
        self.milestones.set_badges(active_badges)
        self.milestones.update_tooltips(stats)

    def on_resume_clicked(self):
        if not self.current_ticker: return
        
        try:
            doc_path = self.library_manager.get_smart_resume_doc(self.current_ticker)
            
            if doc_path and os.path.exists(doc_path):
                 self.request_open_document.emit(doc_path)
            else:
                 QMessageBox.information(self, "Status", "No specific document prioritized. Explore the library!")
                
        except Exception as e:
            print(f"Error in Smart Resume: {e}")
            QMessageBox.critical(self, "Error", f"Smart Resume Failed: {e}")
