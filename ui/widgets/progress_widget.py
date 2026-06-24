from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QBrush, QColor, QFont, QLinearGradient
from ui.styles import COLORS

class ProgressWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(25)
        self.progress = 0.0 # 0.0 to 1.0
        
    def set_progress(self, val):
        self.progress = max(0.0, min(1.0, val))
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.setBrush(QBrush(QColor(COLORS['surface_light'])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)
        
        if self.progress > 0:
            # Gradient Bar
            grad = QLinearGradient(0, 0, self.width(), 0)
            grad.setColorAt(0, QColor("#FF6D00")) # Start Orange
            grad.setColorAt(1, QColor("#FFD600")) # End Yellow
            
            width = int(self.width() * self.progress)
            rect = self.rect()
            rect.setWidth(width)
            
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(rect, 12, 12)
            
        # Draw Text
        painter.setPen(QColor("black") if self.progress > 0.5 else QColor(COLORS['text_dim']))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        text = f"{int(self.progress * 100)}%"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
