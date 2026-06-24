import os
import re
import json

# Define Data Path
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CODES_FILE = os.path.join(DATA_DIR, "codes.json")

# Defaults
# Defaults
DEFAULT_SNE_TYPES = {
    # Core Financials
    'REP': 'Reporte Principal (10-K, 10-Q, Annual, Interim)',
    'MDA': 'Management Discussion & Analysis (Si va separado)',
    'AIF': 'Annual Info Form (Canada/Regulatory)',
    
    # Management & Governance (CRITICAL FOR VALUE INVESTING)
    'PROXY': 'Proxy Statement / DEF 14A (Incentivos y Directiva)', 
    'LET': 'Letter to Shareholders (Carta del CEO)',

    # Events & Updates
    'TRANS': 'Transcript (Conference Call Q&A)',
    'PRES': 'Investor Presentation (Slides)',
    'PR': 'Press Release (Earnings/News)',
    'EVT': 'Evento Relevante (8-K, M&A, Material Change)',

    # Foundation & External
    'PROS': 'Prospectus (S-1, IPO, Spin-off doc)',
    'IPO': 'Initial Public Offering',
    'EXT': 'External Research (Credit Ratings, Short Reports, Competitor Analysis)',

    # User Generated
    'NOT': 'Mis Notas / Journal',
    'EXCEL': 'Modelo de Valoración',
    'THESIS': 'Investment Thesis (Nota Final)'
}

DEFAULT_SNE_PERIODS = {
    'FY': 'Fiscal Year (Anual)',
    'Q1': 'Overview Q1',
    'Q2': 'Overview Q2', 
    'Q3': 'Overview Q3',
    'Q4': 'Overview Q4',
    'HY': 'Half-Year (Semestral)',
    'NA': 'No Aplica'
}

def load_codes():
    if os.path.exists(CODES_FILE):
        try:
            with open(CODES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Merge with defaults to ensure new types appear
                loaded_types = data.get("types", {})
                loaded_periods = data.get("periods", {})
                
                # Merge Defaults (Priority to loaded, but add missing defaults)
                final_types = DEFAULT_SNE_TYPES.copy()
                final_types.update(loaded_types) # Overwrite defaults with loaded custom
                # actually, we want to ensure *new* defaults exist. 
                # If user deleted one, it reappears. 
                # Better: Update loaded with defaults if missing?
                # User wants "TESIS" to appear.
                for k, v in DEFAULT_SNE_TYPES.items():
                    if k not in loaded_types:
                        loaded_types[k] = v
                
                for k, v in DEFAULT_SNE_PERIODS.items():
                    if k not in loaded_periods:
                        loaded_periods[k] = v
                        
                return loaded_types, loaded_periods
        except Exception as e:
            print(f"Error loading codes: {e}")
    return DEFAULT_SNE_TYPES.copy(), DEFAULT_SNE_PERIODS.copy()

def save_codes(types, periods):
    data = {"types": types, "periods": periods}
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        with open(CODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving codes: {e}")

# Load on module init
SNE_TYPES, SNE_PERIODS = load_codes()

def generate_sne_filename(date_str, ticker, period, doc_type, extra_tag="", extension=".pdf"):
    """
    Generates a Standardized Naming (SNE) filename.
    Format: {YYYY-MM-DD}_{TICKER}_{PERIODO}_{TIPO}_{EXTRA}.ext
    
    Args:
        date_str (str): Date in YYYY-MM-DD format.
        ticker (str): Ticker symbol (e.g., 'AAPL', 'CSU.TO').
        period (str): Period code (FY, Q1, Q2, HY, Q3, Q4, NA).
        doc_type (str): Document type code (REP, MDA, PR, PRES, TRANS, EVT, NOT).
        extra_tag (str, optional): Free text for disambiguation (CamelCase).
        extension (str, optional): File extension (default .pdf).
    """
    # 1. Cleaning
    clean_ticker = ticker.strip().upper().replace(" ", "")
    clean_extra = extra_tag.strip().replace(" ", "") # Simple CamelCase simulation by removing spaces
    
    # 2. Validation / defaults
    clean_period = period.upper() if period.upper() in SNE_PERIODS else "NA"
    clean_type = doc_type.upper() if doc_type.upper() in SNE_TYPES else "DOC"
    
    # 3. Construction
    basename = f"{date_str}_{clean_ticker}_{clean_period}_{clean_type}"
    
    if clean_extra:
        basename += f"_{clean_extra}"
        
    if not extension.startswith('.'):
        extension = f".{extension}"
        
    return f"{basename}{extension}"

def get_sne_destination_folder(root_path, ticker, doc_type, year):
    """
    Determines the destination folder structure based on SNE type.
    
    Structure:
    STOCK/<TICKER>/
      1 REPORTS <TICKER>/<YEAR>/
      2 TRANSCRIPTS <TICKER>/<YEAR>/
      3 EXCEL <TICKER>/
      4 VARIOS <TICKER>/<YEAR>/
    """
    clean_ticker = ticker.strip().upper()
    
    # Map SNE Types to Folders
    if doc_type in ["REP", "MDA", "AIF"]:
        subfolder = f"1 REPORTS {clean_ticker}"
        use_year = True
    elif doc_type in ["TRANS"]:
        subfolder = f"2 TRANSCRIPTS {clean_ticker}"
        use_year = True
    elif doc_type == "EXCEL":
        subfolder = f"3 EXCEL {clean_ticker}"
        use_year = False # Excel usually in root of folder 3? Or per year? 
        # User prompt said "solo estara los excel de cada compania", implying root of folder 3
    else:
        # PR, PRES, EVT, NOT, others
        subfolder = f"4 VARIOS {clean_ticker}"
        use_year = True
        
    path = os.path.join(root_path, "STOCK", clean_ticker, subfolder)
    
    if use_year and year:
        path = os.path.join(path, str(year))
        
    return path
