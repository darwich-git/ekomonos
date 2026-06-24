from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGridLayout, QFrame, QScrollArea)
from PyQt6.QtCore import Qt
from ui.styles import COLORS
from ui.components.cards import DashboardCard
import os

class CompanyDetailWidget(QWidget):
    def __init__(self, ticker, portfolio_manager):
        super().__init__()
        self.ticker = ticker
        self.manager = portfolio_manager
        self.data = self.manager.companies.get(ticker, {})
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 1. Header: Ticker + Actions
        header = QHBoxLayout()
        
        # Title
        title = QLabel(f"{self.ticker} Analysis")
        title.setStyleSheet(f"color: {COLORS['text_main']}; font-size: 28px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Action Buttons
        btn_style = f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['text_main']};
                border: 1px solid {COLORS['border']};
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
        """
        
        open_excel_btn = QPushButton("Open Excel Model")
        open_excel_btn.setStyleSheet(btn_style)
        open_excel_btn.clicked.connect(self.open_excel)
        header.addWidget(open_excel_btn)
        
        open_notes_btn = QPushButton("Open Notes")
        open_notes_btn.setStyleSheet(btn_style)
        # open_notes_btn.clicked.connect(self.open_notes) # To implement
        header.addWidget(open_notes_btn)
        
        layout.addLayout(header)

        # 2. KPI Grid (Financials)
        # We will fetch these from Excel later. For now, placeholders as requested.
        kpi_label = QLabel("Key Financials (LTM / NTM)")
        kpi_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-weight: bold; margin-top: 10px;")
        layout.addWidget(kpi_label)

        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(15)
        
        # Row 1
        kpi_grid.addWidget(DashboardCard("Price", "$145.30", "Close", COLORS['primary']), 0, 0)
        kpi_grid.addWidget(DashboardCard("Market Cap", "$2.4B", "USD", COLORS['primary']), 0, 1)
        kpi_grid.addWidget(DashboardCard("Revenue (2025E)", "$850M", "Projected", COLORS['accent']), 0, 2)
        kpi_grid.addWidget(DashboardCard("EBIT Margin", "18.5%", "LTM", COLORS['success']), 0, 3)
        
        # Row 2
        kpi_grid.addWidget(DashboardCard("NTM EBIT", "$155M", "Projected", COLORS['accent']), 1, 0)
        kpi_grid.addWidget(DashboardCard("PER (NTM)", "15.4x", "Ratio", COLORS['warning']), 1, 1)
        kpi_grid.addWidget(DashboardCard("Net Debt/EBITDA", "1.2x", "Leverage", COLORS['danger']), 1, 2)
        kpi_grid.addWidget(DashboardCard("Target Price", "$180.00", "Upside +24%", COLORS['success']), 1, 3)
        
        layout.addLayout(kpi_grid)

        # 3. Time Tracking (Pomodoro Context)
        # This section visualizes time spent. The actual timer is in the sidebar, 
        # but we can show stats here.
        time_label = QLabel("Research Time Allocation")
        time_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-weight: bold; margin-top: 20px;")
        layout.addWidget(time_label)
        
        # Placeholder for Time Bar
        time_container = QFrame()
        time_container.setStyleSheet(f"background-color: {COLORS['surface']}; border-radius: 8px; padding: 20px;")
        time_layout = QHBoxLayout(time_container)
        
        total_hours = QLabel("12.5 Hours Invested")
        total_hours.setStyleSheet(f"color: {COLORS['text_main']}; font-size: 18px; font-weight: bold;")
        time_layout.addWidget(total_hours)
        
        time_layout.addStretch()
        
        # Visual bar
        # (We can add a custom paint event or progress bar here later)
        
        layout.addWidget(time_container)
        
        layout.addStretch()

    def open_excel(self):
        excel_path = self.data.get("excel_file")
        if excel_path and os.path.exists(excel_path):
            try:
                os.startfile(excel_path)
            except Exception as e:
                print(f"Error opening excel: {e}")
        else:
            print("No excel file found")
