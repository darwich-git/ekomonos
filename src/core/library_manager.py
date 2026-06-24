import os
import sqlite3
import json
import csv
from datetime import datetime
from config import MAIN_DB

class LibraryManager:
    def __init__(self, root_path):
        self.root_path = root_path
        self.db_path = str(MAIN_DB) # Apunta ahora directamente a fortress_vault.db
        self._init_db()
        
    def _init_db(self):
        """Initialize the SQLite database and tables."""
        if not os.path.exists(self.root_path):
            os.makedirs(self.root_path, exist_ok=True)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if columns exist (migration for existing DB)
        cursor.execute("PRAGMA table_info(files)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if not columns:
            # Create new table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    ticker TEXT,
                    category TEXT,
                    year TEXT,
                    quarter TEXT,
                    status INTEGER DEFAULT 0, -- 0=New, 1=In Process, 2=Reviewed
                    language TEXT DEFAULT 'EN',
                    notes_json TEXT
                )
            ''')
        else:
            # Migrate if needed
            if 'status' not in columns:
                cursor.execute("ALTER TABLE files ADD COLUMN status INTEGER DEFAULT 0")
                # Migrate old 'reviewed' boolean if it existed (it was in previous schema)
                if 'reviewed' in columns:
                    cursor.execute("UPDATE files SET status = 2 WHERE reviewed = 1")
            
            if 'language' not in columns:
                cursor.execute("ALTER TABLE files ADD COLUMN language TEXT DEFAULT 'EN'")
                
            if 'last_page_read' not in columns:
                cursor.execute("ALTER TABLE files ADD COLUMN last_page_read INTEGER DEFAULT 0")
                
            if 'last_accessed' not in columns:
                cursor.execute("ALTER TABLE files ADD COLUMN last_accessed TEXT") # Store as ISO string

        conn.commit()
        conn.close()

    def get_file_metadata(self, path):
        """Retrieve metadata for a specific file."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT category, year, quarter, status, language, notes_json, last_page_read, last_accessed FROM files WHERE path = ?', (path,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "category": row[0],
                "year": row[1],
                "quarter": row[2],
                "status": row[3],
                "language": row[4],
                "notes": json.loads(row[5]) if row[5] else {},
                "last_page_read": row[6] if row[6] else 0,
                "last_accessed": row[7]
            }
        return None

    def update_file_metadata(self, path, ticker, category=None, year=None, quarter=None, status=None, language=None, notes=None, last_page_read=None, last_accessed=None):
        """Update or insert metadata for a file."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute('SELECT id, notes_json FROM files WHERE path = ?', (path,))
        row = cursor.fetchone()
        
        current_notes = json.loads(row[1]) if row and row[1] else {}
        if notes:
            current_notes.update(notes)
            
        if row:
            # Update
            query = 'UPDATE files SET ticker = ?'
            params = [ticker]
            
            if category is not None:
                query += ', category = ?'
                params.append(category)
            if year is not None:
                query += ', year = ?'
                params.append(year)
            if quarter is not None:
                query += ', quarter = ?'
                params.append(quarter)
            if status is not None:
                query += ', status = ?'
                params.append(status)
            if language is not None:
                query += ', language = ?'
                params.append(language)
            if last_page_read is not None:
                query += ', last_page_read = ?'
                params.append(last_page_read)
            if last_accessed is not None:
                query += ', last_accessed = ?'
                params.append(last_accessed)
            
            query += ', notes_json = ? WHERE path = ?'
            params.append(json.dumps(current_notes))
            params.append(path)
            
            cursor.execute(query, tuple(params))
        else:
            # Insert
            cursor.execute('''
                INSERT INTO files (path, ticker, category, year, quarter, status, language, notes_json, last_page_read, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (path, ticker, category, year, quarter, status if status is not None else 0, language if language else 'EN', json.dumps(notes if notes else {}), last_page_read if last_page_read else 0, last_accessed))
            
        conn.commit()
        conn.close()

    def get_smart_resume_doc(self, ticker):
        """
        Waterfall Logic for Smart Resume:
        1. In Progress (status=1) ordered by last_accessed DESC
        2. Unread Tier 1 (Annual Reports, Transcript) ordered by Year DESC
        3. Excel/Thesis
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Priority A: In Progress
        cursor.execute('''
            SELECT path FROM files 
            WHERE ticker = ? AND status = 1 
            ORDER BY last_accessed DESC LIMIT 1
        ''', (ticker,))
        row = cursor.fetchone()
        if row: 
            conn.close()
            return row['path']
            
        # 2. Priority B: Unread Tier 1
        # Tier 1 = Annual Reports, Transcript (Proxy, Prospectus if mapped)
        # Assuming mapped category names
        cursor.execute('''
            SELECT path FROM files 
            WHERE ticker = ? AND status = 0 
            AND category IN ('Annual Reports', 'Transcript')
            ORDER BY year DESC, path ASC LIMIT 1
        ''', (ticker,))
        row = cursor.fetchone()
        if row:
            conn.close()
            return row['path']
            
        # 3. Priority C: Excel
        cursor.execute('''
            SELECT path FROM files 
            WHERE ticker = ? AND category = 'Excel'
            LIMIT 1
        ''', (ticker,))
        row = cursor.fetchone()
        conn.close()
        
        return row['path'] if row else None

    def get_company_progress(self, ticker):
        """
        Calculate composite progress score (0-100%) based on Legend:
        - 15% Files (Depth: 5 AR + 5 Transcripts)
        - 35% Reading (Weighted completion)
        - 30% Time (Target: 30 hours)
        - 20% Deliverables (Excel + Thesis)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT category, status, path FROM files WHERE ticker = ?', (ticker,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return 0, {}

        # 1. FILES (15%) - Depth
        count_ar = 0
        count_trans = 0
        has_excel = False
        has_thesis = False 
        
        # 2. READING (35%)
        reading_points_earned = 0
        reading_points_total = 0
        
        for category, status, path in rows:
            path_lower = path.lower()
            name_lower = os.path.basename(path).lower()

            # Metrics counts
            if category == "Annual Reports": count_ar += 1
            elif category == "Transcript": count_trans += 1
            
            # Excel Detection
            if category == "Excel" or path_lower.endswith(".xlsx") or path_lower.endswith(".xlsm") or "valuation" in name_lower:
                has_excel = True
            
            # Thesis detection (heuristic)
            # Use 'Category' if set, or filename keywords
            if category == "Tesis" or "thesis" in name_lower or "tesis" in name_lower or "analisis" in name_lower or "analysis" in name_lower:
                has_thesis = True
                
            # Reading Weights
            w = 2 # Low
            if category == "Annual Reports": w = 10
            elif category == "Transcript": w = 5
            
            reading_points_total += w
            if status == 2: # Reviewed
                reading_points_earned += w
            elif status == 1: # In Progress
                reading_points_earned += (w * 0.5)

        # Score A: Files (15%)
        # Target: 5 AR and 5 Transcripts
        score_ar = min(count_ar, 5) / 5.0
        score_trans = min(count_trans, 5) / 5.0
        score_files = ((score_ar + score_trans) / 2.0) * 15.0
        
        # Score B: Reading (35%)
        score_reading = 0
        if reading_points_total > 0:
            score_reading = (reading_points_earned / reading_points_total) * 35.0
            
        # Score C: Time (30%)
        # Target: 30 Hours
        hours = self.get_company_hours(ticker)
        score_time = min(hours / 30.0, 1.0) * 30.0
        
        # Score D: Deliverables (20%)
        # Excel (10%) + Thesis (10%)
        score_deliv = 0
        if has_excel: score_deliv += 10
        if has_thesis: score_deliv += 10
        
        total_pct = score_files + score_reading + score_time + score_deliv
        
        # Detailed Stats for Tooltips
        stats = {
            "count_ar": count_ar,
            "count_trans": count_trans,
            "has_excel": True if has_excel else False, # Force bool
            "has_thesis": True if has_thesis else False,
            "hours": round(hours, 1),
            "score_files": score_files,
            "score_reading": score_reading,
            "progress_percent": int(total_pct)
        }
        
        return int(total_pct), stats

    def check_duplicates(self, ticker, year, category):
        """Check for potential duplicates (same ticker, year, category)."""
        if category not in ["Annual Reports"]: # Mostly relevant for Annual Reports
            return []
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT path FROM files WHERE ticker = ? AND year = ? AND category = ?', (ticker, year, category))
        rows = cursor.fetchall()
        conn.close()
        
        return [r[0] for r in rows] if len(rows) > 1 else []

    def get_company_hours(self, ticker):
        """Calculate total hours spent on a company from the log."""
        log_file = os.path.join(self.root_path, "pomodoro_log.csv")
        if not os.path.exists(log_file):
            return 0.0
            
        total_minutes = 0
        try:
            with open(log_file, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Company") == ticker:
                        try:
                            duration = int(row.get("Duration (min)", 0))
                            total_minutes += duration
                        except ValueError:
                            pass
        except Exception as e:
            print(f"Error reading log: {e}")
            return 0.0
            
        return round(total_minutes / 60.0, 1)
