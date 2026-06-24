"""
config.py — Ekomonos Configuration
====================================
SINGLE SOURCE OF TRUTH for all paths and application settings.

Rules:
  - ALL file paths in the entire project must come from here.
  - NO hardcoded paths anywhere else.
  - Paths are always relative to this file's location (ROOT),
    so the project works on any machine without modification.
"""

from pathlib import Path

# ─── Root ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()

# ─── Library (Filesystem) ────────────────────────────────────────────────────
LIBRARY_ROOT   = Path(r"D:\00_EKOSISTEMA_OS\03_DINERO\03.01_Inversion\03.01_Ekomonos_Library")
STOCK_PATH     = LIBRARY_ROOT / "STOCK"
SPECIAL_PATH   = LIBRARY_ROOT / "SPECIAL"
POMODORO_LOG   = LIBRARY_ROOT / "pomodoro_log.csv"
LIBRARY_DB     = LIBRARY_ROOT / "library.db"

# ─── Databases ───────────────────────────────────────────────────────────────
DB_FOLDER      = ROOT.parent / "db"
MAIN_DB        = DB_FOLDER / "fortress_vault.db"       # SQLAlchemy (primary)
SPECIAL_DB     = DB_FOLDER / "special_situations.db"   # Legacy (to be merged)

# ─── Assets ──────────────────────────────────────────────────────────────────
ASSETS_PATH    = ROOT / "assets"
SPLASH_IMAGE   = ASSETS_PATH / "splash_image.png"
DESKTOP_ICON   = ASSETS_PATH / "desktop_icon.ico"

# ─── Data ────────────────────────────────────────────────────────────────────
DATA_PATH      = ROOT / "data"
UI_STATE_PATH  = DATA_PATH / "ui_state.json"
PROMPTS_PATH   = DATA_PATH / "prompts.json"
CODES_PATH     = DATA_PATH / "codes.json"

# ─── Application ─────────────────────────────────────────────────────────────
APP_NAME       = "Ekomonos"
DEBUG_MODE     = False   # Set to True only for development. Controls debug logging.

# ─── Integration Apps ────────────────────────────────────────────────────────
TIKR_HARVEST_PATH = ROOT.parent / "tikr-harvest"
TIKR_PORT      = 3000

# ─── Helpers ─────────────────────────────────────────────────────────────────
def ensure_dirs():
    """Create all required directories if they don't exist."""
    for d in [LIBRARY_ROOT, STOCK_PATH, SPECIAL_PATH, DB_FOLDER, DATA_PATH]:
        d.mkdir(parents=True, exist_ok=True)
