import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.services.company_service import CompanyService
from core.database import init_db

class TestCompanyService(unittest.TestCase):
    def setUp(self):
        self.service = CompanyService()
        
    def test_get_all_companies(self):
        companies = self.service.get_all()
        self.assertIsInstance(companies, list, "Service should return a list even if empty")
        # Ensure it's returning dicts or objects we expect
        if len(companies) > 0:
            self.assertIn('id', companies[0], "Company dictionary must have 'id'")
            self.assertIn('ticker', companies[0], "Company dictionary must have 'ticker'")
            
    def test_search_company(self):
        # A search for gibberish should be None
        res = self.service.get_by_ticker("GIBBERISH_XYZ_123")
        self.assertIsNone(res)

    def test_rename_company(self):
        # We will insert a dummy company, then rename it, and verify, and clean up.
        # Use a unique ticker like "TSTRNM" to avoid conflicts.
        import sqlite3
        from config import MAIN_DB, LIBRARY_ROOT
        
        old_ticker = "TSTRNM"
        new_ticker = "TSTRNM2"
        
        # Ensure directories exist
        import os
        from pathlib import Path
        
        old_cloud_dir = os.path.join(str(LIBRARY_ROOT), "STOCK", old_ticker)
        new_cloud_dir = os.path.join(str(LIBRARY_ROOT), "STOCK", new_ticker)
        old_local_dir = os.path.join(r"D:\00_LOCAL_ARCHIVE_NO_SYNC\Ekomonos_Library\STOCK", old_ticker)
        new_local_dir = os.path.join(r"D:\00_LOCAL_ARCHIVE_NO_SYNC\Ekomonos_Library\STOCK", new_ticker)
        
        # Clean up any leftover test data
        for d in [old_cloud_dir, new_cloud_dir, old_local_dir, new_local_dir]:
            if os.path.exists(d):
                # Delete junction first if it exists to avoid deleting real files
                junction = os.path.join(d, "02_Fuentes_Inmutables")
                if os.path.exists(junction):
                    try: os.rmdir(junction)
                    except: pass
                try:
                    import shutil
                    shutil.rmtree(d)
                except:
                    pass
                    
        conn = sqlite3.connect(str(MAIN_DB))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM companies WHERE ticker IN (?, ?)", (old_ticker, new_ticker))
        cursor.execute("DELETE FROM files WHERE ticker IN (?, ?)", (old_ticker, new_ticker))
        conn.commit()
        
        # Create directories
        os.makedirs(old_cloud_dir, exist_ok=True)
        os.makedirs(old_local_dir, exist_ok=True)
        # Create subfolders inside cloud
        for sub in ["1 REPORTS", "2 TRANSCRIPTS", "3 EXCEL", "4 VARIOS"]:
            os.makedirs(os.path.join(old_cloud_dir, f"{sub} {old_ticker}"), exist_ok=True)
            
        # Create a test file inside local, and create junction link
        os.makedirs(os.path.join(old_local_dir, "02_Fuentes_Inmutables"), exist_ok=True)
        junction_path = os.path.join(old_cloud_dir, "02_Fuentes_Inmutables")
        local_base = os.path.join(old_local_dir, "02_Fuentes_Inmutables")
        import subprocess
        subprocess.run(f'cmd /c mklink /J "{junction_path}" "{local_base}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Insert company to db
        # fortress_vault.db requires non-null columns (ticker, name, status, sector)
        cursor.execute(
            "INSERT INTO companies (ticker, name, status, sector, category) VALUES (?, ?, ?, ?, ?)",
            (old_ticker, "Test Rename Co", "To Research", "Technology", "Watchlist")
        )
        # Insert dummy file
        cursor.execute(
            "INSERT INTO files (ticker, path, category) VALUES (?, ?, ?)",
            (old_ticker, f"STOCK\\{old_ticker}\\1 REPORTS {old_ticker}\\report.pdf", "Reports")
        )
        conn.commit()
        conn.close()
        
        try:
            # Execute rename via service!
            success, msg = self.service.rename_company(old_ticker, new_ticker)
            self.assertTrue(success, f"Rename failed: {msg}")
            
            # Verify FS
            self.assertFalse(os.path.exists(old_cloud_dir), "Old cloud dir should not exist")
            self.assertTrue(os.path.exists(new_cloud_dir), "New cloud dir should exist")
            self.assertFalse(os.path.exists(old_local_dir), "Old local dir should not exist")
            self.assertTrue(os.path.exists(new_local_dir), "New local dir should exist")
            
            # Verify subfolders renamed
            for sub in ["1 REPORTS", "2 TRANSCRIPTS", "3 EXCEL", "4 VARIOS"]:
                self.assertTrue(os.path.exists(os.path.join(new_cloud_dir, f"{sub} {new_ticker}")), f"{sub} folder was not renamed")
                
            # Verify junction link recreated
            new_junction_path = os.path.join(new_cloud_dir, "02_Fuentes_Inmutables")
            self.assertTrue(os.path.exists(new_junction_path), "Junction link was not recreated")
            
            # Verify DB
            conn = sqlite3.connect(str(MAIN_DB))
            cursor = conn.cursor()
            cursor.execute("SELECT ticker, name FROM companies WHERE ticker = ?", (new_ticker,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, "Company not found under new ticker in DB")
            self.assertEqual(row[1], "Test Rename Co")
            
            cursor.execute("SELECT ticker FROM companies WHERE ticker = ?", (old_ticker,))
            self.assertIsNone(cursor.fetchone(), "Company still exists under old ticker in DB")
            
            # Verify files table updated
            cursor.execute("SELECT ticker, path FROM files WHERE ticker = ?", (new_ticker,))
            file_row = cursor.fetchone()
            self.assertIsNotNone(file_row)
            self.assertEqual(file_row[1], f"STOCK\\{new_ticker}\\1 REPORTS {new_ticker}\\report.pdf")
            
            conn.close()
            
        finally:
            # Clean up test directories and database rows
            for d in [old_cloud_dir, new_cloud_dir, old_local_dir, new_local_dir]:
                if os.path.exists(d):
                    # Delete junction first if it exists to avoid deleting real files
                    junction = os.path.join(d, "02_Fuentes_Inmutables")
                    if os.path.exists(junction):
                        try: os.rmdir(junction)
                        except: pass
                    try:
                        import shutil
                        shutil.rmtree(d)
                    except:
                        pass
            conn = sqlite3.connect(str(MAIN_DB))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM companies WHERE ticker IN (?, ?)", (old_ticker, new_ticker))
            cursor.execute("DELETE FROM files WHERE ticker IN (?, ?)", (old_ticker, new_ticker))
            conn.commit()
            conn.close()

if __name__ == '__main__':
    unittest.main()
