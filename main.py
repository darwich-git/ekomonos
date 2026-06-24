import sys
import os
import traceback
from datetime import datetime

# Ensure src directory is in path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from config import (
    APP_NAME, LIBRARY_ROOT, STOCK_PATH,
    SPLASH_IMAGE, DESKTOP_ICON, ensure_dirs
)

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.styles import STYLESHEET

# Global exception hook to catch silent crashes
def exception_hook(exctype, value, tb):
    print("CRITICAL: Unhandled exception caught:")
    traceback.print_exception(exctype, value, tb)
    
    # Write to a file
    with open("crash_log.txt", "a") as f:
        f.write(f"\n--- Crash at {datetime.now()} ---\n")
        traceback.print_exception(exctype, value, tb, file=f)
        
    sys.exit(1)

sys.excepthook = exception_hook

from PyQt6.QtWidgets import QApplication, QSplashScreen, QProgressBar, QLabel, QVBoxLayout, QWidget, QFrame
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal


from version import APP_NAME, __version__

# Worker Thread for Heavy Initialization
class InitWorker(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal()
    
    def run(self):
        # Step 1: Booting
        self.progress_signal.emit(10, "Booting Ekomonos Engine...")
        QThread.msleep(400)
        
        # Step 2: Database init
        self.progress_signal.emit(30, "Initializing Secure Vault...")
        QThread.msleep(400)
        
        # Step 3: Loading modules
        self.progress_signal.emit(50, "Loading Market Data Modules...")
        QThread.msleep(300)
        
        # Step 4: FETCH REAL PRICES
        self.progress_signal.emit(70, "Fetching Live Prices...")
        try:
            self.fetch_and_save_prices()
        except Exception as e:
            print(f"Error fetching prices during splash: {e}")
            import traceback
            traceback.print_exc()
        
        self.progress_signal.emit(100, "Ready")
        self.finished_signal.emit()
    
    def fetch_and_save_prices(self):
        """Fetch prices and save to database during splash screen."""
        from core.companies_manager import CompaniesManager
        from core.price_fetcher import price_fetcher
        from core.special_manager import SpecialManager

        manager = CompaniesManager(str(LIBRARY_ROOT))
        special_manager = SpecialManager()
        manager.sync_with_library()
        
        # Build fetch list (same logic as companies_view.py)
        all_companies = manager.get_companies()
        fetch_list = []
        seen_tickers = set()
        exclude_tickers = {"CASH", "LTG", "TITC", "EUR"}
        
        for c in all_companies:
            t = c['ticker']
            if t and t not in seen_tickers and t.upper() not in exclude_tickers:
                fetch_list.append({
                    'ticker': t,
                    'primary_exchange': c.get('primary_exchange', ''),
                    'yahoo_ticker': c.get('yahoo_ticker', '')
                })
                seen_tickers.add(t)
        
        # Add special situations tickers
        special_rows = special_manager.get_all_situations()
        for s in special_rows:
            t = s.get('tickers', {}).get('target')
            if t and t not in seen_tickers:
                fetch_list.append({'ticker': t, 'primary_exchange': ''})
                seen_tickers.add(t)
        
        # Fetch prices
        prices = price_fetcher.fetch_prices(fetch_list)
        
        # Save to database
        for tick, p in prices.items():
            manager.update_company(tick, last_price=p)


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) # Removed margins to avoid "double border" look
        
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: #121212;
                border: 1px solid #333; /* Softer border */
                border-radius: 12px;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.setContentsMargins(20, 20, 20, 20)
        
        # Logo
        logo_label = QLabel()
        # Use full path or relative? Ensure consistent path
        pixmap = QPixmap(str(SPLASH_IMAGE))
        
        if not pixmap.isNull():
            # Image scaled to 400px
            logo_label.setPixmap(pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo_label.setText(APP_NAME.upper())
            logo_label.setStyleSheet("font-size: 50px; color: #FF9800; font-weight: bold;")
            
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("border: none; background: transparent;")
        
        # Version Title
        title_label = QLabel(f"Version {__version__}")
        title_label.setStyleSheet("color: #AAA; font-size: 16px; font-weight: bold; border: none; margin-top: 5px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #444;
                border-radius: 2px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #FF9800;
                border-radius: 2px;
            }
        """)
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("color: #888; font-size: 11px; border: none; margin-top: 8px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        container_layout.addWidget(logo_label)
        container_layout.addWidget(title_label)
        container_layout.addSpacing(15)
        container_layout.addWidget(self.progress_bar)
        container_layout.addWidget(self.status_label)
        
        layout.addWidget(self.container)
        
        # Tighter size to match image (400px image + minimal padding)
        self.resize(440, 520) 
        self.center()

        # FORCE STYLE REFRESH (Matched Background)
        self.container.setObjectName("SplashContainer")
        self.container.setStyleSheet("""
            #SplashContainer {
                background-color: #2e2e2c; 
                border: none; 
                border-radius: 12px;
            }
        """)
        
    def center(self):
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def update_progress(self, val, msg):
        self.progress_bar.setValue(val)
        self.status_label.setText(msg)
from PyQt6.QtCore import QObject, QEvent

class WheelEventFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            from PyQt6.QtWidgets import QAbstractSpinBox, QComboBox, QDateEdit, QDateTimeEdit
            if isinstance(obj, (QAbstractSpinBox, QComboBox, QDateEdit, QDateTimeEdit)):
                # Ignore wheel events for inputs globally to prevent accidental changes
                event.ignore()
                return True
        return super().eventFilter(obj, event)

def main():
    ensure_dirs()  # Make sure all required directories exist
    app = QApplication(sys.argv)

    # SECURE GLOBAL EVENTS
    wheel_filter = WheelEventFilter(app)
    app.installEventFilter(wheel_filter)

    
    # SINGLE INSTANCE GUARD
    from PyQt6.QtCore import QSharedMemory
    shared_mem = QSharedMemory("EKKOMONOS_SINGLE_INSTANCE_GUARD")
    if shared_mem.attach():
        print("Application is already running. Exiting local instance.")
        sys.exit(0)
    if not shared_mem.create(1):
        print("Application is already running. Exiting local instance.")
        sys.exit(0)
    
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    
    # Set Window Icon
    try:
        from PyQt6.QtGui import QIcon
        if DESKTOP_ICON.exists():
            app.setWindowIcon(QIcon(str(DESKTOP_ICON)))
    except Exception as e:
        print(f"Failed to set icon: {e}")
    
    # 1. Show Splash
    splash = SplashScreen()
    splash.show()
    
    # 2. Init Worker
    worker = InitWorker()
    
    # 3. Define Finish Handler
    def on_loaded():
        try:
            # Create window but DO NOT show it yet
            window = MainWindow()
            window.setWindowTitle(f"{APP_NAME} {__version__}")
            
            print("[INIT] Creating main window (hidden)...")
            
            # Position window BEFORE showing (no visible movement)
            # Get screen geometry
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                x = screen_geometry.x()
                y = screen_geometry.y()
                width = screen_geometry.width() // 2
                height = screen_geometry.height()
                
                # Set geometry while hidden
                window.setGeometry(x, y, width, height)
                print(f"[INIT] Pre-positioned to left half: x={x}, y={y}, w={width}, h={height}")
            
            # Small delay to ensure positioning is complete
            QTimer.singleShot(50, lambda: finish_loading(window))
            
        except Exception as e:
            print(f"Error creating main window: {e}")
            traceback.print_exc()
            sys.exit(1)
    
    def finish_loading(window):
        """Show window after positioning is complete"""
        print("[INIT] Revealing positioned window...")
        
        # Close splash first
        splash.close()
        
        # Now show window (already positioned)
        window.show()
        window.activateWindow()
        window.raise_()
        
        print("[INIT] Window visible and ready!")
            
    worker.progress_signal.connect(splash.update_progress)
    worker.finished_signal.connect(on_loaded)
    worker.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
