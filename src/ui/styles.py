# Professional Dark Theme for Ekkomonos
# Inspired by Bloomberg Terminal / High-End Financial Software
import os, subprocess

def open_url_chrome(url):
    """Open a URL in Chrome. Falls back to system default if Chrome not found."""
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if os.path.exists(chrome_path):
        subprocess.Popen([chrome_path, url])
    else:
        import webbrowser
        webbrowser.open(url)

COLORS = {
    "background": "#121212",
    "surface": "#1E1E1E",
    "surface_light": "#2D2D2D",
    "primary": "#FF9800", # Amber/Orange for focus
    "text_main": "#E0E0E0",
    "text_dim": "#A0A0A0",
    "border": "#333333",
    "success": "#2ECC71",
    "danger": "#E74C3C",
    "accent": "#3498DB",
    "warning": "#F1C40F"
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS["background"]};
}}

QWidget {{
    background-color: {COLORS["background"]};
    color: {COLORS["text_main"]};
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 14px;
}}

/* --- Navigation Bar --- */
QListWidget {{
    background-color: {COLORS["surface"]};
    border: none;
    outline: none;
    padding-top: 10px;
}}

QListWidget::item {{
    height: 50px;
    padding-left: 15px;
    color: {COLORS["text_dim"]};
    border-left: 3px solid transparent;
}}

QListWidget::item:hover {{
    background-color: {COLORS["surface_light"]};
    color: {COLORS["text_main"]};
}}

QListWidget::item:selected {{
    background-color: {COLORS["surface_light"]};
    color: {COLORS["primary"]};
    border-left: 3px solid {COLORS["primary"]};
}}

/* --- Content Area --- */
QStackedWidget {{
    background-color: {COLORS["background"]};
}}

QLabel {{
    color: {COLORS["text_main"]};
}}

QPushButton {{
    background-color: {COLORS["surface_light"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 6px 12px;
    color: {COLORS["text_main"]};
}}

QPushButton:hover {{
    background-color: {COLORS["border"]};
    border-color: {COLORS["text_dim"]};
}}

QPushButton:pressed {{
    background-color: {COLORS["primary"]};
    color: #000000;
}}

QLineEdit, QTextEdit {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px;
    color: {COLORS["text_main"]};
    selection-background-color: {COLORS["primary"]};
    selection-color: #000000;
}}

/* --- Scrollbars --- */
QScrollBar:vertical {{
    border: none;
    background: {COLORS["background"]};
    width: 10px;
    margin: 0px 0px 0px 0px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS["surface_light"]};
    min-height: 20px;
    border-radius: 5px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}

/* --- Global SpinBox No-Arrows --- */
QSpinBox::up-button, QSpinBox::down-button, 
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0px;
    height: 0px;
    border: none;
    background: transparent;
}}
"""
