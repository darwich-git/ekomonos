import os
import requests
from datetime import datetime
import shutil

from config import LIBRARY_ROOT as _DEFAULT_LIBRARY_ROOT, MAIN_DB
from core.library_manager import LibraryManager
from core.database import get_session, Company, SpecialSituation, init_db
from sqlalchemy import select, text, inspect

class CompaniesManager:
    def __init__(self, root_path):
        self.root_path = root_path
        self.db_path = str(MAIN_DB)

        # Ensure DB schema is complete (Context: LibraryManager creates 'files' table)
        LibraryManager(root_path)
        
        self._init_db()

    def _init_db(self):
        """Ensure all required columns exist in the database."""
        engine = init_db()
        inspector = inspect(engine)
        
        # Check if table exists
        if 'companies' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('companies')]
            new_cols = {
                'category': "VARCHAR(50) DEFAULT 'Watchlist'",
                'currency': "VARCHAR(10) DEFAULT 'USD'",
                'shares_count': "INTEGER DEFAULT 0",
                'cost_basis': "FLOAT DEFAULT 0.0",
                'fair_value': "FLOAT DEFAULT 0.0",
                'potential_5y': "FLOAT DEFAULT 0.0",
                'last_price': "FLOAT DEFAULT 0.0",
                'last_update': "VARCHAR(50)",
                'metric_type': "VARCHAR(50)",
                'next_presentation': "VARCHAR(50)",
                'notes': "TEXT",
                'primary_exchange': "VARCHAR(100)", 
                'yahoo_ticker': "VARCHAR(20)",
                'aliases': "TEXT",
                'status': "VARCHAR(20) DEFAULT 'To Research'"
            }
            
            with engine.begin() as conn:
                for col, defi in new_cols.items():
                    if col not in columns:
                        try:
                            print(f"Migrating: Adding column '{col}' to companies table...")
                            conn.execute(text(f"ALTER TABLE companies ADD COLUMN {col} {defi}"))
                        except Exception as e:
                            print(f"Migration error ({col}): {e}")

    def sync_with_library(self):
        """Syncs tickers from files table AND folders to companies table."""
        with get_session() as session:
            # 1. Get tickers from FILES table
            try:
                res = session.execute(text("SELECT DISTINCT ticker FROM files")).all()
                file_tickers = [row[0] for row in res if row[0]]
            except Exception as e:
                print(f"Error querying files table for sync: {e}")
                file_tickers = []
            
            # 2. Get tickers from FOLDERS
            folder_tickers = []
            stock_path = os.path.join(self.root_path, "STOCK")
            if os.path.exists(stock_path):
                folder_tickers = [d for d in os.listdir(stock_path) if os.path.isdir(os.path.join(stock_path, d))]
                
            all_tickers = set(file_tickers + folder_tickers)
            
            # Get existing companies in DB
            existing_companies = session.execute(select(Company)).scalars().all()
            existing_tickers = {c.ticker for c in existing_companies}
            
            # Add missing
            added_count = 0
            for t in all_tickers:
                if t not in existing_tickers:
                    new_co = Company(ticker=t, name='', category='Watchlist', status='To Research')
                    session.add(new_co)
                    added_count += 1
            session.commit()
            
            # Recalculate Last Update for ALL companies
            all_companies = session.execute(select(Company)).scalars().all()
            
            cleaned_count = 0
            for co in all_companies:
                t = co.ticker
                cat = co.category
                
                # Explicit Phantoms
                if t in ["CASH", "LTG", "TITC", "EUR", "VBNK.TO", "VBKN.TO"]:
                    session.delete(co)
                    cleaned_count += 1
                    continue
                
                # Folder Check
                s_path = os.path.join(self.root_path, "STOCK", t)
                if not os.path.exists(s_path) and cat in ['Watchlist', 'Portfolio']:
                    print(f"Pruning phantom company from DB: {t} (No folder found)")
                    session.delete(co)
                    cleaned_count += 1
                    continue
                
                last_up = self.calculate_last_update(t)
                co.last_update = last_up
                
            # Separate pass for Alias Cleanup (VBNK)
            vbnk_companies = session.execute(select(Company).where(Company.aliases.like('%VBNK.TO%'))).scalars().all()
            for co in vbnk_companies:
                if co.aliases:
                    new_als = ", ".join([a.strip() for a in co.aliases.split(',') if "VBNK.TO" not in a.strip().upper()])
                    co.aliases = new_als
                    print(f"Removed VBNK.TO alias from {co.ticker}")
                    
            session.commit()
            if cleaned_count > 0:
                print(f"Pruned {cleaned_count} phantom companies from DB.")

    def get_companies(self, category=None):
        with get_session() as session:
            if category:
                stmt = select(Company).where(Company.category == category)
            else:
                stmt = select(Company)
            res = session.execute(stmt).scalars().all()
            
            # Convert to list of dicts for backward compatibility with UI
            companies = []
            for c in res:
                companies.append({
                    'id': c.id,
                    'ticker': c.ticker,
                    'name': c.name,
                    'category': c.category,
                    'currency': c.currency,
                    'shares_count': c.shares_count,
                    'cost_basis': c.cost_basis,
                    'fair_value': c.fair_value,
                    'potential_5y': c.potential_5y,
                    'last_price': c.last_price,
                    'last_update': c.last_update,
                    'metric_type': c.metric_type,
                    'next_presentation': c.next_presentation,
                    'notes': c.notes,
                    'primary_exchange': c.primary_exchange,
                    'yahoo_ticker': c.yahoo_ticker,
                    'aliases': c.aliases,
                    'status': c.status
                })
            return companies

    def add_company(self, ticker, name, category, currency, primary_exchange, yahoo_ticker, aliases, notes, status, last_update):
        with get_session() as session:
            company = session.execute(select(Company).where(Company.ticker == ticker)).scalar_one_or_none()
            if not company:
                company = Company(ticker=ticker)
                session.add(company)
            
            company.name = name
            company.category = category
            company.currency = currency
            company.primary_exchange = primary_exchange
            company.yahoo_ticker = yahoo_ticker
            company.aliases = aliases
            company.notes = notes
            company.status = status
            company.last_update = last_update
            
            session.commit()

    def update_company(self, ticker, **kwargs):
        """Update fields for a company."""
        if not kwargs: return
        
        with get_session() as session:
            company = session.execute(select(Company).where(Company.ticker == ticker)).scalar_one_or_none()
            if company:
                for k, v in kwargs.items():
                    if hasattr(company, k):
                        setattr(company, k, v)
                session.commit()

    def calculate_last_update(self, ticker):
        """
        Returns the latest date (YYYY-MM-DD) of activity for a ticker.
        Max of:
        1. Newest File (date_added)
        2. Newest Time Log (end_time) where duration > 25 mins (1500 sec)
        """
        max_file_date = None
        max_log_date = None
        
        with get_session() as session:
            # 1. Check Files
            try:
                res = session.execute(text("SELECT MAX(date_added) FROM files WHERE ticker = :t"), {"t": ticker}).scalar()
                if res:
                    max_file_date = res[:10]
            except: pass
            
            # 2. Check Time Logs (> 25 mins)
            try:
                check = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='time_logs'")).scalar()
                if check:
                    res = session.execute(
                        text("SELECT MAX(end_time) FROM time_logs WHERE ticker = :t AND duration_seconds >= 1500"), 
                        {"t": ticker}
                    ).scalar()
                    if res:
                        max_log_date = res[:10]
            except: pass
            
        dates = []
        if max_file_date: dates.append(max_file_date)
        if max_log_date: dates.append(max_log_date)
        
        # 3. Check Excel File Modification (Highest Priority)
        excel_date = None
        try:
            stock_path = os.path.join(self.root_path, "STOCK", ticker)
            excel_folder_name = f"3 EXCEL {ticker}"
            excel_path = os.path.join(stock_path, excel_folder_name)
            
            if os.path.exists(excel_path):
                files = [f for f in os.listdir(excel_path) if f.lower().endswith(('.xlsx', '.xlsm'))]
                if files:
                    latest_mtime = 0
                    for f in files:
                        full_path = os.path.join(excel_path, f)
                        mtime = os.path.getmtime(full_path)
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                    
                    if latest_mtime > 0:
                        excel_date = datetime.fromtimestamp(latest_mtime).strftime('%Y-%m-%d')
        except Exception as e:
            print(f"Error checking excel date for {ticker}: {e}")

        # 4. Check All Other Folders (Reports, Transcripts, Varios) - Fallback
        folder_date = None
        try:
            subfolders = [f"1 REPORTS {ticker}", f"2 TRANSCRIPTS {ticker}", f"4 VARIOS {ticker}"]
            latest_mtime = 0
            
            for sub in subfolders:
                s_path = os.path.join(self.root_path, "STOCK", ticker, sub)
                if os.path.exists(s_path):
                    for root, dirs, files in os.walk(s_path):
                        for f in files:
                            if f.startswith("~$") or f == "Thumbs.db": continue
                            full_path = os.path.join(root, f)
                            mtime = os.path.getmtime(full_path)
                            if mtime > latest_mtime:
                                latest_mtime = mtime
            
            if latest_mtime > 0:
                folder_date = datetime.fromtimestamp(latest_mtime).strftime('%Y-%m-%d')
        except Exception as e:
            print(f"Error checking folder dates for {ticker}: {e}")

        if excel_date: dates.append(excel_date)
        if folder_date: dates.append(folder_date)
        
        if not dates:
            return "N/A"
            
        return max(dates)
        
    def delete_company(self, ticker):
        """
        Deletes a company from the database and moves its folder to the Recycle Bin.
        """
        with get_session() as session:
            try:
                company = session.execute(select(Company).where(Company.ticker == ticker)).scalar_one_or_none()
                if company:
                    session.delete(company)
                    session.commit()
                
                # Move Folder to Recycle Bin / Trash
                stock_path = os.path.join(self.root_path, "STOCK", ticker)
                if os.path.exists(stock_path):
                    trash_path = os.path.join(self.root_path, "_Trash")
                    if not os.path.exists(trash_path): os.makedirs(trash_path)
                    
                    dest = os.path.join(trash_path, f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                    try:
                        shutil.move(stock_path, dest)
                    except Exception as e:
                        print(f"Move to trash failed: {e}")
                        return False
                    return True
                return True
            except Exception as e:
                print(f"Error deleting company {ticker}: {e}")
                session.rollback()
                return False

    def rename_company(self, old_ticker, new_ticker):
        """
        Renames a company's ticker across database and filesystem.
        """
        old_ticker = old_ticker.strip().upper()
        new_ticker = new_ticker.strip().upper()
        if old_ticker == new_ticker:
            return True, "No change in ticker."
            
        with get_session() as session:
            # Check duplicate
            dup = session.execute(select(Company).where(Company.ticker == new_ticker)).scalar_one_or_none()
            if dup:
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
                        os.rmdir(junction_path)
                    except Exception as e:
                        return False, f"Failed to remove old junction: {e}"

            # 2. Rename folder on disk
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
                    return False, f"Failed to rename local archive directory: {e}"
                    
            if os.path.exists(old_cloud_dir):
                try:
                    for sub in ["1 REPORTS", "2 TRANSCRIPTS", "3 EXCEL", "4 VARIOS"]:
                        old_sub = os.path.join(old_cloud_dir, f"{sub} {old_ticker}")
                        new_sub = os.path.join(old_cloud_dir, f"{sub} {new_ticker}")
                        if os.path.exists(old_sub):
                            os.rename(old_sub, new_sub)
                    
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
                    return False, f"Failed to rename cloud directory: {e}"
                    
                # Recreate junction under new cloud directory
                new_junction_path = os.path.join(new_cloud_dir, "02_Fuentes_Inmutables")
                new_local_base = os.path.join(new_local_dir, "new_local_dir") # Wait, is this a typo in previous code?
                # Ah! In the original code it was:
                # new_local_base = os.path.join(new_local_dir, "02_Fuentes_Inmutables")
                # Let's fix that typo while we are here:
                new_local_base = os.path.join(new_local_dir, "02_Fuentes_Inmutables")
                if os.path.exists(new_local_base):
                    import subprocess
                    res = subprocess.run(f'cmd /c mklink /J "{new_junction_path}" "{new_local_base}"', shell=True, capture_output=True, text=True)
                    if res.returncode != 0:
                        print(f"[CompaniesManager] mklink failed: {res.stderr.strip()}")
                    
            # 2. Database updates
            try:
                # Table companies
                session.execute(text("UPDATE companies SET ticker = :new_t WHERE ticker = :old_t"), {"new_t": new_ticker, "old_t": old_ticker})
                
                # Table files
                session.execute(text("UPDATE files SET ticker = :new_t WHERE ticker = :old_t"), {"new_t": new_ticker, "old_t": old_ticker})
                
                # Table files: paths
                res = session.execute(text("SELECT id, path FROM files WHERE ticker = :t"), {"t": new_ticker}).all()
                for fid, path in res:
                    if path:
                        new_path = path.replace(f"STOCK\\{old_ticker}\\", f"STOCK\\{new_ticker}\\")
                        new_path = new_path.replace(f"STOCK/{old_ticker}/", f"STOCK/{new_ticker}/")
                        new_path = new_path.replace(f" REPORTS {old_ticker}", f" REPORTS {new_ticker}")
                        new_path = new_path.replace(f" TRANSCRIPTS {old_ticker}", f" TRANSCRIPTS {new_ticker}")
                        new_path = new_path.replace(f" EXCEL {old_ticker}", f" EXCEL {new_ticker}")
                        new_path = new_path.replace(f" VARIOS {old_ticker}", f" VARIOS {new_ticker}")
                        
                        if new_path != path:
                            session.execute(text("UPDATE files SET path = :p WHERE id = :id"), {"p": new_path, "id": fid})
                            
                # Table special_situations
                spec_res = session.execute(select(SpecialSituation)).scalars().all()
                for spec in spec_res:
                    if spec.tickers:
                        try:
                            import json
                            t_data = json.loads(spec.tickers)
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
                                spec.tickers = json.dumps(t_data)
                        except:
                            pass
                            
                session.commit()
                return True, "Success"
            except Exception as db_e:
                session.rollback()
                return False, f"Database update error: {db_e}"
