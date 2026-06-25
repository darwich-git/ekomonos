import os
import json
import csv
from datetime import datetime
from config import MAIN_DB
from core.database import get_session, File, init_db
from sqlalchemy import select, text, inspect

class LibraryManager:
    def __init__(self, root_path):
        self.root_path = root_path
        self.db_path = str(MAIN_DB)
        self._init_db()
        
    def _init_db(self):
        """Ensure all required columns exist in the files table."""
        if not os.path.exists(self.root_path):
            os.makedirs(self.root_path, exist_ok=True)
            
        engine = init_db()
        inspector = inspect(engine)
        
        # Check if table exists
        if 'files' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('files')]
            
            new_cols = {
                'status': "INTEGER DEFAULT 0",
                'language': "VARCHAR(10) DEFAULT 'EN'",
                'last_page_read': "INTEGER DEFAULT 0",
                'last_accessed': "VARCHAR(50)",
                'notes_json': "TEXT"
            }
            
            with engine.begin() as conn:
                # Migrate status first if needed (backward compatibility)
                if 'status' not in columns:
                    try:
                        conn.execute(text("ALTER TABLE files ADD COLUMN status INTEGER DEFAULT 0"))
                        # Migrate old 'reviewed' boolean if it existed
                        if 'reviewed' in columns:
                            conn.execute(text("UPDATE files SET status = 2 WHERE reviewed = 1"))
                    except Exception as e:
                        print(f"Migration error (status): {e}")
                
                for col, defi in new_cols.items():
                    if col == 'status': continue  # Already handled above
                    if col not in columns:
                        try:
                            print(f"Migrating: Adding column '{col}' to files table...")
                            conn.execute(text(f"ALTER TABLE files ADD COLUMN {col} {defi}"))
                        except Exception as e:
                            print(f"Migration error ({col}): {e}")

    def get_file_metadata(self, path):
        """Retrieve metadata for a specific file."""
        with get_session() as session:
            f = session.execute(select(File).where(File.path == path)).scalar_one_or_none()
            if f:
                return {
                    "category": f.category,
                    "year": f.year,
                    "quarter": f.quarter,
                    "status": f.status,
                    "language": f.language,
                    "notes": json.loads(f.notes_json) if f.notes_json else {},
                    "last_page_read": f.last_page_read,
                    "last_accessed": f.last_accessed
                }
            return None

    def update_file_metadata(self, path, ticker, category=None, year=None, quarter=None, status=None, language=None, notes=None, last_page_read=None, last_accessed=None):
        """Update or insert metadata for a file."""
        with get_session() as session:
            f = session.execute(select(File).where(File.path == path)).scalar_one_or_none()
            
            current_notes = json.loads(f.notes_json) if f and f.notes_json else {}
            if notes:
                current_notes.update(notes)
                
            if f:
                # Update existing
                f.ticker = ticker
                if category is not None: f.category = category
                if year is not None: f.year = year
                if quarter is not None: f.quarter = quarter
                if status is not None: f.status = status
                if language is not None: f.language = language
                if last_page_read is not None: f.last_page_read = last_page_read
                if last_accessed is not None: f.last_accessed = last_accessed
                f.notes_json = json.dumps(current_notes)
            else:
                # Insert new
                new_file = File(
                    path=path,
                    ticker=ticker,
                    category=category,
                    year=year,
                    quarter=quarter,
                    status=status if status is not None else 0,
                    language=language if language else 'EN',
                    notes_json=json.dumps(notes if notes else {}),
                    last_page_read=last_page_read if last_page_read else 0,
                    last_accessed=last_accessed
                )
                session.add(new_file)
                
            session.commit()

    def get_smart_resume_doc(self, ticker):
        """
        Waterfall Logic for Smart Resume:
        1. In Progress (status=1) ordered by last_accessed DESC
        2. Unread Tier 1 (Annual Reports, Transcript) ordered by Year DESC
        3. Excel/Thesis
        """
        with get_session() as session:
            # 1. Priority A: In Progress
            res = session.execute(
                select(File.path)
                .where(File.ticker == ticker, File.status == 1)
                .order_by(File.last_accessed.desc())
                .limit(1)
            ).scalar()
            if res:
                return res
                
            # 2. Priority B: Unread Tier 1
            res = session.execute(
                select(File.path)
                .where(File.ticker == ticker, File.status == 0, File.category.in_(['Annual Reports', 'Transcript']))
                .order_by(File.year.desc(), File.path.asc())
                .limit(1)
            ).scalar()
            if res:
                return res
                
            # 3. Priority C: Excel
            res = session.execute(
                select(File.path)
                .where(File.ticker == ticker, File.category == 'Excel')
                .limit(1)
            ).scalar()
            return res

    def get_company_progress(self, ticker):
        """
        Calculate composite progress score (0-100%) based on Legend:
        - 15% Files (Depth: 5 AR + 5 Transcripts)
        - 35% Reading (Weighted completion)
        - 30% Time (Target: 30 hours)
        - 20% Deliverables (Excel + Thesis)
        """
        with get_session() as session:
            rows = session.execute(
                select(File.category, File.status, File.path).where(File.ticker == ticker)
            ).all()
            
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
        score_ar = min(count_ar, 5) / 5.0
        score_trans = min(count_trans, 5) / 5.0
        score_files = ((score_ar + score_trans) / 2.0) * 15.0
        
        # Score B: Reading (35%)
        score_reading = 0
        if reading_points_total > 0:
            score_reading = (reading_points_earned / reading_points_total) * 35.0
            
        # Score C: Time (30%)
        hours = self.get_company_hours(ticker)
        score_time = min(hours / 30.0, 1.0) * 30.0
        
        # Score D: Deliverables (20%)
        score_deliv = 0
        if has_excel: score_deliv += 10
        if has_thesis: score_deliv += 10
        
        total_pct = score_files + score_reading + score_time + score_deliv
        
        # Detailed Stats for Tooltips
        stats = {
            "count_ar": count_ar,
            "count_trans": count_trans,
            "has_excel": True if has_excel else False,
            "has_thesis": True if has_thesis else False,
            "hours": round(hours, 1),
            "score_files": score_files,
            "score_reading": score_reading,
            "progress_percent": int(total_pct)
        }
        
        return int(total_pct), stats

    def check_duplicates(self, ticker, year, category):
        """Check for potential duplicates (same ticker, year, category)."""
        if category not in ["Annual Reports"]:
            return []
            
        with get_session() as session:
            rows = session.execute(
                select(File.path).where(File.ticker == ticker, File.year == year, File.category == category)
            ).scalars().all()
            
        return rows if len(rows) > 1 else []

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
