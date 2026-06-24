from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog
from PyQt6.QtCore import Qt, QUrl, QProcess
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
import os
import time
from config import TIKR_HARVEST_PATH, TIKR_PORT

class TikrHarvestWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # UI: Browser View
        # UI: Browser View
        self.browser = QWebEngineView()
        self.browser.page().profile().downloadRequested.connect(self._on_download_requested)
        self.layout.addWidget(self.browser)
        
        # State
        self.server_process = None
        self.is_running = False
        
        # Start server
        self.start_node_server()

    def _log(self, level, message):
        try:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "node_output.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{level}] {message}\n")
        except Exception as e:
            print(f"Error writing to node_output.log: {e}")

    def _kill_port_owner(self, port):
        import subprocess
        try:
            self._log("INFO", f"Checking if port {port} is occupied...")
            # Run netstat to find the PID of the process listening on the port
            output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode('utf-8', errors='ignore')
            pids = set()
            for line in output.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 5 and 'LISTENING' in line:
                    pid = parts[-1].strip()
                    if pid.isdigit():
                        pids.add(int(pid))
            
            for pid in pids:
                self._log("INFO", f"Killing process {pid} occupying port {port}...")
                # Kill the process
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self._log("WARNING", f"Error check/killing port owner: {e}")

    def start_node_server(self):
        """Starts the TIKR Harvest Node.js backend using QProcess."""
        self._log("INFO", "start_node_server() called.")
        
        # Free port 3000 if it is occupied to prevent crash
        self._kill_port_owner(TIKR_PORT)
        
        if not os.path.exists(TIKR_HARVEST_PATH):
            self._log("ERROR", f"Path not found: {TIKR_HARVEST_PATH}")
            self._show_error(f"Cannot find TIKR Harvest directory at {TIKR_HARVEST_PATH}")
            return
            
        server_script = os.path.join(TIKR_HARVEST_PATH, "dist", "server.cjs")
        if not os.path.exists(server_script):
             self._log("ERROR", f"Server script not found: {server_script}")
             self._show_error(f"Cannot find compiled server at {server_script}. Make sure you built it.")
             return
             
        self.server_process = QProcess(self)
        self.server_process.setWorkingDirectory(str(TIKR_HARVEST_PATH))
        
        # Connect signals
        self.server_process.readyReadStandardOutput.connect(self._handle_stdout)
        self.server_process.readyReadStandardError.connect(self._handle_stderr)
        self.server_process.errorOccurred.connect(self._handle_error)
        self.server_process.started.connect(self._on_server_started)
        
        # Start node
        self._log("INFO", f"Starting Node process in directory: {TIKR_HARVEST_PATH} with script: dist/server.cjs")
        # Make sure node is in PATH
        self.server_process.start("node", ["dist/server.cjs"])

    def _show_error(self, msg):
        self.browser.setHtml(f"<html><body style='background:#121212;color:red;display:flex;justify-content:center;align-items:center;height:100vh;'><h2>{msg}</h2></body></html>")

    def _on_server_started(self):
        self._log("INFO", f"Node process started successfully on port {TIKR_PORT}")
        self.is_running = True
        # Give it a short delay to spin up the express server
        import PyQt6.QtCore as QtCore
        QtCore.QTimer.singleShot(1500, self._load_url)

    def _load_url(self):
        url = QUrl(f"http://localhost:{TIKR_PORT}")
        self._log("INFO", f"Loading UI: {url.toString()}")
        self.browser.setUrl(url)

    def _on_download_requested(self, download: QWebEngineDownloadRequest):
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", download.downloadFileName())
        path, _ = QFileDialog.getSaveFileName(self, "Save File", default_path)
        if path:
            download.setDownloadDirectory(os.path.dirname(path))
            download.setDownloadFileName(os.path.basename(path))
            download.accept()
            self._log("INFO", f"Downloading to: {path}")

    def _handle_stdout(self):
        if self.server_process:
            data = self.server_process.readAllStandardOutput().data().decode('utf-8', errors='replace').strip()
            if data:
                self._log("NODE_STDOUT", data)
                # Parse action triggers from Node stdout
                for line in data.splitlines():
                    line = line.strip()
                    if line.startswith("ACTION_TRIGGER:CREATE_COMPANY:"):
                        parts = line.split(":", 3)
                        ticker = parts[2].strip() if len(parts) > 2 else ""
                        name = parts[3].strip() if len(parts) > 3 else ""
                        if ticker:
                            self._log("INFO", f"Intercepted CREATE_COMPANY request for {ticker} ({name})")
                            from ui.app_state import AppState
                            AppState.get().request_create_company.emit(ticker, name)
                    elif line.startswith("ACTION_TRIGGER:DOWNLOAD_FINISHED:"):
                        parts = line.split(":", 2)
                        ticker = parts[2].strip() if len(parts) > 2 else ""
                        self._log("INFO", f"Intercepted DOWNLOAD_FINISHED for {ticker}")
                        from ui.app_state import AppState
                        AppState.get().notify_library_synced()

    def _handle_stderr(self):
        if self.server_process:
            data = self.server_process.readAllStandardError().data().decode('utf-8', errors='replace').strip()
            if data:
                self._log("NODE_STDERR", data)
                
    def _handle_error(self, error):
        self._log("PROCESS_ERROR", f"QProcess error occurred: {error}")
        self._show_error(f"Failed to start Node process. Is NodeJS installed and in PATH?<br>{error}")

    def closeEvent(self, event):
        """Ensure the node process is terminated when the widget is destroyed."""
        self._cleanup()
        super().closeEvent(event)
        
    def _cleanup(self):
        if self.server_process and self.server_process.state() != QProcess.ProcessState.NotRunning:
            self._log("INFO", "Terminating Node server...")
            self.server_process.terminate()
            if not self.server_process.waitForFinished(2000):
                self._log("INFO", "Node server did not exit in time. Killing it...")
                self.server_process.kill()
        self.is_running = False

    def __del__(self):
        self._cleanup()
