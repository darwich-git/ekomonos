import shutil
import os
import datetime
from PyQt6.QtWidgets import QMessageBox

class BackupManager:
    @staticmethod
    def create_backup(source_dir, backup_root=r"D:\Proyectos\Backups", show_msg=True):
        """
        Creates a zip backup of source_dir into backup_root/Ekkomonos_YYYYMMDD_HHMMSS.zip
        """
        try:
            if not os.path.exists(backup_root):
                os.makedirs(backup_root)
                
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"Ekkomonos_{timestamp}"
            output_path = os.path.join(backup_root, base_name)
            
            # Helper to filter ignored files
            def ignore_func(dir, files):
                ignored = []
                if "tmp" in dir.split(os.sep): ignored.extend(files)
                if ".git" in dir.split(os.sep): ignored.extend(files)
                if ".venv" in dir.split(os.sep): ignored.extend(files)
                if "__pycache__" in dir.split(os.sep): ignored.extend(files)
                
                # Also ignore explicit folders
                return [f for f in files if f in ['.git', '.venv', '__pycache__', 'tmp']]

            # Shutil make_archive does not easily support advanced filtering without copying first,
            # but usually it's fine to just ignore specific patterns. 
            # Ideally we use zipfile for granular control, but shutil is robust.
            # We will use shutil but we can't easily filter deep nested without a custom ignore
            # which shutil.make_archive doesn't support directly like copytree.
            # So, we will use a custom zip approach for safety and cleanliness.
            
            import zipfile
            
            zip_filename = output_path + ".zip"
            
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(source_dir):
                    # Filter dirs to traverse
                    # REMOVED 'data' from ignore list to include DB.
                    # Added 'market_data' or specific heavy folders if needed to be ignored?
                    # For now, we trust the user wants their DB.
                    dirs[:] = [d for d in dirs if d not in ['.git', '.venv', '__pycache__', 'tmp', '.gemini', '.idea', '.vscode', 'Ekomonos Library', 'ui_backup_blue']]
                    
                    for file in files:
                        if file.endswith('.pyc') or file.endswith('.log'): continue
                        
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, arcname)
                        
            if show_msg:
                # Use ctypes for a simple msg box if UI not available, or just print
                # Assuming this is run from UI context usually
                print(f"Backup created at: {zip_filename}")
                
            return zip_filename
            
        except Exception as e:
            print(f"Backup failed: {e}")
            return None
