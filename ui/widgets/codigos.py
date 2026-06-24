from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout,
                             QGridLayout, QPushButton, QDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from ui.styles import COLORS
from core.sne_manager import SNE_TYPES, SNE_PERIODS

SPECIAL_SITUATIONS_GLOSSARY = [
    # Global Parameters
    {"code": "SPREAD", "type": "Global", "desc": "Spread Bruto: (Target - Current) / Current"},
    {"code": "D_CLOSE", "type": "Global", "desc": "Days to Close: Target Date - Current Date"},
    {"code": "IRR_ANN", "type": "Global", "desc": "TIR Anualizada: [(1 + Spread)^(365/Days) - 1]"},
    {"code": "EV", "type": "Global", "desc": "Expected Value: (Prob * Profit) - ((1-Prob) * Loss)"},
    
    # Block 1 Example
    {"code": "MERGER_CASH", "type": "M&A", "desc": "Merger Arb (Cash): Arb on cash buyout spread."},
    {"code": "MERGER_STOCK", "type": "M&A", "desc": "Merger Arb (Stock): Arb on exchange ratio (Long Target / Short Acq)."},
    {"code": "CVR", "type": "M&A", "desc": "Contingent Value Right: Payout if milestone hit."},
    {"code": "LBO", "type": "M&A", "desc": "Going Private: Private Equity buyout (credit risk key)."},
    {"code": "LITIGATION", "type": "M&A", "desc": "Litigation Arb: Bet on lawsuit outcome."},
    
    # Block 2
    {"code": "SPINOFF", "type": "Spinouff", "desc": "Spin-off: Share distribution of sub (Forced selling opp)."},
    {"code": "SPLITOFF", "type": "Spinoff", "desc": "Split-off: Exchange offer (Voluntary share swap)."},
    {"code": "RMT", "type": "Spinoff", "desc": "Reverse Morris Trust: Tax-free spin + merger."},
    {"code": "CARVEOUT", "type": "Spinoff", "desc": "Equity Carve-out: IPO of a subsidiary."},
    {"code": "LIQUIDATION", "type": "Spinoff", "desc": "Liquidation: Dissolution and cash distribution."},
    
    # Block 3
    {"code": "ODD_LOT", "type": "Capital", "desc": "Odd Lot Tender: Priority buyback for <100 shares."},
    {"code": "DUTCH_AUC", "type": "Capital", "desc": "Dutch Auction: Shareholders set sell price within range."},
    {"code": "RIGHTS", "type": "Capital", "desc": "Rights Offering: Discounted share issuance to existing holders."},
    {"code": "SPAC_ARB", "type": "Capital", "desc": "SPAC Arb: Buying below Trust Value (Risk Free Yield)."},
    {"code": "INDEX_EV", "type": "Capital", "desc": "Index Inclusion: Arb on forced buying by index funds."},
    {"code": "RECAP", "type": "Capital", "desc": "Recapitalization: Leverage up to pay special div."},
    
    # Block 4
    {"code": "CH11", "type": "Distress", "desc": "Chapter 11: Reorg bankruptcy (New Equity valuation)."},
    {"code": "DE_SWAP", "type": "Distress", "desc": "Debt-Equity Swap: Creditors become owners."},
    {"code": "CURE_ARB", "type": "Distress", "desc": "Cure Period: Arb on technical default grace period."},
    
    # Block 5
    {"code": "HOLDCO", "type": "Structural", "desc": "HoldCo Discount: Parent trading < Sum of Parts."},
    {"code": "DUAL_CLASS", "type": "Structural", "desc": "Dual Class: Spread between voting vs non-voting shares."},
    {"code": "DELISTING", "type": "Structural", "desc": "Delisting: Moving off exchange (or Relisting back)."},
    {"code": "ACTIVISM", "type": "Structural", "desc": "Activism: Investor forcing management change."},
    {"code": "DEMUTUAL", "type": "Structural", "desc": "Demutualization: Customer owned -> Shareholder owned."},
    {"code": "CEF_ARB", "type": "Structural", "desc": "CEF Arb: Closed End Fund trading at discount to NAV."},
    
    # Block 6
    {"code": "REFLEX", "type": "Macro", "desc": "Reflexivity: Price affecting fundamentals (Soros)."},
    {"code": "MACRO_ARB", "type": "Macro", "desc": "Macro/FX Arb: Mispricing in currency/rates."},
    {"code": "DARK_POOL", "type": "Macro", "desc": "Block Trade: Large liquidity discount absorption."},
    {"code": "REV_SPLIT", "type": "Macro", "desc": "Reverse Split: Artificial price increase (Short watch)."},
    
    # Status Colors
    {"code": "STATUS_YELLOW", "type": "Color Code", "desc": "Pipeline: Idea en seguimiento, sin posición abierta."},
    {"code": "STATUS_GREEN", "type": "Color Code", "desc": "Active: Posición abierta y activa."},
    {"code": "STATUS_RED", "type": "Color Code", "desc": "Cancelled: Idea descartada, anulada o fallida."},
    {"code": "STATUS_GRAY", "type": "Color Code", "desc": "Closed: Operación finalizada."}
]

# AddCodeDialog Removed

class NomenclaturaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Codigos") 
        self.resize(600, 600)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']};")
        self.setWindowFlags(Qt.WindowType.Window) 
        
        layout = QVBoxLayout(self)
        
        # Header (Simple Title, No Buttons)
        h_layout = QHBoxLayout()
        lbl_title = QLabel("Nomenclatura Reportes")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['primary']};")
        h_layout.addWidget(lbl_title)
        
        h_layout.addStretch()
        
        # Add Button Removed
        
        layout.addLayout(h_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Code", "Type", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) 
        self.table.setStyleSheet(f"gridline-color: {COLORS['border']}; selection-background-color: {COLORS['primary']}; selection-color: black;")
        
        # POlicy Removed
        
        layout.addWidget(self.table)
        
        self.refresh_table()
        
    def refresh_table(self):
        self.table.setRowCount(0)
        
        rows = []
        # Load from SNE_PERIODS
        for code, desc in SNE_PERIODS.items():
            rows.append((code, "Period", desc))
            
        # Load from SNE_TYPES
        for code, desc in SNE_TYPES.items():
            rows.append((code, "Document Type", desc))
            
        # Load from SPECIAL_SITUATIONS_GLOSSARY
        for item in SPECIAL_SITUATIONS_GLOSSARY:
            rows.append((item['code'], f"Special Situations ({item['type']})", item['desc']))
            
        rows.sort(key=lambda x: (x[1], x[0])) 
        
        self.table.setRowCount(len(rows))
        for i, (code, func, desc) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(code))
            self.table.setItem(i, 1, QTableWidgetItem(func))
            self.table.setItem(i, 2, QTableWidgetItem(desc))
            
    # Add/Edit/Delete Logic Removed

class ColorCodesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Colour Codes")
        self.resize(500, 400)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']};")
        self.setWindowFlags(Qt.WindowType.Window) 
        
        layout = QVBoxLayout(self)
        
        # Grid for colors
        grid = QGridLayout()
        grid.setSpacing(15)
        
        codes = [
            ("#FFF176", "NEUTRAL", "Información general, contexto."), 
            ("#81C784", "RELEVANTE POTENCIAL POSITIVO", "Datos que soportan la tesis alcista."), 
            ("#E57373", "RELEVANTE POTENCIAL NEGATIVO", "Riesgos, datos que debilitan la tesis."), 
            ("#BA68C8", "EXTREMADAMENTE RELEVANTE CRUCIAL", "Factores decisivos para la inversión."), 
            ("#64B5F6", "OJO!!! PROFUNDIZAR", "Temas que requieren más investigación.") 
        ]
        
        for i, (col, title, desc) in enumerate(codes):
            # Color Box
            box = QFrame()
            box.setFixedSize(50, 50)
            box.setStyleSheet(f"background-color: {col}; border: 1px solid {COLORS['border']}; border-radius: 8px;")
            
            # Text
            lbl_title = QLabel(title)
            lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")
            
            lbl_desc = QLabel(desc)
            lbl_desc.setStyleSheet(f"color: {COLORS['text_dim']}; font-style: italic;")
            
            grid.addWidget(box, i, 0)
            grid.addWidget(lbl_title, i, 1)
            grid.addWidget(lbl_desc, i, 2)
            
        layout.addLayout(grid)
        layout.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close) 
        layout.addWidget(btn_close)

class BadgesLegendDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Badges Legend") 
        self.resize(500, 400)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']};")
        
        layout = QVBoxLayout(self)
        
        lbl_title = QLabel("BADGES (QUALITY GATES)")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['primary']};")
        layout.addWidget(lbl_title)
        
        html_text = """
        <ul>
            <li>🏛️ <b>The Historian:</b> Tienes al menos 5 Reportes Anuales y 5 Transcripts en la carpeta.</li>
            <li>👓 <b>The Reader:</b> Has leído (>80%) de esa base histórica.</li>
            <li>Σ <b>The Valuator:</b> Existe un modelo de valoración (Excel) en la carpeta.</li>
            <li>⚖️ <b>The Skeptic:</b> Has subido documentos de 'Proxy' (Incentivos) o Research Externo.</li>
            <li>🗡️ <b>The Thesis:</b> Has redactado la nota de conclusión final.</li>
        </ul>
        """
        lbl_content = QLabel(html_text)
        lbl_content.setWordWrap(True)
        lbl_content.setTextFormat(Qt.TextFormat.RichText)
        lbl_content.setStyleSheet(f"font-size: 14px; line-height: 1.5;")
        layout.addWidget(lbl_content)
        
        layout.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

class ProgressLogicDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Progress Logic") 
        self.resize(500, 400)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']};")
        
        layout = QVBoxLayout(self)
        
        lbl_title = QLabel("PROGRESS BAR LOGIC")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['primary']};")
        layout.addWidget(lbl_title)
        
        html_text = """
        <ul>
            <li><b>Distribución:</b> 15% Archivos + 35% Lectura + 30% Tiempo (Meta: 30h) + 20% Entregables.</li>
            <li><b>Pesos de Lectura:</b>
                <ul>
                    <li><i>High Impact (10pts):</i> Annual Reports (10-K), Proxy, Prospectus.</li>
                    <li><i>Mid Impact (5pts):</i> Transcripts, Quarterly Reports.</li>
                    <li><i>Low Impact (2pts):</i> Presentaciones, Noticias.</li>
                </ul>
            </li>
            <li><i>Nota:</i> La barra penaliza si falta profundidad histórica (menos de 5 años).</li>
        </ul>
        """
        lbl_content = QLabel(html_text)
        lbl_content.setWordWrap(True)
        lbl_content.setTextFormat(Qt.TextFormat.RichText)
        lbl_content.setStyleSheet(f"font-size: 14px; line-height: 1.5;")
        layout.addWidget(lbl_content)
        
        layout.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

class SpecialCalculationsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Special Situations Formulas") 
        self.resize(600, 500)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']};")
        
        layout = QVBoxLayout(self)
        
        lbl_title = QLabel("CALCULATIONS GLOSSARY")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['primary']};")
        layout.addWidget(lbl_title)
        
        html_text = """
        <h3>ARBITRAJE RIGHTS OFFERING (DERECHOS)</h3>
        <ul>
            <li><b>Synthetic Cost:</b> Price Rights + Strike Price.</li>
            <li><b>Arbitrage Spread:</b> Share Price - Synthetic Cost. (Positive = Profit).</li>
            <li><b>Theoretical Ex-Rights Price (TERP):</b> (MarketCap + CapitalRaised) / TotalSharesNew.</li>
        </ul>
        <h3>ARBITRAJE M&A</h3>
        <ul>
            <li><b>Gross Spread:</b> (Offer Price - Current Price) / Current Price.</li>
            <li><b>Annualized Return (IRR):</b> (1 + Spread)^(365/Days to Close) - 1.</li>
        </ul>
        <h3>SPIN-OFFS</h3>
        <ul>
            <li><b>SOTP (Sum of Parts):</b> Valuation of Parent + Valuation of SpinCo > Current Market Cap.</li>
        </ul>
        <h3>LIQUIDATIONS</h3>
        <ul>
            <li><b>Net Liquidation Value:</b> (Assets - Liabilities - Burn Rate*Months) / Shares.</li>
        </ul>
        """
        lbl_content = QLabel(html_text)
        lbl_content.setWordWrap(True)
        lbl_content.setTextFormat(Qt.TextFormat.RichText)
        lbl_content.setStyleSheet(f"font-size: 14px; line-height: 1.5;")
        layout.addWidget(lbl_content)
        
        layout.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)


class SpecialProgressLogicDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Special Situations Progress") 
        self.resize(500, 400)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']};")
        
        layout = QVBoxLayout(self)
        
        lbl_title = QLabel("SPECIAL PROGRESS LOGIC")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['primary']};")
        layout.addWidget(lbl_title)
        
        html_text = """
        <ul>
            <li><b>Lógica General:</b> Barra de progreso basada en actividad y completitud.</li>
            <li><b>Pesos (Weighting):</b>
                <ul>
                    <li><i>Tiempo (30%):</i> Basado en horas registradas (Meta: 10 horas = 100% de este bloque).</li>
                    <li><i>Archivos (30%):</i> Se valora que existan archivos en la carpeta de la situación.</li>
                    <li><i>Hitos (20%):</i> Se valora que se hayan definido hitos en el Timeline.</li>
                    <li><i>Notas (20%):</i> Se valora que existan notas o datos específicos rellenados.</li>
                </ul>
            </li>
        </ul>
        """
        lbl_content = QLabel(html_text)
        lbl_content.setWordWrap(True)
        lbl_content.setTextFormat(Qt.TextFormat.RichText)
        lbl_content.setStyleSheet(f"font-size: 14px; line-height: 1.5;")
        layout.addWidget(lbl_content)
        
        layout.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)


class OptionsBasicsDialog(QDialog):
    """Pizarrón de opciones — apunte de referencia personal."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Options Basics — Se Autosuficiente")
        self.resize(620, 580)
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']};")
        self.setWindowFlags(Qt.WindowType.Window)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 20)
        layout.setSpacing(15)

        # ── Title ──────────────────────────────────────────────────────
        lbl_title = QLabel("Se Autosuficiente — Opciones")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: #9B59B6; "
            f"border-bottom: 2px solid {COLORS['border']}; padding-bottom: 8px;"
        )
        layout.addWidget(lbl_title)

        # ── Grid table (Call / Put × Buy / Sell) ───────────────────────
        table = QTableWidget(2, 2)
        table.setHorizontalHeaderLabels(["⬆ CALL", "⬇ PUT"])
        table.setVerticalHeaderLabels(["BUY", "SELL"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setFixedHeight(190)
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
                font-size: 14px;
            }}
            QHeaderView::section {{
                background-color: {COLORS['surface_light']};
                font-weight: bold;
                font-size: 14px;
                padding: 6px;
                border: 1px solid {COLORS['border']};
            }}
        """)

        cells = [
            (0, 0, "Derecho Comprar\nPaga prima",   "#27ae60"),
            (0, 1, "Derecho Vender\nPaga prima",    "#e74c3c"),
            (1, 0, "Obligación Sell\nRecibe prima",  "#2980b9"),
            (1, 1, "Obligación Buy\nRecibe prima",   "#2980b9"),
        ]
        for r, c, txt, col in cells:
            item = QTableWidgetItem(txt)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor(col))
            item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            table.setItem(r, c, item)
        layout.addWidget(table)

        # ── 6 Factores que afectan al precio ───────────────────────────
        lbl_factors = QLabel("Factores que afectan al precio de la opción:")
        lbl_factors.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['primary']}; margin-top: 10px;")
        layout.addWidget(lbl_factors)

        factors_html = """
        <table width='100%' cellspacing='8'>
          <tr>
            <td width='50%' style='font-size:14px;'>
              <span style='color:#27ae60; font-weight:bold;'>1.</span> Valor del Subyacente &amp; Plazo Vencimiento
            </td>
            <td width='50%' style='font-size:14px;'>
              <span style='color:#9B59B6; font-weight:bold;'>4.</span> <span style='color:#9B59B6;'>Volatilidad</span>
            </td>
          </tr>
          <tr>
            <td style='font-size:14px;'>
              <span style='color:#27ae60; font-weight:bold;'>3.</span> Strike
            </td>
            <td style='font-size:14px;'>
              <span style='color:#9B59B6; font-weight:bold;'>5.</span> <span style='color:#9B59B6;'>Tipos de Interés</span>
            </td>
          </tr>
          <tr>
            <td></td>
            <td style='font-size:14px;'>
              <span style='color:#9B59B6; font-weight:bold;'>6.</span> <span style='color:#9B59B6;'>Dividendos</span>
            </td>
          </tr>
        </table>
        """
        lbl_fac = QLabel(factors_html)
        lbl_fac.setTextFormat(Qt.TextFormat.RichText)
        lbl_fac.setWordWrap(True)
        lbl_fac.setStyleSheet(f"background-color: {COLORS['surface_light']}; border-radius: 8px; padding: 12px;")
        layout.addWidget(lbl_fac)

        # ── Quick note ─────────────────────────────────────────────────
        note_html = """
        <p style='font-size:12px; color:#888; margin-top:8px;'>
          <b>Buy Call</b> → apostar a subida. &nbsp;
          <b>Buy Put</b> → apostar a bajada. &nbsp;
          <b>Sell = obligación</b>, exposición ilimitada en Call.
        </p>
        """
        lbl_note = QLabel(note_html)
        lbl_note.setTextFormat(Qt.TextFormat.RichText)
        lbl_note.setWordWrap(True)
        layout.addWidget(lbl_note)

        layout.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)


class CodigosWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text_main']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("CÓDIGOS") 
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['primary']}; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Main Grid for Cards
        grid = QGridLayout()
        grid.setSpacing(20)
        
        # 1. Nomenclatura Button
        btn_nom = self.create_card("NOMENCLATURA\nREPORTES", "Lista de siglas (FY, Q1...)", self.show_nomenclatura)
        grid.addWidget(btn_nom, 0, 0)
        
        # 2. PDF Colour Button
        btn_col = self.create_card("PDF COLOUR\nSYSTEM", "Guía de colores para subrayado", self.show_colors)
        grid.addWidget(btn_col, 0, 1)
        
        # 3. Badges Legend
        btn_badges = self.create_card("BADGES\nLEGEND", "Explicación de logros", self.show_badges_legend)
        grid.addWidget(btn_badges, 1, 0)
        
        # 4. Progress Logic
        btn_prog = self.create_card("PROGRESS\nLOGIC", "Cálculo de barra de progreso", self.show_progress_logic)
        grid.addWidget(btn_prog, 1, 1)

        # 5. Special Formulas
        btn_spec = self.create_card("SPECIAL\nFORMULAS", "Glosario de cálculos (IRR, Spread...)", self.show_special_formulas)
        grid.addWidget(btn_spec, 2, 0)
        
        # 6. Special Progress
        btn_prog_spec = self.create_card("SPECIAL\nPROGRESS", "Lógica de barra de progreso", self.show_special_progress)
        grid.addWidget(btn_prog_spec, 2, 1)
        
        # 7. Options Basics (photo note — spans 2 columns)
        btn_opts = self.create_wide_card(
            "📋  OPTIONS BASICS",
            "Apunte: Call/Put · Buy/Sell · 6 factores de precio",
            self.show_options_basics
        )
        grid.addWidget(btn_opts, 3, 0, 1, 2)  # span 2 columns
        
        layout.addLayout(grid)
        layout.addStretch()
        
        # Holds references to keep windows alive
        self.nomenclatura_dialog  = None
        self.colors_dialog        = None
        self.badges_dialog        = None
        self.progress_dialog      = None
        self.special_dialog       = None
        self.special_prog_dialog  = None
        self.options_dialog       = None

    def create_card(self, title, subtitle, click_handler):
        btn = QPushButton()
        btn.setFixedSize(250, 150)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 2px solid {COLORS['primary']};
                border-radius: 15px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary']};
            }}
        """)
        btn.clicked.connect(click_handler)
        
        layout = QVBoxLayout(btn)
        lbl_t = QLabel(title)
        lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_t.setStyleSheet("font-size: 18px; font-weight: bold; color: #E0E0E0; background: transparent;")
        
        lbl_s = QLabel(subtitle)
        lbl_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_s.setStyleSheet("font-size: 12px; color: #B0B0B0; background: transparent;")
        
        layout.addWidget(lbl_t)
        layout.addWidget(lbl_s)
        
        return btn

    def create_wide_card(self, title, subtitle, click_handler):
        """Full-width (2-column) card variant."""
        btn = QPushButton()
        btn.setFixedHeight(90)
        btn.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface_light']};
                border: 2px solid #9B59B6;
                border-radius: 15px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: #9B59B6;
            }}
        """)
        btn.clicked.connect(click_handler)

        layout = QVBoxLayout(btn)
        lbl_t = QLabel(title)
        lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_t.setStyleSheet("font-size: 16px; font-weight: bold; color: #E0E0E0; background: transparent;")

        lbl_s = QLabel(subtitle)
        lbl_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_s.setStyleSheet("font-size: 11px; color: #B0B0B0; background: transparent;")

        layout.addWidget(lbl_t)
        layout.addWidget(lbl_s)
        return btn

    def show_nomenclatura(self):
        if self.nomenclatura_dialog is None:
            self.nomenclatura_dialog = NomenclaturaDialog(self)
        self.nomenclatura_dialog.show()
        self.nomenclatura_dialog.raise_()
        self.nomenclatura_dialog.activateWindow()

    def show_colors(self):
        if self.colors_dialog is None:
            self.colors_dialog = ColorCodesDialog(self)
        self.colors_dialog.show()
        self.colors_dialog.raise_()
        self.colors_dialog.activateWindow()
        
    def show_badges_legend(self):
        if self.badges_dialog is None:
            self.badges_dialog = BadgesLegendDialog(self)
        self.badges_dialog.show()
        self.badges_dialog.raise_()
        self.badges_dialog.activateWindow()
        
    def show_progress_logic(self):
        if self.progress_dialog is None:
            self.progress_dialog = ProgressLogicDialog(self)
        self.progress_dialog.show()
        self.progress_dialog.raise_()
        self.progress_dialog.activateWindow()

    def show_special_formulas(self):
        if self.special_dialog is None:
            self.special_dialog = SpecialCalculationsDialog(self)
        self.special_dialog.show()
        self.special_dialog.raise_()
        self.special_dialog.show()
        self.special_dialog.raise_()
        self.special_dialog.activateWindow()

    def show_special_progress(self):
        if self.special_prog_dialog is None:
            self.special_prog_dialog = SpecialProgressLogicDialog(self)
        self.special_prog_dialog.show()
        self.special_prog_dialog.raise_()
        self.special_prog_dialog.activateWindow()

    def show_options_basics(self):
        if self.options_dialog is None:
            self.options_dialog = OptionsBasicsDialog(self)
        self.options_dialog.show()
        self.options_dialog.raise_()
        self.options_dialog.activateWindow()

    # --- Documentation (Legend) ---
        legend_label = QLabel("LEGEND & METHODOLOGY")
        legend_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['text_main']}; margin-top: 30px;")
        
        legend_text = """
        <h3>A. LEYENDA DE BADGES (QUALITY GATES)</h3>
        <ul>
            <li>🏛️ <b>The Historian:</b> Tienes al menos 5 Reportes Anuales y 5 Transcripts en la carpeta.</li>
            <li>👓 <b>The Reader:</b> Has leído (>80%) de esa base histórica.</li>
            <li>Σ <b>The Valuator:</b> Existe un modelo de valoración (Excel) en la carpeta.</li>
            <li>⚖️ <b>The Skeptic:</b> Has subido documentos de 'Proxy' (Incentivos) o Research Externo.</li>
            <li>🗡️ <b>The Thesis:</b> Has redactado la nota de conclusión final.</li>
        </ul>
        <h3>B. LÓGICA DE LA BARRA DE PROGRESO</h3>
        <ul>
            <li><b>Distribución:</b> 15% Archivos + 35% Lectura + 30% Tiempo (Meta: 30h) + 20% Entregables.</li>
            <li><b>Pesos de Lectura:</b>
                <ul>
                    <li><i>High Impact (10pts):</i> Annual Reports (10-K), Proxy, Prospectus.</li>
                    <li><i>Mid Impact (5pts):</i> Transcripts, Quarterly Reports.</li>
                    <li><i>Low Impact (2pts):</i> Presentaciones, Noticias.</li>
                </ul>
            </li>
            <li><i>Nota:</i> La barra penaliza si falta profundidad histórica (menos de 5 años).</li>
        </ul>
        """
        
        lbl_doc = QLabel(legend_text)
        lbl_doc.setStyleSheet(f"color: {COLORS['text_main']}; font-size: 13px; line-height: 1.4;")
        lbl_doc.setWordWrap(True)
        lbl_doc.setTextFormat(Qt.TextFormat.RichText)
        
        # Add to layout (need to access layout from init, this snippet is misplaced inside show_colors, moving logic to init)

