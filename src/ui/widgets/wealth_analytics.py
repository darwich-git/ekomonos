from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QGridLayout, QFrame, QButtonGroup, QScrollArea, QSizePolicy, QStackedWidget)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QCursor

from ui.styles import COLORS
from ui.widgets.wealth_wizard import WealthWizardDialog
from ui.widgets.highcharts_view import HighchartsWidget

class StatCard(QFrame):
    def __init__(self, title, value, subtitle=""):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(5)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 14px; font-weight: bold; border: none;")
        layout.addWidget(title_lbl)
        
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(f"color: {COLORS['text_main']}; font-size: 28px; font-weight: bold; border: none;")
        layout.addWidget(self.value_lbl)
        
        if subtitle:
            self.subtitle_lbl = QLabel(subtitle)
            self.subtitle_lbl.setStyleSheet(f"color: {COLORS['primary']}; font-size: 12px; border: none;")
            layout.addWidget(self.subtitle_lbl)
        
        layout.addStretch()

    def set_value(self, value, subtitle_text=""):
        self.value_lbl.setText(value)
        if hasattr(self, 'subtitle_lbl') and subtitle_text:
            self.subtitle_lbl.setText(subtitle_text)

class WealthAnalyticsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # --- Top Bar (Owner Toggle + Update Month) ---
        top_bar_layout = QHBoxLayout()
        
        # 1. Owner Toggle
        toggle_container = QFrame()
        toggle_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {COLORS['text_dim']};
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton:checked {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['primary']};
            }}
            QPushButton:hover:!checked {{
                background-color: {COLORS['background']};
            }}
        """)
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(4, 4, 4, 4)
        toggle_layout.setSpacing(2)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        self.btn_rafa = QPushButton("Rafa")
        self.btn_rafa.setCheckable(True)
        self.btn_rafa.setChecked(True) # Default
        self.btn_rafa.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.btn_cris = QPushButton("Cris")
        self.btn_cris.setCheckable(True)
        self.btn_cris.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.btn_comun = QPushButton("Family")
        self.btn_comun.setCheckable(True)
        self.btn_comun.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.btn_group.addButton(self.btn_rafa, 0)
        self.btn_group.addButton(self.btn_cris, 1)
        self.btn_group.addButton(self.btn_comun, 2)
        
        self.btn_group.buttonClicked.connect(self.on_owner_changed)
        
        toggle_layout.addWidget(self.btn_rafa)
        toggle_layout.addWidget(self.btn_cris)
        toggle_layout.addWidget(self.btn_comun)
        
        top_bar_layout.addWidget(toggle_container)
        
        # Spacer
        top_bar_layout.addStretch()
        
        # 1. Balance Sheet Button
        self.btn_balance = QPushButton("Balance Sheet")
        self.btn_balance.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_balance.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['text_main']};
                font-weight: bold;
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 6px;
                border: 1px solid {COLORS['border']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
            }}
        """)
        self.btn_balance.clicked.connect(self.show_balance_sheet)
        top_bar_layout.addWidget(self.btn_balance)
        
        # 3. Update Month Button
        self.btn_update = QPushButton("+ Monthly Update")
        self.btn_update.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_update.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: #000000;
                font-weight: bold;
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #E68900;
            }}
        """)
        self.btn_update.clicked.connect(self.open_wizard)
        top_bar_layout.addWidget(self.btn_update)
        
        # 3.5 Sync Excel Button
        self.btn_sync = QPushButton("Sync Excel")
        self.btn_sync.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_sync.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['primary']};
                font-weight: bold;
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 6px;
                border: 1px solid {COLORS['primary']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface']};
            }}
        """)
        self.btn_sync.clicked.connect(self.force_sync_excel)
        top_bar_layout.addWidget(self.btn_sync)
        
        # 4. Settings (Categories) Button
        from ui.widgets.category_manager_dialog import CategoryManagerDialog
        self.btn_categories = QPushButton("⚙")
        self.btn_categories.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_categories.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['text_main']};
                font-weight: bold;
                font-size: 16px;
                padding: 10px;
                border-radius: 6px;
                border: 1px solid {COLORS['border']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
            }}
        """)
        self.btn_categories.clicked.connect(lambda: CategoryManagerDialog(self).exec())
        top_bar_layout.addWidget(self.btn_categories)
        
        main_layout.addLayout(top_bar_layout)
        
        self.stacked_widget = QStackedWidget(self)
        main_layout.addWidget(self.stacked_widget)
        
        # --- PAGE 0: DASHBOARD OVERVIEW ---
        self.page_overview = QWidget()
        overview_layout = QVBoxLayout(self.page_overview)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Scrollable Content Area ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(20)
        
        # -- KPI Cards Grid --
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(15)
        
        self.card_net_worth = StatCard("📈 Patrimonio Neto", "£0.00", "Total general")
        self.card_income    = StatCard("💵 Ingreso Mensual", "£0.00", "YTD: -")
        self.card_expenses  = StatCard("🛒 Gastos Mensuales", "£0.00", "YTD: -")
        self.card_cashflow  = StatCard("⚖ Cash Flow", "£0.00", "Mes actual")
        self.card_savings   = StatCard("🏦 Tasa de Ahorro", "0%", "YTD: 0%")
        self.card_cash      = StatCard("💧 Liquidez", "£0.00", "Cuentas y Efectivo")
        self.card_ibkr      = StatCard("📊 IBKR", "£0.00", "Value vs Invested")
        self.card_fund      = StatCard("🌍 Fundsmith / Other", "£0.00", "Value vs Invested")
        
        self._make_card_clickable(self.card_net_worth, "net_worth")
        self._make_card_clickable(self.card_income, "income")
        self._make_card_clickable(self.card_expenses, "expenses")
        self._make_card_clickable(self.card_cashflow, "cashflow")
        self._make_card_clickable(self.card_savings, "savings")
        self._make_card_clickable(self.card_cash, "cash")
        self._make_card_clickable(self.card_ibkr, "ibkr")
        self._make_card_clickable(self.card_fund, "fundsmith")
        
        # Row 1
        kpi_grid.addWidget(self.card_net_worth, 0, 0)
        kpi_grid.addWidget(self.card_income, 0, 1)
        kpi_grid.addWidget(self.card_expenses, 0, 2)
        # Row 2
        kpi_grid.addWidget(self.card_cashflow, 1, 0)
        kpi_grid.addWidget(self.card_savings, 1, 1)
        kpi_grid.addWidget(self.card_cash, 1, 2)
        # Row 3
        kpi_grid.addWidget(self.card_ibkr, 2, 0)
        kpi_grid.addWidget(self.card_fund, 2, 1)
        
        self.content_layout.addLayout(kpi_grid)
        
        # 3. Highcharts Overview Container
        # We will dynamically add charts here
        self.overview_charts_layout = QHBoxLayout()
        self.overview_charts_layout.setSpacing(15)
        
        self.chart_nw = HighchartsWidget()
        self.chart_nw.setMinimumHeight(400)
        self.chart_nw.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        self.chart_dist = HighchartsWidget()
        self.chart_dist.setMinimumHeight(400)
        self.chart_dist.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.chart_dist.setMinimumWidth(350)
        
        self.overview_charts_layout.addWidget(self.chart_nw, stretch=2)
        self.overview_charts_layout.addWidget(self.chart_dist, stretch=1)
        
        self.content_layout.addLayout(self.overview_charts_layout)
        
        # Add stretch to push content up
        self.content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        overview_layout.addWidget(scroll_area)
        self.stacked_widget.addWidget(self.page_overview)
        
        # --- PAGE 1: DETAILED VIEW (Drill-down) ---
        self.page_detail = QWidget()
        page_detail_layout = QVBoxLayout(self.page_detail)
        page_detail_layout.setContentsMargins(0, 0, 0, 0)
        
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        detail_content_widget = QWidget()
        detail_content_widget.setStyleSheet("background-color: transparent;")
        detail_layout = QVBoxLayout(detail_content_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        
        detail_top_bar = QHBoxLayout()
        self.btn_back = QPushButton("⬅ Back to Dashboard")
        self.btn_back.setStyleSheet(f"""
            QPushButton {{ background: {COLORS['surface_light']}; color: {COLORS['text_main']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 10px 20px; font-weight: bold; font-size: 14px;}}
            QPushButton:hover {{ background: {COLORS['border']}; }}
        """)
        self.btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_back.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        detail_top_bar.addWidget(self.btn_back)
        
        self.lbl_detail_title = QLabel("Detail View")
        self.lbl_detail_title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['text_main']}; margin-left: 20px;")
        detail_top_bar.addWidget(self.lbl_detail_title)
        
        detail_top_bar.addStretch()
        detail_layout.addLayout(detail_top_bar)
        
        self.detail_chart_layout = QVBoxLayout()
        detail_layout.addLayout(self.detail_chart_layout)
        
        # Detail stats cards at the bottom
        self.detail_bottom_container = QVBoxLayout()
        detail_layout.addLayout(self.detail_bottom_container)
        
        detail_layout.addStretch()
        detail_scroll.setWidget(detail_content_widget)
        page_detail_layout.addWidget(detail_scroll)
        
        self.stacked_widget.addWidget(self.page_detail)
        
        # Load mock data for testing UI
        self.load_dummy_data()

    def _make_card_clickable(self, card, detail_id):
        card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        card.mousePressEvent = lambda event, cid=detail_id: self.open_detail_view(cid)

    def on_owner_changed(self, button):
        owner_name = button.text()
        print(f"Switching view to: {owner_name}")
        self.fetch_real_data(owner_name)
        if self.stacked_widget.currentIndex() == 1:
            # We need to know which category we are currently viewing
            if hasattr(self, 'current_category_id'):
                self.render_detail_chart(self.current_category_id, owner_name)

    def fetch_real_data(self, owner_name):
        from core.services.wealth_service import WealthService
        
        # Determine active owner
        if not owner_name:
            if self.btn_rafa.isChecked(): owner_name = "Rafa"
            elif self.btn_cris.isChecked(): owner_name = "Cris"
            else: owner_name = "Family"
            
        self.current_owner = owner_name
        
        svc = WealthService()
        result = svc.get_overview_data(owner_name)
        
        if result.get('error'):
            self.card_net_worth.set_value("£0.00", "DB Error")
            return
            
        kpis = result['kpis']
        charts = result['charts']
        
        sign_m = "+" if kpis['nw_growth_monthly'] >= 0 else ""
        sign_cagr = "+" if kpis['nw_cagr'] >= 0 else ""
        subtitle_nw = f"Inception: {sign_cagr}{kpis['nw_cagr']:.1f}% | MTH: {sign_m}{kpis['nw_growth_monthly']:.1f}%"
        
        # --- Update KPIs ---
        self.card_net_worth.set_value(f"£{kpis['total_nw']:,.0f}", subtitle_nw)
        self.card_cash.set_value(f"£{kpis['total_cash']:,.2f}", "Disponible")
        self.card_ibkr.set_value(f"£{kpis['total_ibkr']:,.2f}", "Balance total")
        self.card_fund.set_value(f"£{kpis['total_fund']:,.2f}", "Balance total")
        
        self.card_income.set_value(f"£{kpis['inc_month']:,.2f}", f"YTD: £{kpis['inc_ytd']:,.2f}")
        self.card_expenses.set_value(f"£{kpis['exp_month']:,.2f}", f"YTD: £{kpis['exp_ytd']:,.2f}")
        
        sign = "+" if kpis['cashflow_month'] >= 0 else ""
        self.card_cashflow.set_value(f"{sign}£{kpis['cashflow_month']:,.2f}", f"Mes: {kpis['latest_snap_month']}")
        
        self.card_savings.set_value(f"{kpis['ytd_savings']:.1f}%", f"Mes actual: {kpis['month_savings']:.1f}%")
            
        # --- Draw Highcharts ---
        
        # Net Worth Line Chart
        nw_options = {
            'chart': {'type': 'area'},
            'title': {'text': 'Net Worth Growth'},
            'xAxis': {'categories': charts['months_labels']},
            'yAxis': {'title': {'text': 'Value (£)'}, 'labels': {'format': '£{value:,.0f}'}},
            'tooltip': {'valuePrefix': '£', 'valueDecimals': 0},
            'series': [{
                'name': 'Net Worth',
                'data': charts['history_nw'],
                'color': '#ff9800',
                'fillColor': {
                    'linearGradient': {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 1},
                    'stops': [
                        [0, 'rgba(255, 152, 0, 0.5)'],
                        [1, 'rgba(255, 152, 0, 0.05)']
                    ]
                }
            }]
        }
        self.chart_nw.set_chart(nw_options)
        
        # Asset Allocation Pie Chart
        pie_data = []
        if charts['pie']['cash'] > 0: pie_data.append({'name': 'Cash', 'y': charts['pie']['cash'], 'color': '#2196F3'})
        if charts['pie']['ibkr'] > 0: pie_data.append({'name': 'IBKR', 'y': charts['pie']['ibkr'], 'color': '#F44336'})
        if charts['pie']['fund'] > 0: pie_data.append({'name': 'Funds', 'y': charts['pie']['fund'], 'color': '#4CAF50'})
        if charts['pie']['house'] > 0: pie_data.append({'name': 'Real Estate', 'y': charts['pie']['house'], 'color': '#9C27B0'})
        
        dist_options = {
            'chart': {'type': 'pie'},
            'title': {'text': 'Asset Allocation'},
            'tooltip': {'pointFormat': '{series.name}: <b>{point.percentage:.1f}%</b><br/>Value: £{point.y:,.0f}'},
            'plotOptions': {
                'pie': {
                    'allowPointSelect': True,
                    'cursor': 'pointer',
                    'dataLabels': {
                        'enabled': True,
                        'format': '<b>{point.name}</b>: {point.percentage:.1f} %'
                    }
                }
            },
            'series': [{
                'name': 'Assets',
                'colorByPoint': True,
                'data': pie_data
            }]
        }
        self.chart_dist.set_chart(dist_options)

    def load_dummy_data(self):
        self.fetch_real_data("Rafa")
        self.card_savings.set_value("45%", "Solid")
        self.card_cashflow.set_value("+€1,250", "December closing")

    def show_balance_sheet(self):
        import os
        try:
            excel_path = os.path.abspath("Master_Balance.xlsx")
            if os.path.exists(excel_path):
                os.startfile(excel_path)
            else:
                self.btn_balance.setText("No existe Master_Balance")
        except Exception as e:
            self.btn_balance.setText("Error")
            print("Export error:", e)

    def open_wizard(self):
        wizard = WealthWizardDialog(self)
        if wizard.exec():
            # Get values (soon we will save to database)
            month = wizard.month_input.date().toString("yyyy-MM")
            gbp = wizard.gbp_input.text()
            print(f"[WIZARD] Closing month {month} with GBP={gbp}")
            self.card_cashflow.set_value("Saved!", f"Month: {month}")
            self.fetch_real_data(self.current_owner)

    def force_sync_excel(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from core.database import DB_PATH, MonthlySnapshot
        from core.excel_bridge import export_snapshot_to_master
        from PyQt6.QtWidgets import QMessageBox
        from core.workers.base_worker import BaseWorker
        
        try:
            engine = create_engine(f"sqlite:///{DB_PATH}")
            Session = sessionmaker(bind=engine)
            session = Session()
            snap = session.query(MonthlySnapshot).order_by(MonthlySnapshot.month_id.desc()).first()
            session.close()
            
            if not snap:
                QMessageBox.warning(self, "Excel Warning", "No hay datos para sincronizar.")
                return
                
            self.btn_sync.setEnabled(False)
            self.btn_sync.setText("Sincronizando...")
            
            def on_success(result):
                self.btn_sync.setEnabled(True)
                self.btn_sync.setText("Sync Excel Master")
                if result:
                    QMessageBox.information(self, "Success", f"Datos copiados con éxito a Master_Balance.xlsx para {snap.month_id}")
                else:
                    QMessageBox.warning(self, "Excel Warning", "No se pudo escribir en Master_Balance.xlsx.\n¿Está abierto por Excel?\n\nConsulta src/logs/excel_bridge.log para más detalles.")

            def on_error(err):
                self.btn_sync.setEnabled(True)
                self.btn_sync.setText("Sync Excel Master")
                QMessageBox.critical(self, "Error", f"Fallo al sincronizar:\n{err}")

            self._excel_worker = BaseWorker(export_snapshot_to_master, snap.id)
            self._excel_worker.success.connect(on_success)
            self._excel_worker.error.connect(on_error)
            self._excel_worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fallo al iniciar sincronización: {str(e)}")


    def open_detail_view(self, category_id):
        self.current_category_id = category_id
        # Update title based on category clicked
        titles = {
            "net_worth": "Net Worth Details",
            "cash": "Cash & Liquidity",
            "ibkr": "Interactive Brokers Performance",
            "fundsmith": "Fundsmith & Other Funds",
            "savings": "Savings Rate Analysis",
            "cashflow": "Cashflow & Income vs Expenses"
        }
        self.lbl_detail_title.setText(titles.get(category_id, "Details"))
        
        # Clear existing detail charts
        while self.detail_chart_layout.count():
            item = self.detail_chart_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Create new detail chart instance
        self.current_detail_chart = HighchartsWidget()
        self.current_detail_chart.setMinimumHeight(400)
        self.current_detail_chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.detail_chart_layout.addWidget(self.current_detail_chart)
        
        # Switch to detail page
        self.stacked_widget.setCurrentIndex(1)
        
        # Render specific chart for this category
        # Pass current owner to detail rendering
        self.render_detail_chart(category_id, self.current_owner)

    def render_detail_chart(self, category_id, owner_name):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from core.database import DB_PATH, MonthlySnapshot, AccountBalance, Account, IncomeRecord
        import datetime
        
        try:
            engine = create_engine(f"sqlite:///{DB_PATH}")
            Session = sessionmaker(bind=engine)
            session = Session()

            snaps = session.query(MonthlySnapshot).order_by(MonthlySnapshot.month_id.asc()).all()
            if not snaps:
                session.close()
                return

            all_accounts = {a.id: a for a in session.query(Account).all()}
            
            categories = [snap.month_id for snap in snaps]
            timestamps = []
            for c in categories:
                y_str, m_str = c.split('-')
                dt = datetime.datetime(int(y_str), int(m_str), 1)
                timestamps.append(int(dt.timestamp() * 1000))
            
            # Pre-fetch incomes
            monthly_incomes = {}
            for inc in session.query(IncomeRecord).all():
                if inc.month_id not in monthly_incomes:
                    monthly_incomes[inc.month_id] = {"Rafa": 0, "Cris": 0, "Gastos_Rafa": 0, "Gastos_Cris": 0}
                monthly_incomes[inc.month_id][inc.owner] = (inc.net_amount or 0)
                monthly_incomes[inc.month_id][f"Gastos_{inc.owner}"] = (inc.total_expenses or 0)
            
            options = {
                'chart': {'type': 'line', 'zoomType': 'x'},
                'title': {'text': ''},
                'xAxis': {
                    'type': 'datetime',
                    'dateTimeLabelFormats': {'year': '%Y'},
                    'tickInterval': 365 * 24 * 3600 * 1000
                },
                'yAxis': {
                    'title': {'text': 'Value (£)'},
                    'labels': {'format': '£{value:,.0f}'}
                },
                'tooltip': {'valueDecimals': 0, 'shared': True, 'xDateFormat': '%b %Y'},
                'series': []
            }
            
            if category_id == "net_worth":
                options['chart']['type'] = 'area'
                data = []
                for i, snap in enumerate(snaps):
                    bals = session.query(AccountBalance).filter_by(snapshot_id=snap.id).all()
                    nw = 0
                    house = 0
                    mort = 0
                    ap_rafa = 0
                    ap_cris = 0
                    real_debt = 0
                    for b in bals:
                        acc = all_accounts.get(b.account_id)
                        if not acc: continue
                        if acc.type == 'equity' and 'aportado' not in acc.name.lower(): continue
                        val = b.current_value or 0
                        if acc.type == 'real_estate': house += val
                        elif acc.type == 'mortgage': mort += val
                        elif 'aportado hipoteca rafa' in acc.name.lower(): ap_rafa += val
                        elif 'aportado hipoteca cris' in acc.name.lower(): ap_cris += val
                        elif 'deuda equity' in acc.name.lower() or 'interna rafa' in acc.name.lower(): real_debt += val
                        else:
                            if acc.type == 'equity': continue
                            owner_group = acc.owner if acc.owner in ['Rafa', 'Cris'] else 'Comun'
                            if owner_name in ['Family', owner_group]:
                                nw += val
                                
                    if real_debt == 0 and (ap_rafa > 0 or ap_cris > 0):
                        calc_debt = (ap_cris - ap_rafa) / 2
                    else:
                        calc_debt = real_debt
                        
                    if owner_name == 'Family':
                        nw += (house - mort)
                    elif owner_name == 'Rafa':
                        nw += (house - mort) / 2 - calc_debt
                    elif owner_name == 'Cris':
                        nw += (house - mort) / 2 + calc_debt
                        
                    data.append([timestamps[i], nw])
                
                options['title']['text'] = f'{owner_name} - Historical Net Worth'
                options['series'] = [{
                    'name': 'Net Worth',
                    'data': data,
                    'color': '#ff9800',
                    'fillColor': {'linearGradient': {'x1':0,'y1':0,'x2':0,'y2':1}, 'stops': [[0,'rgba(255,152,0,0.5)'],[1,'rgba(255,152,0,0.05)']]}
                }]

            elif category_id == "cash":
                options['chart']['type'] = 'column'
                data = []
                for i, snap in enumerate(snaps):
                    bals = session.query(AccountBalance).filter_by(snapshot_id=snap.id).all()
                    tot = 0
                    for b in bals:
                        acc = all_accounts.get(b.account_id)
                        if not acc: continue
                        if acc.type in ['cash', 'bank'] or 'monetario' in acc.name.lower():
                            if owner_name == 'Family' or (acc.owner == owner_name) or (owner_name in acc.owner):
                                tot += (b.current_value or 0)
                    data.append([timestamps[i], tot])
                options['title']['text'] = f'{owner_name} - Cash & Liquidity History'
                options['series'] = [{'name': 'Cash', 'data': data, 'color': '#2196F3'}]

            elif category_id in ["ibkr", "fundsmith"]:
                options['chart']['type'] = 'line'
                data_val = []
                data_cost = []
                for i, snap in enumerate(snaps):
                    bals = session.query(AccountBalance).filter_by(snapshot_id=snap.id).all()
                    tot_v = 0
                    tot_c = 0
                    for b in bals:
                        acc = all_accounts.get(b.account_id)
                        if not acc: continue
                        if category_id in acc.name.lower() or (category_id == 'fundsmith' and 'fund' in acc.name.lower()):
                            if owner_name == 'Family' or (acc.owner == owner_name) or (owner_name in acc.owner):
                                tot_v += (b.current_value or 0)
                                tot_c += (b.invested_amount or 0)
                    data_val.append([timestamps[i], tot_v])
                    data_cost.append([timestamps[i], tot_c])
                    
                name_lbl = "Interactive Brokers" if category_id == "ibkr" else "Funds"
                options['title']['text'] = f'{owner_name} - {name_lbl} Performance'
                options['series'] = [
                    {'name': 'Current Value', 'data': data_val, 'color': '#4CAF50', 'lineWidth': 3},
                    {'name': 'Invested Capital', 'data': data_cost, 'color': '#AAAAAA', 'dashStyle': 'Dash'}
                ]
                
            elif category_id in ["income", "expenses", "cashflow", "savings"]:
                data_in = []
                data_ex = []
                data_cf = []
                data_sv = []
                
                for i, cat_month in enumerate(categories):
                    inc_val = 0
                    exp_val = 0
                    if cat_month in monthly_incomes:
                        vals = monthly_incomes[cat_month]
                        if owner_name == 'Rafa':
                            inc_val, exp_val = vals['Rafa'], vals['Gastos_Rafa']
                        elif owner_name == 'Cris':
                            inc_val, exp_val = vals['Cris'], vals['Gastos_Cris']
                        else:
                            c_exp = 0
                            s = session.query(MonthlySnapshot).filter_by(month_id=cat_month).first()
                            if s: c_exp = s.comun_expenses or 0
                            inc_val = vals['Rafa'] + vals['Cris']
                            exp_val = vals['Gastos_Rafa'] + vals['Gastos_Cris'] + c_exp
                     
                    data_in.append([timestamps[i], inc_val])
                    data_ex.append([timestamps[i], exp_val])
                    data_cf.append([timestamps[i], inc_val - exp_val])
                    data_sv.append([timestamps[i], ((inc_val - exp_val) / inc_val * 100) if inc_val > 0 else 0])
                
                if category_id == "income":
                    options['chart']['type'] = 'column'
                    options['title']['text'] = 'Income History'
                    options['series'] = [{'name': 'Income', 'data': data_in, 'color': '#4CAF50'}]
                elif category_id == "expenses":
                    options['chart']['type'] = 'column'
                    options['title']['text'] = 'Expenses History'
                    options['series'] = [{'name': 'Expenses', 'data': data_ex, 'color': '#F44336'}]
                elif category_id == "cashflow":
                    options['chart']['type'] = 'column'
                    options['title']['text'] = 'Income vs Expenses (Cashflow)'
                    options['series'] = [
                        {'name': 'Income', 'data': data_in, 'color': '#4CAF50'},
                        {'name': 'Expenses', 'data': data_ex, 'color': '#F44336'},
                        {'name': 'Cashflow', 'data': data_cf, 'type': 'spline', 'color': '#2196F3', 'marker': {'enabled': False}}
                    ]
                elif category_id == "savings":
                    options['chart']['type'] = 'spline'
                    options['title']['text'] = 'Savings Rate History'
                    options['tooltip'] = {'valueSuffix': '%'}
                    options['yAxis']['title']['text'] = 'Percentage (%)'
                    options['series'] = [{'name': 'Savings Rate', 'data': data_sv, 'color': '#FF9800'}]

            self.current_detail_chart.set_chart(options)
            
            # --- Update Bottom Detail Cards ---
            # Default empty function to handle widget clearing safely
            def clear_layout(layout):
                if layout is not None:
                    while layout.count():
                        item = layout.takeAt(0)
                        widget = item.widget()
                        if widget is not None:
                            widget.deleteLater()
                        else:
                            clear_layout(item.layout())

            clear_layout(self.detail_bottom_container)
            
            cards_hk_layout = QHBoxLayout()
            self.detail_bottom_container.addLayout(cards_hk_layout)
            self.detail_extra_layout = QVBoxLayout()
            self.detail_bottom_container.addLayout(self.detail_extra_layout)

            if len(options['series']) > 0 and len(options['series'][0]['data']) > 1:
                main_data = options['series'][0]['data']
                val_first = main_data[0][1]
                val_last = main_data[-1][1]
                val_prev = main_data[-2][1]
                
                curr_year = categories[-1].split('-')[0]
                val_ytd_start = val_first
                for i, c in enumerate(categories):
                    if c.startswith(curr_year):
                        val_ytd_start = main_data[max(0, i-1)][1]
                        break
                
                years = len(main_data) / 12.0
                
                cagr_total = 0
                if val_first > 0 and years > 0:
                    cagr_total = ((val_last / val_first) ** (1 / years) - 1) * 100
                    
                years_ytd = max(1, len([c for c in categories if c.startswith(curr_year)])) / 12.0
                growth_ytd = 0
                if val_ytd_start > 0:
                    growth_ytd = ((val_last - val_ytd_start) / val_ytd_start) * 100
                    
                growth_1m = 0
                if val_prev > 0:
                    growth_1m = (val_last - val_prev) / val_prev * 100
                
                abs_tot = val_last - val_first
                abs_ytd = val_last - val_ytd_start
                abs_1m = val_last - val_prev
                
                def f_pct(v): return f"{'+' if v>=0 else ''}{v:.2f}%"
                def f_abs(v): return f"{'+£' if v>=0 else '-£'}{abs(v):,.0f}"

                if category_id == "net_worth":
                    cards_hk_layout.addWidget(StatCard("CAGR desde el inicio", f_pct(cagr_total), f_abs(abs_tot)))
                    cards_hk_layout.addWidget(StatCard("Crecimiento YTD", f_pct(growth_ytd), f_abs(abs_ytd)))
                    cards_hk_layout.addWidget(StatCard("Crecimiento Último Mes", f_pct(growth_1m), f_abs(abs_1m)))
                    
                    # Extra: Pie Chart distribution grouped by Year
                    from PyQt6.QtWidgets import QComboBox
                    h_combo = QHBoxLayout()
                    lbl = QLabel("Distribución Anual:")
                    lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['text_main']};")
                    h_combo.addWidget(lbl)
                    
                    year_combo = QComboBox()
                    unq_years = sorted(list(set(c.split('-')[0] for c in categories)), reverse=True)
                    year_combo.addItems(unq_years)
                    year_combo.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']}; padding: 5px; border: 1px solid {COLORS['border']};")
                    h_combo.addWidget(year_combo)
                    h_combo.addStretch()
                    self.detail_extra_layout.addLayout(h_combo)

                    pie_widget = HighchartsWidget()
                    pie_widget.setMinimumHeight(400)
                    self.detail_extra_layout.addWidget(pie_widget)
                    
                    # Function to draw pie
                    def draw_nw_pie(year_str):
                        # Find the latest month for that year
                        month_candidates = [c for c in categories if c.startswith(year_str)]
                        if not month_candidates: return
                        target_m = sorted(month_candidates)[-1]
                        
                        snap = session.query(MonthlySnapshot).filter_by(month_id=target_m).first()
                        if not snap: return
                        
                        bals = session.query(AccountBalance).filter_by(snapshot_id=snap.id).all()
                        house=0; ibkr=0; fund=0; cash=0; mort=0; real_debt=0; ap_rafa=0; ap_cris=0;
                        for b in bals:
                            acc = all_accounts.get(b.account_id)
                            if not acc: continue
                            val = b.current_value or 0
                            
                            # debt/ap calculations needed for rafa/cris net_house calculation
                            if 'aportado hipoteca rafa' in acc.name.lower(): ap_rafa += val
                            elif 'aportado hipoteca cris' in acc.name.lower(): ap_cris += val
                            elif 'deuda equity' in acc.name.lower() or 'interna rafa' in acc.name.lower(): real_debt += val

                            if owner_name == 'Family' or owner_name in acc.owner or acc.owner == owner_name:
                                if acc.type == 'cash' or acc.type == 'bank' or 'monetario' in acc.name.lower(): cash += val
                                elif 'ibkr' in acc.name.lower(): ibkr += val
                                elif 'fund' in acc.name.lower() and acc.type == 'fund': fund += val
                                
                            if acc.type == 'real_estate': house += val
                            elif acc.type == 'mortgage': mort += val

                        if real_debt == 0 and (ap_rafa > 0 or ap_cris > 0):
                            calc_debt = (ap_cris - ap_rafa) / 2
                        else:
                            calc_debt = real_debt
                            
                        # Correct asset distribution logic
                        net_house = 0
                        if owner_name == 'Family':
                            net_house = max(house - mort, 0)
                        elif owner_name == 'Rafa':
                            net_house = max((house - mort)/2 - calc_debt, 0)
                        elif owner_name == 'Cris':
                            net_house = max((house - mort)/2 + calc_debt, 0)
                            
                        pie_data = []
                        if cash > 0: pie_data.append({'name': 'Cash', 'y': cash, 'color': '#2196F3'})
                        if ibkr > 0: pie_data.append({'name': 'IBKR', 'y': ibkr, 'color': '#F44336'})
                        if fund > 0: pie_data.append({'name': 'Funds', 'y': fund, 'color': '#4CAF50'})
                        if net_house > 0: pie_data.append({'name': 'Real Estate', 'y': net_house, 'color': '#9C27B0'})
                        
                        dist_options = {
                            'chart': {'type': 'pie'},
                            'title': {'text': f'Asset Allocation - {owner_name} ({target_m})'},
                            'tooltip': {'pointFormat': '{series.name}: <b>{point.percentage:.1f}%</b><br/>Value: £{point.y:,.0f}'},
                            'plotOptions': {'pie': {'allowPointSelect': True, 'cursor': 'pointer', 'dataLabels': {'enabled': True, 'format': '<b>{point.name}</b>: {point.percentage:.1f} %'}}},
                            'series': [{'name': 'Assets', 'colorByPoint': True, 'data': pie_data}]
                        }
                        pie_widget.set_chart(dist_options)
                        
                    # Save a strong reference
                    year_combo.currentTextChanged.connect(draw_nw_pie)
                    draw_nw_pie(year_combo.currentText())

                elif category_id == "income":
                    # Income specific calculations
                    # YTD Income is the SUM of all income in the current year, not the subtraction of first month!
                    income_ytd_sum = sum(v[1] for i, v in enumerate(main_data) if categories[i].startswith(curr_year))
                    
                    # Income specific cards
                    inc_card_day = StatCard("Ingreso por Día", "£0.00")
                    inc_card_ytd = StatCard("Total Ingreso YTD", f"£{income_ytd_sum:,.0f}")
                    inc_card_1 = StatCard("Var. Mes Anterior", f_pct(growth_1m), f_abs(abs_1m))
                    
                    cards_hk_layout.addWidget(inc_card_day)
                    cards_hk_layout.addWidget(inc_card_ytd)
                    cards_hk_layout.addWidget(inc_card_1)
                    
                    # Combobox for Day Income Year inside the card title layout ideally, but we can just put it above layout
                    from PyQt6.QtWidgets import QComboBox
                    h_combo = QHBoxLayout()
                    lbl = QLabel("Seleccione Año para Media de Ingreso:")
                    lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['text_main']};")
                    h_combo.addWidget(lbl)
                    
                    year_combo = QComboBox()
                    unq_years = sorted(list(set(c.split('-')[0] for c in categories)), reverse=True)
                    year_combo.addItems(unq_years)
                    year_combo.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']}; padding: 5px; border: 1px solid {COLORS['border']};")
                    h_combo.addWidget(year_combo)
                    h_combo.addStretch()
                    self.detail_extra_layout.addLayout(h_combo)

                    # Update day income logic
                    def update_day_income(year_str):
                        tot = 0
                        import datetime
                        # get all months in that year
                        yr_cats = [c for c in categories if c.startswith(year_str)]
                        for m_id in yr_cats:
                            if m_id in monthly_incomes:
                                vals = monthly_incomes[m_id]
                                if owner_name == 'Rafa': tot += vals['Rafa']
                                elif owner_name == 'Cris': tot += vals['Cris']
                                else: tot += (vals['Rafa'] + vals['Cris'])
                                
                        if year_str == str(datetime.datetime.now().year):
                            # Days since Jan 1st - assuming cobro to cobro could be just today's day number
                            import time
                            days = max(1, datetime.datetime.now().timetuple().tm_yday)
                        else:
                            days = 365 # ignoring leap basically
                            
                        inc_card_day.set_value(f"£{tot/days:,.2f}/día", f"Basado en {days} días (Total {year_str}: £{tot:,.0f})")
                        
                    year_combo.currentTextChanged.connect(update_day_income)
                    update_day_income(year_combo.currentText())

                    # Bar chart for total income per year
                    bar_widget = HighchartsWidget()
                    bar_widget.setMinimumHeight(400)
                    self.detail_extra_layout.addWidget(bar_widget)
                    
                    years_ordered = sorted(list(set(c.split('-')[0] for c in categories)))
                    bar_options = {
                        'chart': {'type': 'column'},
                        'title': {'text': f'Ingreso Total por Año - {owner_name}'},
                        'xAxis': {'categories': years_ordered},
                        'yAxis': {'title': {'text': '£'}},
                        'tooltip': {'valuePrefix': '£', 'shared': True},
                        'plotOptions': {'column': {'stacking': 'normal' if owner_name == 'Family' else None}},
                        'series': []
                    }
                    
                    if owner_name == 'Family':
                        data_rafa = []
                        data_cris = []
                        for y in years_ordered:
                            tot_r = 0; tot_c = 0
                            for m_id in [c for c in categories if c.startswith(y)]:
                                if m_id in monthly_incomes:
                                    tot_r += monthly_incomes[m_id]['Rafa']
                                    tot_c += monthly_incomes[m_id]['Cris']
                            data_rafa.append(tot_r)
                            data_cris.append(tot_c)
                        bar_options['series'].append({'name': 'Rafa', 'data': data_rafa, 'color': '#2196F3'})
                        bar_options['series'].append({'name': 'Cris', 'data': data_cris, 'color': '#E91E63'})
                    else:
                        bar_data = []
                        for y in years_ordered:
                            tot = 0
                            for m_id in [c for c in categories if c.startswith(y)]:
                                if m_id in monthly_incomes:
                                    vals = monthly_incomes[m_id]
                                    if owner_name == 'Rafa': tot += vals['Rafa']
                                    elif owner_name == 'Cris': tot += vals['Cris']
                            bar_data.append(tot)
                        bar_options['series'] = [{'name': 'Total Income', 'data': bar_data, 'color': '#4CAF50'}]
                        
                    bar_widget.set_chart(bar_options)

                else:
                    # Default cards
                    cards_hk_layout.addWidget(StatCard("CAGR", f_pct(cagr_total), f_abs(abs_tot)))
                    cards_hk_layout.addWidget(StatCard("YTD", f_pct(growth_ytd), f_abs(abs_ytd)))
                    cards_hk_layout.addWidget(StatCard("1 Month", f_pct(growth_1m), f_abs(abs_1m)))

            session.close()
            
        except Exception as e:
            print(f"Error rendering detail chart: {e}")
