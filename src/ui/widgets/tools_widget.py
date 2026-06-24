from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QStackedWidget, QLineEdit, 
                             QFormLayout, QFrame, QMessageBox, QComboBox, QScrollArea)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont
from ui.styles import COLORS

class CalculatorBase(QWidget):
    def __init__(self, title, description):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {COLORS['primary']}; font-size: 24px; font-weight: bold;")
        layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 14px;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)
        
        # Content Container (Form)
        form_frame = QFrame()
        form_frame.setStyleSheet(f"background-color: {COLORS['surface_light']}; border-radius: 8px; border: 1px solid {COLORS['border']};")
        self.form_layout = QFormLayout(form_frame)
        self.form_layout.setContentsMargins(20, 20, 20, 20)
        self.form_layout.setSpacing(15)
        layout.addWidget(form_frame)
        
        # Result Area
        self.lbl_result = QLabel("")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_result.setStyleSheet(f"color: {COLORS['success']}; font-size: 20px; font-weight: bold; padding: 10px;")
        layout.addWidget(self.lbl_result)
        
        layout.addStretch()

    def add_input(self, label, placeholder="0"):
        inp = QLineEdit()
        inp.setPlaceholderText(str(placeholder))
        inp.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']}; padding: 8px; border: 1px solid {COLORS['border']}; border-radius: 4px;")
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {COLORS['text_main']}; font-weight: bold;")
        self.form_layout.addRow(lbl, inp)
        return inp
        
    def add_button(self, text, handler):
        btn = QPushButton(text)
        btn.setStyleSheet(f"background-color: {COLORS['primary']}; color: white; padding: 10px; font-weight: bold; border-radius: 4px; border: none;")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(handler)
        self.form_layout.addRow("", btn) # Centered or fill? Form layout makes it fill 2nd col usually

# 1. CAGR
class CagrCalculator(CalculatorBase):
    def __init__(self):
        super().__init__("CAGR Calculator", "Calculate the Compound Annual Growth Rate.")
        self.inp_start = self.add_input("Start Value:", "e.g. 100")
        self.inp_end = self.add_input("End Value:", "e.g. 200")
        self.inp_years = self.add_input("Years:", "e.g. 5")
        self.add_button("Calculate CAGR", self.calculate)
        
    def calculate(self):
        try:
            start = float(self.inp_start.text())
            end = float(self.inp_end.text())
            years = float(self.inp_years.text())
            
            if start == 0 or years == 0:
                self.lbl_result.setText("Invalid Input")
                return
                
            cagr = ((end / start) ** (1 / years)) - 1
            self.lbl_result.setText(f"CAGR: {cagr * 100:.2f}%")
        except ValueError:
            self.lbl_result.setText("Use numeric values")

# 2. Compound Interest
class CompoundInterestCalculator(CalculatorBase):
    def __init__(self):
        super().__init__("Compound Interest", "Calculate future value with compound interest.")
        self.inp_principal = self.add_input("Initial Investment:", "1000")
        self.inp_monthly = self.add_input("Monthly Contribution:", "100")
        self.inp_rate = self.add_input("Annual Interest Rate (%):", "7")
        self.inp_years = self.add_input("Years to Grow:", "10")
        self.add_button("Calculate Future Value", self.calculate)
        
    def calculate(self):
        try:
            p = float(self.inp_principal.text() or 0)
            pmt = float(self.inp_monthly.text() or 0)
            r = float(self.inp_rate.text() or 0) / 100
            t = float(self.inp_years.text() or 0)
            n = 12 # Monthly compounding assumption
            
            # FV of Principal: P * (1 + r/n)^(nt)
            fv_p = p * (1 + r/n)**(n*t)
            
            # FV of Contributions: PMT * [ (1 + r/n)^(nt) - 1 ] / (r/n)
            if r == 0:
                fv_c = pmt * n * t
            else:
                fv_c = pmt * ((1 + r/n)**(n*t) - 1) / (r/n)
                
            total = fv_p + fv_c
            total_contrib = p + (pmt * n * t)
            interest = total - total_contrib
            
            self.lbl_result.setText(f"Future Value: ${total:,.2f}\nTotal Interest: ${interest:,.2f}")
        except ValueError:
            self.lbl_result.setText("Use numeric values")

# 3. Growth %
class GrowthCalculator(CalculatorBase):
    def __init__(self):
        super().__init__("Growth Percentage", "Calculate the percentage change between two numbers.")
        self.inp_old = self.add_input("Old Value:", "100")
        self.inp_new = self.add_input("New Value:", "150")
        self.add_button("Calculate Growth", self.calculate)
        
    def calculate(self):
        try:
            old = float(self.inp_old.text())
            new = float(self.inp_new.text())
            
            if old == 0:
                self.lbl_result.setText("Infinite Growth (Old=0)")
                return
                
            change = new - old
            pct = (change / old) * 100
            self.lbl_result.setText(f"Change: {change:,.2f}\nPercentage: {pct:+.2f}%")
        except ValueError:
            self.lbl_result.setText("Use numeric values")

# 4. Mortgage
class MortgageCalculator(CalculatorBase):
    def __init__(self):
        super().__init__("Mortgage Calculator", "Estimate monthly mortgage payments.")
        self.inp_loan = self.add_input("Loan Amount:", "200000")
        self.inp_rate = self.add_input("Annual Interest Rate (%):", "4.5")
        self.inp_years = self.add_input("Loan Term (Years):", "30")
        self.add_button("Calculate Payment", self.calculate)
        
    def calculate(self):
        try:
            loan = float(self.inp_loan.text())
            r_annual = float(self.inp_rate.text()) / 100
            years = float(self.inp_years.text())
            
            if r_annual == 0:
                payment = loan / (years * 12)
            else:
                r_monthly = r_annual / 12
                n_months = years * 12
                
                # M = P [ i(1 + i)^n ] / [ (1 + i)^n – 1 ]
                numerator = r_monthly * (1 + r_monthly)**n_months
                denominator = (1 + r_monthly)**n_months - 1
                payment = loan * (numerator / denominator)
                
            self.lbl_result.setText(f"Monthly Payment: ${payment:,.2f}")
        except ValueError:
            self.lbl_result.setText("Use numeric values")

# 5. Discounted Cash Flow (DCF)
class DcfCalculator(CalculatorBase):
    def __init__(self):
        super().__init__("DCF Valuation", "Simple 2-stage Discounted Cash Flow model.")
        self.inp_fcf = self.add_input("Current FCF:", "100")
        self.inp_growth = self.add_input("Growth Rate (Next 5y) %:", "10")
        self.inp_term = self.add_input("Terminal Growth % (Perpetuity):", "2.5")
        self.inp_discount = self.add_input("Discount Rate (WACC) %:", "9")
        self.inp_shares = self.add_input("Shares Outstanding (m):", "50")
        self.add_button("Calculate Fair Value", self.calculate)
        
    def calculate(self):
        try:
            fcf = float(self.inp_fcf.text())
            g = float(self.inp_growth.text()) / 100
            g_term = float(self.inp_term.text()) / 100
            wacc = float(self.inp_discount.text()) / 100
            shares = float(self.inp_shares.text())
            
            if wacc <= g_term:
                self.lbl_result.setText("Error: WACC must be > Terminal Growth")
                return
            
            # Stage 1: 5 Years
            npv_stage1 = 0
            curr_fcf = fcf
            for i in range(1, 6):
                curr_fcf *= (1 + g)
                npv_stage1 += curr_fcf / ((1 + wacc)**i)
                
            # Stage 2: Terminal Value
            # TV = (FCF5 * (1 + g_term)) / (WACC - g_term)
            terminal_val = (curr_fcf * (1 + g_term)) / (wacc - g_term)
            pv_terminal = terminal_val / ((1 + wacc)**5)
            
            total_val = npv_stage1 + pv_terminal
            price_per_share = total_val / shares
            
            self.lbl_result.setText(f"Enterprise Value: ${total_val:,.2f}\nFair Value per Share: ${price_per_share:,.2f}")
        except ValueError:
            self.lbl_result.setText("Use numeric values")

# 6. Reverse DCF
class ReverseDcfCalculator(CalculatorBase):
    def __init__(self):
        super().__init__("Reverse DCF", "Implied Growth Rate from current Stock Price.")
        self.inp_price = self.add_input("Current Stock Price:", "150")
        self.inp_eps = self.add_input("EPS / FCF per Share:", "8")
        self.inp_discount = self.add_input("Discount Rate (WACC) %:", "10")
        self.inp_term = self.add_input("Terminal Growth %:", "3")
        self.add_button("Calculate Implied Growth", self.calculate)
        
    def calculate(self):
        try:
            price = float(self.inp_price.text())
            eps = float(self.inp_eps.text())
            wacc = float(self.inp_discount.text()) / 100
            g_term = float(self.inp_term.text()) / 100
            
            # Solving for g (Growth for first 10 years, simplified) is complex to do analytically.
            # We will approximate iteratively.
            
            low = 0.0
            high = 1.0 # 100% growth
            implied_g = 0
            
            for _ in range(20): # 20 iterations is plenty for binary search
                mid = (low + high) / 2
                
                # Calc Value with 'mid' growth
                curr_eps = eps
                val = 0
                for i in range(1, 11): # 10 year model for reverse usually
                    curr_eps *= (1 + mid)
                    val += curr_eps / ((1 + wacc)**i)
                    
                tv = (curr_eps * (1 + g_term)) / (wacc - g_term)
                val += tv / ((1 + wacc)**10)
                
                if val > price:
                    high = mid
                else:
                    low = mid
            
            implied_g = (low + high) / 2
            
            self.lbl_result.setText(f"Implied Growth (10y): {implied_g * 100:.2f}%")
        except ValueError:
            self.lbl_result.setText("Use numeric values")

# 7. Resources Page
class ResourcesPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl = QLabel("External Resources")
        lbl.setStyleSheet(f"color: {COLORS['primary']}; font-size: 24px; font-weight: bold;")
        layout.addWidget(lbl)
        
        btn = QPushButton("Damodaran Sector Multiples (NYU)")
        btn.setFixedSize(300, 60)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']}; 
                color: black; 
                font-size: 16px; 
                font-weight: bold;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #ffd700;
            }}
        """)
        btn.clicked.connect(self.open_url)
        layout.addWidget(btn)
        
    def open_url(self):
        from ui.styles import open_url_chrome
        open_url_chrome("https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/vebitda.html")

# --- MAIN TOOLS WIDGET ---

class ToolsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Sidebar
        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(220)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['surface']};
                border-right: 1px solid {COLORS['border']};
                outline: none;
            }}
            QListWidget::item {{
                padding: 15px;
                color: {COLORS['text_dim']};
                font-size: 14px;
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['surface_light']};
                color: {COLORS['primary']};
                border-left: 3px solid {COLORS['primary']};
            }}
        """)
        layout.addWidget(self.list_widget)
        
        # 2. Content Stack
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Register Tools
        self.tools = [
            ("CAGR / Return", CagrCalculator()),
            ("Compound Interest", CompoundInterestCalculator()),
            ("Growth %", GrowthCalculator()),
            ("Mortgage Calc", MortgageCalculator()),
            ("DCF Valuation", DcfCalculator()),
            ("Reverse DCF", ReverseDcfCalculator()),
            ("Resources", ResourcesPage())
        ]
        
        for name, widget in self.tools:
            self.list_widget.addItem(name)
            self.stack.addWidget(widget)
            
        self.list_widget.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.list_widget.setCurrentRow(0)
