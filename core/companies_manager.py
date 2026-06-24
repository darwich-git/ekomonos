
import sqlite3
import os
import requests
from datetime import datetime

from config import LIBRARY_ROOT as _DEFAULT_LIBRARY_ROOT, MAIN_DB
from core.library_manager import LibraryManager

class CompaniesManager:
    def __init__(self, root_path):
        self.root_path = root_path
        self.db_path = str(MAIN_DB) # Apunta ahora directamente a fortress_vault.db

        
        # Ensure DB schema is complete (Context: LibraryManager creates 'files' table)
        LibraryManager(root_path) 
        
        self._init_db()

    def _init_db(self):
        """Initialize the companies table in library.db."""
        if not os.path.exists(self.db_path):
            return 

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check specific table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE companies (
                    ticker TEXT PRIMARY KEY,
                    name TEXT,
                    category TEXT DEFAULT 'Watchlist', -- Portfolio, Watchlist, Special
                    currency TEXT DEFAULT 'USD',
                    shares_count INTEGER DEFAULT 0,
                    cost_basis REAL DEFAULT 0.0, -- Total Money In
                    fair_value REAL DEFAULT 0.0,
                    potential_5y REAL DEFAULT 0.0,
                    last_price REAL DEFAULT 0.0,
                    last_update TEXT,
                    metric_type TEXT, -- PER, FCF, EBITDA
                    next_presentation TEXT,
                    notes TEXT,
                    primary_exchange TEXT,
                    yahoo_ticker TEXT,
                    aliases TEXT, -- Comma separated aliases (e.g. VBNK.TO, VBNK.NE)
                    status TEXT DEFAULT 'To Research'
                )
            ''')
        else:
            # Check for missing columns (migration)
            cursor.execute("PRAGMA table_info(companies)")
            cols = [info[1] for info in cursor.fetchall()]
            
            new_cols = {
                'category': "TEXT DEFAULT 'Watchlist'",
                'currency': "TEXT DEFAULT 'USD'",
                'shares_count': "INTEGER DEFAULT 0",
                'cost_basis': "REAL DEFAULT 0.0",
                'fair_value': "REAL DEFAULT 0.0",
                'potential_5y': "REAL DEFAULT 0.0",
                'last_price': "REAL DEFAULT 0.0",
                'last_update': "TEXT",
                'metric_type': "TEXT",
                'next_presentation': "TEXT",
                'notes': "TEXT",
                # 'primary_exchange' appeared twice in original code, fixed
                'primary_exchange': "TEXT", 
                'yahoo_ticker': "TEXT",
                'aliases': "TEXT",
                'status': "TEXT DEFAULT 'To Research'" # To Research, In Progress, Done
            }
            
            for col, defi in new_cols.items():
                if col not in cols:
                    try:
                        print(f"Migrating: Adding column '{col}' to companies table...")
                        cursor.execute(f"ALTER TABLE companies ADD COLUMN {col} {defi}")
                        conn.commit() # Commit after each success
                    except Exception as e:
                        print(f"Migration error ({col}): {e}")
                        # Don't re-raise, try next column

        conn.commit()
        conn.close()

    def sync_with_library(self):
        """Syncs tickers from files table AND folders to companies table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Get tickers from FILES table
        cursor.execute("SELECT DISTINCT ticker FROM files")
        file_tickers = [row[0] for row in cursor.fetchall() if row[0]]
        
        # 2. Get tickers from FOLDERS
        folder_tickers = []
        stock_path = os.path.join(self.root_path, "STOCK")
        if os.path.exists(stock_path):
            folder_tickers = [d for d in os.listdir(stock_path) if os.path.isdir(os.path.join(stock_path, d))]
            
        all_tickers = set(file_tickers + folder_tickers)
        
        # Get existing companies in DB
        cursor.execute("SELECT ticker FROM companies")
        existing_tickers = {row[0] for row in cursor.fetchall()}
        
        # Add missing
        added_count = 0
        for t in all_tickers:
            if t not in existing_tickers:
                # fortress_vault.db requires 'name' and 'status' to be NOT NULL
                cursor.execute("INSERT INTO companies (ticker, name, category, status) VALUES (?, ?, ?, ?)", (t, '', "Watchlist", "To Research"))
                added_count += 1
        
        # Recalculate Last Update for ALL companies
        # This ensures the UI is up to date with file system changes
        cursor.execute("SELECT ticker, category FROM companies")
        all_db_rows = cursor.fetchall()
        
        cleaned_count = 0
        for row in all_db_rows:
            t = row[0]
            cat = row[1]
            
            # PRUNING LOGIC:
            # If it is Watchlist or Portfolio, it MUST have a folder in STOCK/
            # Special situations are different (handled by SpecialManager/table), but if they are in 'companies' table
            # they might be hybrid. For now, strict check on STOCK folder for Watchlist/Portfolio.
            
            # Explicit Phantoms (User Request)
            if t in ["CASH", "LTG", "TITC", "EUR", "VBNK.TO", "VBKN.TO"]: # Added typo version just in case
                 cursor.execute("DELETE FROM companies WHERE ticker = ?", (t,))
                 cleaned_count += 1
                 continue
            
            # Folder Check
            stock_path = os.path.join(self.root_path, "STOCK", t)
            if not os.path.exists(stock_path) and cat in ['Watchlist', 'Portfolio']:
                print(f"Pruning phantom company from DB: {t} (No folder found)")
                cursor.execute("DELETE FROM companies WHERE ticker = ?", (t,))
                cleaned_count += 1
                continue

            last_up = self.calculate_last_update(t)
            cursor.execute("UPDATE companies SET last_update = ? WHERE ticker = ?", (last_up, t))
                
        # Separate pass for Alias Cleanup (VBNK)
        cursor.execute("SELECT ticker, aliases FROM companies WHERE aliases LIKE '%VBNK.TO%'")
        alias_rows = cursor.fetchall()
        for t, als in alias_rows:
            if als:
                new_als = ", ".join([a.strip() for a in als.split(',') if "VBNK.TO" not in a.strip().upper()])
                cursor.execute("UPDATE companies SET aliases = ? WHERE ticker = ?", (new_als, t))
                print(f"Removed VBNK.TO alias from {t}")

        if cleaned_count > 0:
            print(f"Pruned {cleaned_count} phantom companies from DB.")

        conn.commit()
        conn.close()

    def get_companies(self, category=None):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if category:
            cursor.execute("SELECT * FROM companies WHERE category = ?", (category,))
        else:
            cursor.execute("SELECT * FROM companies")
            
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def update_company(self, ticker, **kwargs):
        """Update fields for a company."""
        if not kwargs: return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cols = []
        vals = []
        for k, v in kwargs.items():
            cols.append(f"{k} = ?")
            vals.append(v)
            
        vals.append(ticker)
        
        query = f"UPDATE companies SET {', '.join(cols)} WHERE ticker = ?"
        cursor.execute(query, tuple(vals))
        
        conn.commit()
        conn.close()


    def calculate_last_update(self, ticker):
        """
        Returns the latest date (YYYY-MM-DD) of activity for a ticker.
        Max of:
        1. Newest File (date_added)
        2. Newest Time Log (end_time) where duration > 25 mins (1500 sec)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Check Files
        # date_added format: 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'
        max_file_date = None
        try:
            cursor.execute("SELECT MAX(date_added) FROM files WHERE ticker = ?", (ticker,))
            res = cursor.fetchone()
            if res and res[0]:
                max_file_date = res[0][:10] # Just YYYY-MM-DD
        except: pass
        
        # 2. Check Time Logs (> 25 mins)
        # Using simple query if time_logs exists
        max_log_date = None
        try:
            # Check if table exists first to avoid crash if not migrated
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='time_logs'")
            if cursor.fetchone():
                # duration is usually in seconds. 25 min = 1500s
                cursor.execute("SELECT MAX(end_time) FROM time_logs WHERE ticker = ? AND duration >= 1500", (ticker,))
                res = cursor.fetchone()
                if res and res[0]:
                    max_log_date = res[0][:10]
        except: pass
        
        conn.close()
        
        dates = []
        if max_file_date: dates.append(max_file_date)
        if max_log_date: dates.append(max_log_date)
        
        # 3. Check Excel File Modification (Highest Priority)
        excel_date = None
        try:
            stock_path = os.path.join(self.root_path, "STOCK", ticker)
            excel_folder_name = f"3 EXCEL {ticker}"
            excel_path = os.path.join(stock_path, excel_folder_name)
            
            # print(f"DEBUG: Checking Excel path for {ticker}: {excel_path}") # Debug path
            
            if os.path.exists(excel_path):
                # Find all xlsx and xlsm files
                files = [f for f in os.listdir(excel_path) if f.lower().endswith(('.xlsx', '.xlsm'))]
                # print(f"DEBUG: Found {len(files)} excel files for {ticker}")
                
                if files:
                    # Get latest modification time
                    latest_mtime = 0
                    for f in files:
                        full_path = os.path.join(excel_path, f)
                        mtime = os.path.getmtime(full_path)
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                    
                    if latest_mtime > 0:
                        excel_date = datetime.fromtimestamp(latest_mtime).strftime('%Y-%m-%d')
            else:
                 pass
        except Exception as e:
            print(f"Error checking excel date for {ticker}: {e}")

        # 4. Check All Other Folders (Reports, Transcripts, Varios) - Fallback
        # This makes upload "live" without needing DB sync
        folder_date = None
        try:
            subfolders = [f"1 REPORTS {ticker}", f"2 TRANSCRIPTS {ticker}", f"4 VARIOS {ticker}"]
            latest_mtime = 0
            
            for sub in subfolders:
                s_path = os.path.join(self.root_path, "STOCK", ticker, sub)
                if os.path.exists(s_path):
                     # Recursive scan or just top level? Usually scan years.
                     # Simplified: Walk the directory tree
                    for root, dirs, files in os.walk(s_path):
                        for f in files:
                            # Skip temp files
                            if f.startswith("~$") or f == "Thumbs.db": continue
                            
                            full_path = os.path.join(root, f)
                            mtime = os.path.getmtime(full_path)
                            if mtime > latest_mtime:
                                latest_mtime = mtime
            
            if latest_mtime > 0:
                folder_date = datetime.fromtimestamp(latest_mtime).strftime('%Y-%m-%d')
                
        except Exception as e:
            print(f"Error checking folder dates for {ticker}: {e}")

        # Priority: Excel > Folder Scan > DB Files > DB Logs
        if excel_date: dates.append(excel_date)
        if folder_date: dates.append(folder_date)
        
        if not dates:
            return "N/A"
            
        return max(dates)
        
    def delete_company(self, ticker):
        """
        Deletes a company from the database and moves its folder to the Recycle Bin.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Delete from DB
            cursor.execute("DELETE FROM companies WHERE ticker = ?", (ticker,))
            conn.commit()
            
            # 2. Move Folder to Recycle Bin
            stock_path = os.path.join(self.root_path, "STOCK", ticker)
            
            if os.path.exists(stock_path):
                # PowerShell Recycle Bin - TEMPORARILY DISABLED (Crash Suspect)
                # try:
                #     import subprocess
                #     # PowerShell command to recycle
                #     # Load VisualBasic assembly to use FileSystem.DeleteDirectory with Recycle option
                #     ps_command = f"""
                #     Add-Type -AssemblyName Microsoft.VisualBasic
                #     [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory('{stock_path}', 'OnlyErrorDialogs', 'Recycle')
                #     """
                #     subprocess.run(["powershell", "-Command", ps_command], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                #     return True
                # except Exception as e:
                #     print(f"Recycle Bin failed, trying manual move to _Trash: {e}")
                
                # Fallback / Safe Implementation: Move to _Trash
                trash_path = os.path.join(self.root_path, "_Trash")
                if not os.path.exists(trash_path): os.makedirs(trash_path)
                
                import shutil
                # Handle name collision in trash
                dest = os.path.join(trash_path, f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                try:
                    # print(f"DEBUG: PERMANENTLY DELETING {stock_path} (User Request: Disable Recycle Logic)")
                    # shutil.rmtree(stock_path) # PERMANENT DELETE as per user request to fix crash
                    shutil.move(stock_path, dest)
                except Exception as e:
                    print(f"Move to trash failed: {e}")
                    return False
                return True
                    
            return True # Already gone from FS
            
        except Exception as e:
            print(f"Error deleting company {ticker}: {e}")
            return False
        finally:
            conn.close()

    def rename_company(self, old_ticker, new_ticker):
        """
        Renames a company's ticker across database and filesystem.
        """
        old_ticker = old_ticker.strip().upper()
        new_ticker = new_ticker.strip().upper()
        if old_ticker == new_ticker:
            return True, "No change in ticker."
            
        # Check duplicate
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT ticker FROM companies WHERE ticker = ?", (new_ticker,))
        if cursor.fetchone():
            conn.close()
            return False, f"Ticker {new_ticker} already exists in database."
            
        # Filesystem paths
        from config import LIBRARY_ROOT
        old_cloud_dir = os.path.join(str(LIBRARY_ROOT), "STOCK", old_ticker)
        new_cloud_dir = os.path.join(str(LIBRARY_ROOT), "STOCK", new_ticker)
        old_local_dir = os.path.join(r"D:\00_LOCAL_ARCHIVE_NO_SYNC\Ekomonos_Library\STOCK", old_ticker)
        new_local_dir = os.path.join(r"D:\00_LOCAL_ARCHIVE_NO_SYNC\Ekomonos_Library\STOCK", new_ticker)
        
        # 1. Delete old junction link inside cloud folder first (if it exists) to prevent conflicts
        if os.path.exists(old_cloud_dir):
            junction_path = os.path.join(old_cloud_dir, "02_Fuentes_Inmutables")
            if os.path.lexists(junction_path):
                try:
                    # Since it is a junction, os.rmdir will delete the link without deleting contents
                    os.rmdir(junction_path)
                except Exception as e:
                    conn.close()
                    return False, f"Failed to remove old junction: {e}"

        # 2. Rename folder on disk
        # First rename the local archive folder (where real files live)
        if os.path.exists(old_local_dir):
            try:
                os.rename(old_local_dir, new_local_dir)
            except Exception as e:
                # Restore old junction if deleted and abort
                if os.path.exists(old_cloud_dir):
                    old_junction_path = os.path.join(old_cloud_dir, "02_Fuentes_Inmutables")
                    old_local_base = os.path.join(old_local_dir, "02_Fuentes_Inmutables")
                    if os.path.exists(old_local_base):
                        import subprocess
                        subprocess.run(f'cmd /c mklink /J "{old_junction_path}" "{old_local_base}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                conn.close()
                return False, f"Failed to rename local archive directory: {e}"
                
        # Second, rename cloud folder
        if os.path.exists(old_cloud_dir):
            try:
                # Rename the subfolders that contain the ticker name (backward compatibility / legacy)
                for sub in ["1 REPORTS", "2 TRANSCRIPTS", "3 EXCEL", "4 VARIOS"]:
                    old_sub = os.path.join(old_cloud_dir, f"{sub} {old_ticker}")
                    new_sub = os.path.join(old_cloud_dir, f"{sub} {new_ticker}")
                    if os.path.exists(old_sub):
                        os.rename(old_sub, new_sub)
                
                # Now rename the main cloud directory
                os.rename(old_cloud_dir, new_cloud_dir)
            except Exception as e:
                # Restore old local directory and old junction and abort
                if os.path.exists(new_local_dir):
                    try: os.rename(new_local_dir, old_local_dir)
                    except: pass
                if os.path.exists(old_cloud_dir):
                    old_junction_path = os.path.join(old_cloud_dir, "02_Fuentes_Inmutables")
                    old_local_base = os.path.join(old_local_dir, "02_Fuentes_Inmutables")
                    if os.path.exists(old_local_base):
                        import subprocess
                        subprocess.run(f'cmd /c mklink /J "{old_junction_path}" "{old_local_base}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                conn.close()
                return False, f"Failed to rename cloud directory: {e}"
                
            # Recreate junction under new cloud directory
            new_junction_path = os.path.join(new_cloud_dir, "02_Fuentes_Inmutables")
            new_local_base = os.path.join(new_local_dir, "02_Fuentes_Inmutables")
            if os.path.exists(new_local_base):
                import subprocess
                res = subprocess.run(f'cmd /c mklink /J "{new_junction_path}" "{new_local_base}"', shell=True, capture_output=True, text=True)
                if res.returncode != 0:
                    print(f"[CompaniesManager] mklink failed: {res.stderr.strip()} (cmd: cmd /c mklink /J \"{new_junction_path}\" \"{new_local_base}\")")
                
        # 2. Database updates
        try:
            # Table companies
            cursor.execute("UPDATE companies SET ticker = ? WHERE ticker = ?", (new_ticker, old_ticker))
            
            # Table files: update ticker
            cursor.execute("UPDATE files SET ticker = ? WHERE ticker = ?", (new_ticker, old_ticker))
            
            # Table files: update paths containing old_ticker
            cursor.execute("SELECT id, path FROM files WHERE ticker = ?", (new_ticker,))
            file_rows = cursor.fetchall()
            for fid, path in file_rows:
                if path:
                    # Replace both backslashes and slashes to be safe
                    new_path = path.replace(f"STOCK\\{old_ticker}\\", f"STOCK\\{new_ticker}\\")
                    new_path = new_path.replace(f"STOCK/{old_ticker}/", f"STOCK/{new_ticker}/")
                    # Also replace in the f" {old_ticker}" subfolders
                    new_path = new_path.replace(f" REPORTS {old_ticker}", f" REPORTS {new_ticker}")
                    new_path = new_path.replace(f" TRANSCRIPTS {old_ticker}", f" TRANSCRIPTS {new_ticker}")
                    new_path = new_path.replace(f" EXCEL {old_ticker}", f" EXCEL {new_ticker}")
                    new_path = new_path.replace(f" VARIOS {old_ticker}", f" VARIOS {new_ticker}")
                    
                    if new_path != path:
                        cursor.execute("UPDATE files SET path = ? WHERE id = ?", (new_path, fid))
                        
            # Table special_situations: check if ticker exists in JSON array/object
            cursor.execute("SELECT id, tickers FROM special_situations")
            spec_rows = cursor.fetchall()
            for sid, tickers_json in spec_rows:
                if tickers_json:
                    try:
                        import json
                        t_data = json.loads(tickers_json)
                        changed = False
                        if isinstance(t_data, list):
                            for idx, val in enumerate(t_data):
                                if val.strip().upper() == old_ticker:
                                    t_data[idx] = new_ticker
                                    changed = True
                        elif isinstance(t_data, dict):
                            for key, val in t_data.items():
                                if val.strip().upper() == old_ticker:
                                    t_data[key] = new_ticker
                                    changed = True
                        if changed:
                            cursor.execute("UPDATE special_situations SET tickers = ? WHERE id = ?", (json.dumps(t_data), sid))
                    except:
                        pass
                        
            conn.commit()
            conn.close()
            return True, "Success"
        except Exception as db_e:
            if conn:
                conn.rollback()
                conn.close()
            return False, f"Database update error: {db_e}"
