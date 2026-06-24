from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from ui.styles import COLORS

class DashboardCard(QFrame):
    def __init__(self, title, value, subtext=None, color=COLORS['primary']):
        super().__init__()
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame:hover {{
                border: 1px solid {color};
            }}
        """)
        
        # Shadow Effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; font-weight: bold; letter-spacing: 1px; border: none; background: transparent;")
        layout.addWidget(title_lbl)
        
        # Value
        value_lbl = QLabel(str(value))
        value_lbl.setStyleSheet(f"color: {COLORS['text_main']}; font-size: 28px; font-weight: bold; margin-top: 5px; border: none; background: transparent;")
        layout.addWidget(value_lbl)
        
        # Subtext (optional)
        if subtext:
            sub_lbl = QLabel(subtext)
            sub_lbl.setStyleSheet(f"color: {color}; font-size: 12px; margin-top: 2px; border: none; background: transparent;")
            layout.addWidget(sub_lbl)
            
        layout.addStretch()
