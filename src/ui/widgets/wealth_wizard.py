from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QStackedWidget, QWidget, QLineEdit, 
                             QComboBox, QGridLayout, QDateEdit, QScrollArea, QMessageBox, QTextEdit, QFileDialog, QFrame)
from PyQt6.QtCore import Qt, QDate
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.database import DB_PATH, Account, MonthlySnapshot, AccountBalance, IncomeRecord
from ui.styles import COLORS
from ui.widgets.transaction_review_dialog import TransactionReviewDialog
import yfinance as yf
from core.bank_parser import analyze_bos_rafa, analyze_ibkr, analyze_bos_comun
from core.category_manager import get_categories

class WealthWizardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Monthly Data Eater - Ekomonos")
        self.resize(750, 650)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['background']}; }}
            QLabel {{ color: {COLORS['text_main']}; }}
            QLineEdit, QComboBox, QDateEdit {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px;
                color: {COLORS['text_main']};
            }}
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px 16px;
                color: {COLORS['text_main']};
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {COLORS['border']}; }}
            QFrame#card {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        self.header_lbl = QLabel("Step 1: Context & Parameters")
        self.header_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['primary']};")
        self.layout.addWidget(self.header_lbl)

        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)

        # Build steps
        self.build_page_1()
        self.build_page_rafa()
        self.build_page_cris()
        self.build_page_comun()
        
        # Navigation
        nav_layout = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.btn_back.clicked.connect(self.prev_step)
        self.btn_back.hide()
        
        self.btn_next = QPushButton("Next")
        self.btn_next.setStyleSheet(f"background-color: {COLORS['primary']}; color: #000;")
        self.btn_next.clicked.connect(self.next_step)
        
        nav_layout.addWidget(self.btn_back)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        self.layout.addLayout(nav_layout)
        
        # Fetch initial FX data
        self.fetch_fx()
        
        # Connect date change to load existing data
        self.month_input.dateChanged.connect(self.load_existing_data)
        # Call it once to load current default month
        self.load_existing_data()

    def build_page_1(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        lbl = QLabel("First, choose the month we are closing. I will try to fetch the GBP/EUR rate automatically.")
        lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 14px;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        
        grid = QGridLayout()
        grid.setSpacing(15)
        
        grid.addWidget(QLabel("Closing Month:"), 0, 0)
        self.month_input = QDateEdit()
        self.month_input.setDisplayFormat("MM/yyyy")
        self.month_input.setDate(QDate.currentDate().addMonths(-1))
        self.month_input.setCalendarPopup(True)
        grid.addWidget(self.month_input, 0, 1)
        
        grid.addWidget(QLabel("GBP to EUR Rate:"), 1, 0)
        self.gbp_input = QLineEdit("1.18")
        btn_refresh = QPushButton("Refresh rate")
        btn_refresh.clicked.connect(self.fetch_fx)
        
        h_fx = QHBoxLayout()
        h_fx.addWidget(self.gbp_input)
        h_fx.addWidget(btn_refresh)
        grid.addLayout(h_fx, 1, 1)
        
        layout.addLayout(grid)
        layout.addSpacing(20)
        
        lbl_notes = QLabel("Captain's Log (Notas del mes):")
        lbl_notes.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(lbl_notes)
        
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Ej: Se nos fue dinero en arreglar el coche. Pero terminamos de pagar la hipoteca. etc...")
        self.notes_input.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']}; border-radius: 6px; padding: 10px;")
        layout.addWidget(self.notes_input)
        
        self.stacked_widget.addWidget(page)

    def fetch_fx(self):
        try:
            ticker = yf.Ticker('GBPEUR=X')
            data = ticker.history(period='1wk')
            if not data.empty:
                val = data['Close'].iloc[-1]
                self.gbp_input.setText(f"{val:.4f}")
        except Exception as e:
            print("Could not fetch FX automatically:", e)

    def load_existing_data(self):
        try:
            engine = create_engine(f"sqlite:///{DB_PATH}")
            Session = sessionmaker(bind=engine)
            session = Session()
            
            m_id = self.month_input.date().toString("yyyy-MM")
            snap = session.query(MonthlySnapshot).filter_by(month_id=m_id).first()
            if not snap:
                session.close()
                return
                
            self.gbp_input.setText(str(snap.gbp_to_eur or "1.18"))
            self.comun_exp_input.setText(str(snap.comun_expenses or "0.00"))
            self.notes_input.setText(snap.notes or "")
            
            # Fill incomes
            rafa_inc = session.query(IncomeRecord).filter_by(month_id=m_id, owner="Rafa").first()
            if rafa_inc:
                self.rafa_gross.setText(str(rafa_inc.gross_amount or "0.00"))
                self.rafa_net.setText(str(rafa_inc.net_amount or "0.00"))
                self.rafa_exp.setText(str(rafa_inc.total_expenses or "0.00"))
                self.rafa_cuota.setText(str(rafa_inc.shared_quota or "0.00"))
                
            cris_inc = session.query(IncomeRecord).filter_by(month_id=m_id, owner="Cris").first()
            if cris_inc:
                self.cris_gross.setText(str(cris_inc.gross_amount or "0.00"))
                self.cris_net.setText(str(cris_inc.net_amount or "0.00"))
                self.cris_exp.setText(str(cris_inc.total_expenses or "0.00"))
                self.cris_cuota.setText(str(cris_inc.shared_quota or "0.00"))
                
            bals = session.query(AccountBalance).filter_by(snapshot_id=snap.id).all()
            bals_dict = {b.account_id: b for b in bals}
            
            all_accs = [getattr(self, 'rafa_accs', {}), getattr(self, 'cris_accs', {}), getattr(self, 'comun_accs', {})]
            for grid_dict in all_accs:
                if not grid_dict: continue
                for acc_id, meta in grid_dict.items():
                    if acc_id in bals_dict:
                        b = bals_dict[acc_id]
                        if meta['type'] == 'inv':
                            meta['aportado'].setText(f"{(b.invested_amount or 0):.2f}")
                            profit = (b.current_value or 0) - (b.invested_amount or 0)
                            meta['profit'].setText(f"{profit:.2f}")
                        else:
                            meta['current'].setText(f"{(b.current_value or 0):.2f}")
            session.close()
        except Exception as e:
            print("Failed to load existing data:", e)

    def build_page_rafa(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        lbl = QLabel("Upload your Bank of Scotland CSV. Edit classification and enter Manual IBKR metrics if active.")
        lbl.setStyleSheet(f"color: {COLORS['text_dim']}; margin-bottom: 10px;")
        layout.addWidget(lbl)
        
        # CSV UPLOADERS
        h_csv = QHBoxLayout()
        self.btn_csv_rafa = QPushButton("Upload BOS CSV (Rafa)")
        self.btn_csv_rafa.clicked.connect(self.load_bos_rafa)
        h_csv.addWidget(self.btn_csv_rafa)
        
        self.btn_edit_rafa = QPushButton("Edit Classifications")
        self.btn_edit_rafa.clicked.connect(self.edit_rafa_txs)
        self.btn_edit_rafa.hide()
        h_csv.addWidget(self.btn_edit_rafa)
        
        layout.addLayout(h_csv)
        self.rafa_txs = []
        self.rafa_master_bal = 0.0
        
        # RESULTS PANEL
        self.rafa_ai_lbl = QLabel("")
        self.rafa_ai_lbl.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
        layout.addWidget(self.rafa_ai_lbl)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        grid = QGridLayout(content)
        grid.setSpacing(12)
        
        # Incomes & Quotas
        grid.addWidget(QLabel("Ingresos Brutos (£):"), 0, 0)
        self.rafa_gross = QLineEdit("0.00")
        grid.addWidget(self.rafa_gross, 0, 1)
        
        grid.addWidget(QLabel("Ingresos Netos (£):"), 0, 2)
        self.rafa_net = QLineEdit("0.00")
        grid.addWidget(self.rafa_net, 0, 3)
        
        grid.addWidget(QLabel("Gastos Indiv. (£):"), 1, 0)
        self.rafa_exp = QLineEdit("0.00")
        grid.addWidget(self.rafa_exp, 1, 1)
        
        grid.addWidget(QLabel("Cuota a Familia (£):"), 1, 2)
        self.rafa_cuota = QLineEdit("0.00")
        grid.addWidget(self.rafa_cuota, 1, 3)
        
        # Dynamic Accounts
        grid.addWidget(QLabel("<b>Cuentas e Inversiones Rafa</b>"), 2, 0, 1, 4)
        
        try:
            engine = create_engine(f"sqlite:///{DB_PATH}")
            Session = sessionmaker(bind=engine)
            session = Session()
            accs = session.query(Account).filter(Account.is_active == True, Account.owner == "Rafa").all()
            session.close()
        except: accs = []
        
        self.rafa_accs = {}
        row = 3
        for acc in accs:
            lbl_name = QLabel(f"{acc.name}")
            lbl_name.setStyleSheet(f"color: {COLORS['text_dim']};")
            
            # Start Clean from January 2026 philosophy (Master Balance handles history)
            ap_val, pr_val, cur_val = "0.00", "0.00", "0.00"

            if acc.type in ['brokerage', 'fund']:
                grid.addWidget(lbl_name, row, 0)
                grid.addWidget(QLabel("Aportado:"), row, 1)
                inp_ap = QLineEdit(ap_val)
                grid.addWidget(inp_ap, row, 2)
                
                # We need profit too, let's span rows for investments
                row += 1
                grid.addWidget(QLabel("↳ Profit:"), row, 1)
                inp_pr = QLineEdit(pr_val)
                grid.addWidget(inp_pr, row, 2)
                
                self.rafa_accs[acc.id] = {'type': 'inv', 'aportado': inp_ap, 'profit': inp_pr, 'name': acc.name.lower(), 'hist_ap': self.safe_float(ap_val)}
            else:
                grid.addWidget(lbl_name, row, 0)
                if acc.type == 'equity':
                    lbl = "Total Aportado:"
                elif acc.type == 'loan':
                    lbl = "Deuda Actual:"
                else:
                    lbl = "Balance final:"
                grid.addWidget(QLabel(lbl), row, 1)
                inp_cur = QLineEdit(cur_val)
                grid.addWidget(inp_cur, row, 2)
                self.rafa_accs[acc.id] = {'type': 'base', 'current': inp_cur, 'name': acc.name.lower()}
            row += 1
            
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.stacked_widget.addWidget(page)

    def load_bos_rafa(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select BOS CSV", "", "CSV Files (*.csv)")
        if f:
            result = analyze_bos_rafa(f)
            self.rafa_txs = result.get('transactions', [])
            self.rafa_master_bal = result['metrics'].get('master_balance', 0.0)
            self.btn_edit_rafa.show()
            self.edit_rafa_txs()
            
    def edit_rafa_txs(self):
        if not self.rafa_txs: return
        
        cats = get_categories()
        
        dlg = TransactionReviewDialog(self.rafa_txs, cats, self)
        if dlg.exec():
            final_txs = dlg.get_results()
            self.rafa_txs = final_txs
            
            # Re-calculate
            ingresos = sum(t['credit'] for t in final_txs if "Ingreso" in t['category'])
            gastos = sum(t['debit'] for t in final_txs if "Gastos" in t['category'])
            cuota = sum(t['debit'] for t in final_txs if "Cuota" in t['category'])
            
            ibkr_rafa = sum(t['debit'] for t in final_txs if t['category'] == "Inversion: Rafa IBKR")
            fund_rafa = sum(t['debit'] for t in final_txs if t['category'] == "Inversion: Rafa Fundsmith")
            
            ibkr_cris = sum(t['debit'] for t in final_txs if t['category'] == "Inversion: Cris IBKR")
            fondo_cris = sum(t['debit'] for t in final_txs if "Fondo Monetario" in t['category'])
            fund_cris = sum(t['debit'] for t in final_txs if t['category'] == "Inversion: Cris Fundsmith")
            
            self.rafa_net.setText(f"{ingresos:.2f}")
            self.rafa_exp.setText(f"{gastos:.2f}")
            self.rafa_cuota.setText(f"{cuota:.2f}")
            
            # Inversiones/Fondos - Removed internal overrides (Let user type from Excel)
                    
            if hasattr(self, 'cris_accs'):
                for k, v in self.cris_accs.items():
                    if 'monetario' in v['name'].lower() and fondo_cris > 0:
                        if v['type'] == 'base':
                            v['current'].setText(f"{fondo_cris:.2f}")
                        
            if self.rafa_master_bal > 0:
                for k, v in self.rafa_accs.items():
                    if 'master' in v['name'].lower() and v['type'] == 'base':
                        v['current'].setText(f"{self.rafa_master_bal:.2f}")

            # Removed IBKR Re-calculation auto-magic (Now purely manual master balance driven)

            msg = f"✓ AI Analysis Confirmed: £{ingresos:.0f} Net / £{gastos:.0f} Exp / £{cuota:.0f} Family."
            self.rafa_ai_lbl.setText(msg)



    def build_page_cris(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        lbl = QLabel("Upload Cris's BOS CSV (Optional) or fill manually.")
        lbl.setStyleSheet(f"color: {COLORS['text_dim']}; margin-bottom: 10px;")
        layout.addWidget(lbl)
        
        h_csv2 = QHBoxLayout()
        self.btn_csv_cris = QPushButton("Upload BOS CSV (Cris)")
        self.btn_csv_cris.clicked.connect(self.load_bos_cris)
        h_csv2.addWidget(self.btn_csv_cris)
        
        self.btn_edit_cris = QPushButton("Edit Classifications")
        self.btn_edit_cris.clicked.connect(self.edit_cris_txs)
        self.btn_edit_cris.hide()
        h_csv2.addWidget(self.btn_edit_cris)
        
        layout.addLayout(h_csv2)
        self.cris_txs = []
        self.cris_master_bal = 0.0
        
        self.cris_ai_lbl = QLabel("")
        self.cris_ai_lbl.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
        layout.addWidget(self.cris_ai_lbl)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        grid = QGridLayout(content)
        grid.setSpacing(12)
        
        grid.addWidget(QLabel("Ingresos Brutos (£):"), 0, 0)
        self.cris_gross = QLineEdit("0.00")
        grid.addWidget(self.cris_gross, 0, 1)
        
        grid.addWidget(QLabel("Ingresos Netos (£):"), 0, 2)
        self.cris_net = QLineEdit("0.00")
        grid.addWidget(self.cris_net, 0, 3)
        
        grid.addWidget(QLabel("Gastos Indiv. (£):"), 1, 0)
        self.cris_exp = QLineEdit("0.00")
        grid.addWidget(self.cris_exp, 1, 1)
        
        grid.addWidget(QLabel("Cuota a Familia (£):"), 1, 2)
        self.cris_cuota = QLineEdit("0.00")
        grid.addWidget(self.cris_cuota, 1, 3)
        
        # Dynamic Accounts
        grid.addWidget(QLabel("<b>Cuentas e Inversiones Cris</b>"), 2, 0, 1, 4)
        
        try:
            engine = create_engine(f"sqlite:///{DB_PATH}")
            Session = sessionmaker(bind=engine)
            session = Session()
            accs = session.query(Account).filter(Account.is_active == True, Account.owner == "Cris").all()
            session.close()
        except: accs = []
        
        self.cris_accs = {}
        row = 3
        for acc in accs:
            lbl_name = QLabel(f"{acc.name}")
            lbl_name.setStyleSheet(f"color: {COLORS['text_dim']};")
            
            # Start Clean
            ap_val, pr_val, cur_val = "0.00", "0.00", "0.00"

            if acc.type in ['brokerage', 'fund']:
                grid.addWidget(lbl_name, row, 0)
                grid.addWidget(QLabel("Aportado:"), row, 1)
                inp_ap = QLineEdit(ap_val)
                grid.addWidget(inp_ap, row, 2)
                
                row += 1
                grid.addWidget(QLabel("↳ Profit:"), row, 1)
                inp_pr = QLineEdit(pr_val)
                grid.addWidget(inp_pr, row, 2)
                
                self.cris_accs[acc.id] = {'type': 'inv', 'aportado': inp_ap, 'profit': inp_pr, 'name': acc.name.lower(), 'hist_ap': self.safe_float(ap_val)}
            else:
                grid.addWidget(lbl_name, row, 0)
                if acc.type == 'equity':
                    lbl = "Total Aportado:"
                elif acc.type == 'loan':
                    lbl = "Deuda Actual:"
                else:
                    lbl = "Balance final:"
                grid.addWidget(QLabel(lbl), row, 1)
                inp_cur = QLineEdit(cur_val)
                grid.addWidget(inp_cur, row, 2)
                self.cris_accs[acc.id] = {'type': 'base', 'current': inp_cur, 'name': acc.name.lower()}
            row += 1
            
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.stacked_widget.addWidget(page)

    def load_bos_cris(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select BOS CSV", "", "CSV Files (*.csv)")
        if f:
            result = analyze_bos_rafa(f) # Basically same logic applies for her net income and expenses
            self.cris_txs = result.get('transactions', [])
            self.cris_master_bal = result['metrics'].get('master_balance', 0.0)
            self.btn_edit_cris.show()
            self.edit_cris_txs()
            
    def edit_cris_txs(self):
        if not self.cris_txs: return
        
        cats = get_categories()
        
        dlg = TransactionReviewDialog(self.cris_txs, cats, self)
        if dlg.exec():
            final_txs = dlg.get_results()
            self.cris_txs = final_txs
            
            ingresos = sum(t['credit'] for t in final_txs if "Ingreso" in t['category'])
            gastos = sum(t['debit'] for t in final_txs if "Gastos" in t['category'])
            cuota = sum(t['debit'] for t in final_txs if "Cuota" in t['category'])
            
            ibkr_cris = sum(t['debit'] for t in final_txs if t['category'] == "Inversion: Cris IBKR")
            fondo_cris = sum(t['debit'] for t in final_txs if "Fondo Monetario" in t['category'])
            fund_cris = sum(t['debit'] for t in final_txs if t['category'] == "Inversion: Cris Fundsmith")
            
            self.cris_net.setText(f"{ingresos:.2f}")
            self.cris_exp.setText(f"{gastos:.2f}")
            self.cris_cuota.setText(f"{cuota:.2f}")
            
            for k, v in self.cris_accs.items():
                if 'ibkr' in v['name'].lower() and v['type'] == 'inv' and ibkr_cris > 0:
                    v['aportado'].setText(f"{(v.get('hist_ap', 0.0) + ibkr_cris):.2f}")
                if 'fundsmith' in v['name'].lower() and v['type'] == 'inv' and fund_cris > 0:
                    v['aportado'].setText(f"{(v.get('hist_ap', 0.0) + fund_cris):.2f}")
                    
                if 'monetario' in v['name'].lower() and fondo_cris > 0:
                    if v['type'] == 'inv':
                        v['aportado'].setText(f"{(v.get('hist_ap', 0.0) + fondo_cris):.2f}")
                    else:
                        v['current'].setText(f"{fondo_cris:.2f}")
            
            if self.cris_master_bal > 0:
                for k, v in self.cris_accs.items():
                    if 'master' in v['name'].lower() and v['type'] == 'base':
                        v['current'].setText(f"{self.cris_master_bal:.2f}")

            msg = f"✓ AI Analysis Confirmed: £{ingresos:.0f} Net / £{gastos:.0f} Personal Exp."
            self.cris_ai_lbl.setText(msg)

    def build_page_comun(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        lbl = QLabel("Upload Family/Comun BOS CSV. I will find Mortgage and common expenses.")
        lbl.setStyleSheet(f"color: {COLORS['text_dim']}; margin-bottom: 10px;")
        layout.addWidget(lbl)
        
        h_csv3 = QHBoxLayout()
        self.btn_csv_comun = QPushButton("Upload BOS Comun CSV")
        self.btn_csv_comun.clicked.connect(self.load_bos_comun)
        h_csv3.addWidget(self.btn_csv_comun)
        
        self.btn_edit_comun = QPushButton("Edit Classifications")
        self.btn_edit_comun.clicked.connect(self.edit_comun_txs)
        self.btn_edit_comun.hide()
        h_csv3.addWidget(self.btn_edit_comun)
        
        layout.addLayout(h_csv3)
        self.comun_txs = []
        self.comun_master_bal = 0.0
        
        self.comun_ai_lbl = QLabel("")
        self.comun_ai_lbl.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
        layout.addWidget(self.comun_ai_lbl)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        grid = QGridLayout(content)
        grid.setSpacing(12)
        
        grid.addWidget(QLabel("Gastos Familiares Puros (£):"), 0, 0)
        self.comun_exp_input = QLineEdit("0.00")
        grid.addWidget(self.comun_exp_input, 0, 1)
        
        # Dynamic Accounts
        grid.addWidget(QLabel("<b>Cuentas de la Familia (Casa, Comun...)</b>"), 1, 0, 1, 2)
        
        try:
            engine = create_engine(f"sqlite:///{DB_PATH}")
            Session = sessionmaker(bind=engine)
            session = Session()
            accs = session.query(Account).filter(Account.is_active == True, Account.owner == "Comun").all()
            session.close()
        except: accs = []
        
        self.comun_accs = {}
        row = 2
        for acc in accs:
            lbl_name = QLabel(f"{acc.name}")
            lbl_name.setStyleSheet(f"color: {COLORS['text_dim']};")
            
            cur_val = "0.00"
            if acc.type == 'real_estate':
                try:
                    engine = create_engine(f"sqlite:///{DB_PATH}")
                    S2 = sessionmaker(bind=engine)
                    s2 = S2()
                    last_bal = s2.query(AccountBalance).filter_by(account_id=acc.id).order_by(AccountBalance.id.desc()).first()
                    if last_bal and last_bal.current_value:
                        new_val = last_bal.current_value * (1 + (0.02 / 12))
                        cur_val = f"{new_val:.2f}"
                    s2.close()
                except: pass
            
            grid.addWidget(lbl_name, row, 0)
            
            lbl_type = "Balance final:"
            if acc.type == 'mortgage': lbl_type = "Deuda Restante Hipoteca:"
            elif acc.type == 'real_estate': lbl_type = "Valor Estimado Casa:"
            elif acc.type == 'equity': lbl_type = "Total Aportado:"
            elif acc.type == 'loan': lbl_type = "Deuda Actual:"
            
            grid.addWidget(QLabel(lbl_type), row, 1)
            inp_cur = QLineEdit(cur_val)
            grid.addWidget(inp_cur, row, 2)
            self.comun_accs[acc.id] = {'type': 'base', 'current': inp_cur, 'name': acc.name.lower()}
            row += 1
            
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.stacked_widget.addWidget(page)

    def load_bos_comun(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Comun BOS CSV", "", "CSV Files (*.csv)")
        if f:
            result = analyze_bos_comun(f)
            self.comun_txs = result.get('transactions', [])
            self.comun_master_bal = result['metrics'].get('master_balance', 0.0)
            self.btn_edit_comun.show()
            self.edit_comun_txs()
            
    def edit_comun_txs(self):
        if not self.comun_txs: return
        
        cats = get_categories()
        
        dlg = TransactionReviewDialog(self.comun_txs, cats, self)
        if dlg.exec():
            final_txs = dlg.get_results()
            self.comun_txs = final_txs
            
            gastos = sum(t['debit'] for t in final_txs if "Gastos " in t['category'] and "Hipoteca/Alquiler" not in t['category'])
            inc_comun = sum(t['credit'] for t in final_txs if "Aportacion de Socio" in t['category'])
            hipoteca = sum(t['debit'] for t in final_txs if "Hipoteca/Alquiler" in t['category'])
            
            self.comun_exp_input.setText(f"{gastos:.2f}")
            
            if self.comun_master_bal > 0:
                for k, v in self.comun_accs.items():
                    if 'comun' in v['name'].lower() and v['type'] == 'base':
                        v['current'].setText(f"{self.comun_master_bal:.2f}")
                        
            msg = f"✓ Family Analysis Confirmed: £{gastos:.0f} Expenses detected."
            if inc_comun > 0:
                msg += f"\nDetected £{inc_comun:.0f} coming from you both."
            if hipoteca > 0:
                msg += f"\nDetected £{hipoteca:.0f} mortgage payment."
            self.comun_ai_lbl.setText(msg)

    # --- Navigation ---
    def prev_step(self):
        curr = self.stacked_widget.currentIndex()
        if curr > 0: self.stacked_widget.setCurrentIndex(curr - 1)
        self.update_nav()

    def next_step(self):
        curr = self.stacked_widget.currentIndex()
        if curr < self.stacked_widget.count() - 1:
            self.stacked_widget.setCurrentIndex(curr + 1)
        else:
            if self.save_to_db(): self.accept()
        self.update_nav()

    def update_nav(self):
        curr = self.stacked_widget.currentIndex()
        titles = ["Step 1: Parameters", "Step 2: Rafa's Ledger", "Step 3: Cris's Ledger", "Step 4: Family & Finalize"]
        self.header_lbl.setText(titles[curr] if curr < len(titles) else "")
        self.btn_back.setVisible(curr > 0)
        self.btn_next.setText("Save & Finalize (Excel)" if curr == self.stacked_widget.count() - 1 else "Next Steps")

    def safe_float(self, text):
        try: return float(text.replace(',', '').replace('£','').replace('€',''))
        except: return 0.0

    def save_to_db(self):
        try:
            engine = create_engine(f"sqlite:///{DB_PATH}")
            Session = sessionmaker(bind=engine)
            session = Session()
            
            m_id = self.month_input.date().toString("yyyy-MM")
            snap = session.query(MonthlySnapshot).filter_by(month_id=m_id).first()
            if snap:
                reply = QMessageBox.question(self, "Overwrite?", f"Data for {m_id} already exists. Overwrite?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    session.close(); return False
            else:
                snap = MonthlySnapshot(month_id=m_id)
                session.add(snap)
                
            snap.gbp_to_eur = self.safe_float(self.gbp_input.text())
            snap.comun_expenses = self.safe_float(self.comun_exp_input.text())
            snap.notes = self.notes_input.toPlainText()
            session.flush()
            
            # RAFA Incomes
            rafa_inc = session.query(IncomeRecord).filter_by(month_id=m_id, owner="Rafa").first()
            if not rafa_inc: rafa_inc = IncomeRecord(month_id=m_id, owner="Rafa"); session.add(rafa_inc)
            rafa_inc.gross_amount = self.safe_float(self.rafa_gross.text())
            rafa_inc.net_amount = self.safe_float(self.rafa_net.text())
            rafa_inc.total_expenses = self.safe_float(self.rafa_exp.text())
            rafa_inc.shared_quota = self.safe_float(self.rafa_cuota.text())
            
            # CRIS Incomes
            cris_inc = session.query(IncomeRecord).filter_by(month_id=m_id, owner="Cris").first()
            if not cris_inc: cris_inc = IncomeRecord(month_id=m_id, owner="Cris"); session.add(cris_inc)
            cris_inc.gross_amount = self.safe_float(self.cris_gross.text())
            cris_inc.net_amount = self.safe_float(self.cris_net.text())
            cris_inc.total_expenses = self.safe_float(self.cris_exp.text())
            cris_inc.shared_quota = self.safe_float(self.cris_cuota.text())
            
            # ALL Balances (Combines dicts)
            # Combine safely to avoid key collision if acc_ids overlap (they shouldn't, but just in case)
            all_acc_inputs = {}
            all_acc_inputs.update(self.rafa_accs)
            all_acc_inputs.update(self.cris_accs)
            all_acc_inputs.update(self.comun_accs)
            
            for acc_id, dict_val in all_acc_inputs.items():
                bal = session.query(AccountBalance).filter_by(account_id=acc_id, snapshot_id=snap.id).first()
                if not bal: bal = AccountBalance(account_id=acc_id, snapshot_id=snap.id); session.add(bal)
                
                if dict_val['type'] == 'inv':
                    bal.invested_amount = self.safe_float(dict_val['aportado'].text())
                    bal.current_value = bal.invested_amount + self.safe_float(dict_val['profit'].text())
                else:
                    bal.invested_amount = 0.0
                    bal.current_value = self.safe_float(dict_val['current'].text())
                    
            session.commit()
            session.close()
            
            # Bóveda del tiempo backup
            try:
                import shutil, os
                from datetime import datetime
                db_dir = os.path.dirname(DB_PATH)
                backup_dir = os.path.join(db_dir, "backups")
                os.makedirs(backup_dir, exist_ok=True)
                backup_name = f"fortress_vault_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(DB_PATH, os.path.join(backup_dir, backup_name))
            except: pass
            
            # Write to Excel Master (Asynchronously in background)
            try:
                from core.excel_bridge import export_snapshot_to_master
                from core.workers.base_worker import BaseWorker
                
                def handle_excel_result(result):
                    if not result:
                        QMessageBox.warning(None, "Excel Warning", "No se pudo escribir en Master_Balance.xlsx.\n¿Está abierto por Excel?\n\nConsulta src/logs/excel_bridge.log para más detalles.")
                
                def handle_excel_error(err):
                     print("Failed to use excel bridge in worker:", err)
                     QMessageBox.critical(None, "Excel Error", f"Fallo al escribir en Excel Master:\n{err}")

                self._excel_worker = BaseWorker(export_snapshot_to_master, snap.id)
                self._excel_worker.success.connect(handle_excel_result)
                self._excel_worker.error.connect(handle_excel_error)
                self._excel_worker.start()
            except Exception as e:
                print("Failed to start excel bridge worker:", e)

                
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{str(e)}")
            return False
