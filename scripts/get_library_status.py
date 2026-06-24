import sqlite3
import json
import os
import sys

# Single source of truth for the database path resolved dynamically
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
try:
    from config import MAIN_DB
    db_path = str(MAIN_DB)
except ImportError:
    db_path = r"D:\01_PROJECT_CODE\EKKOMONOS\src\db\fortress_vault.db"

def get_library_status():
    if not os.path.exists(db_path):
        return {"error": "Database not found"}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Fetch companies
        cursor.execute("SELECT ticker, name, category, status, aliases FROM companies")
        companies = []
        for row in cursor.fetchall():
            companies.append({
                "ticker": row[0],
                "name": row[1],
                "category": row[2],
                "status": row[3],
                "aliases": [a.strip() for a in row[4].split(",")] if row[4] else []
            })

        # 2. Fetch special situations
        cursor.execute("SELECT id, title, tickers, status, folder_path FROM special_situations")
        specials = []
        for row in cursor.fetchall():
            tickers_json = row[2]
            tickers_list = []
            if tickers_json:
                try:
                    t_dict = json.loads(tickers_json)
                    if isinstance(t_dict, dict):
                        tickers_list = [v.strip() for v in t_dict.values() if v and v.strip()]
                    elif isinstance(t_dict, list):
                        tickers_list = [v.strip() for v in t_dict if v and v.strip()]
                except Exception:
                    pass
            
            specials.append({
                "id": row[0],
                "title": row[1],
                "tickers": tickers_list,
                "status": row[3],
                "folder_path": row[4]
            })

        # 3. Fetch library files
        cursor.execute("SELECT path, ticker, category, year, language FROM files")
        files = []
        for row in cursor.fetchall():
            files.append({
                "path": row[0],
                "ticker": row[1],
                "category": row[2],
                "year": row[3],
                "language": row[4],
                "filename": os.path.basename(row[0])
            })

        conn.close()

        return {
            "companies": companies,
            "special_situations": specials,
            "files": files
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    status = get_library_status()
    print(json.dumps(status))
