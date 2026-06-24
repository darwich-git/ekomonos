"""
Objectives Manager — F12 Objetivos Anuales
Handles all data persistence and business logic for the OKR system.
Uses SQLite via direct sqlite3 (separate from main SQLAlchemy DB to avoid migrations hell).

v2 additions:
  - El Peaje de Ejecución (Type A / Type B tasks)
  - El Estado Gris (stale detection, -20% health penalty)
  - El Seguro contra el Error (investment loss + lección aprendida)
  - Backlog module (dump, prioritize max-3-today, link to objective)
  - Seed data for 5 objectives of 2026
"""

import sqlite3
import json
import os
import math
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from config import MAIN_DB

# Use a dedicated DB for objectives (avoids SQLAlchemy migration issues)
OBJECTIVES_DB_PATH = str(MAIN_DB.parent / "objectives.db")

MAX_OBJECTIVES = 5
MAX_TODAY_TASKS = 3            # Backlog: max tasks moveable to "Today"

METRIC_TYPES = ["Currency €", "Currency £", "Percentage %", "Number", "Boolean"]
OBJ_TYPES = ["Committed", "Aspirational"]
TASK_TYPES = ["Tipo A — Estudio/Meta-trabajo", "Tipo B — Ejecución Física"]
HEALTH_GREEN = 0.90
HEALTH_YELLOW = 0.70
STALE_DAYS = 7                 # Days without update → grey state
GREY_HEALTH_PENALTY = 0.20    # 20% global health score penalty per grey objective


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(OBJECTIVES_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_objectives_db():
    """Create all tables if they don't exist. Uses IF NOT EXISTS for safe re-runs."""
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS objectives (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            year        INTEGER NOT NULL,
            title       TEXT    NOT NULL,
            purpose     TEXT,
            is_the_one_thing INTEGER DEFAULT 0,
            obj_type    TEXT    DEFAULT 'Committed',
            status      TEXT    DEFAULT 'Active',
            metric_type TEXT    DEFAULT 'Number',
            target_value REAL   DEFAULT 0,
            target_locked INTEGER DEFAULT 0,
            color       TEXT    DEFAULT '#FF9800',
            lessons_learned TEXT,
            created_at  TEXT    DEFAULT (datetime('now')),
            archived_at TEXT
        );

        CREATE TABLE IF NOT EXISTS key_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            objective_id    INTEGER NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
            title           TEXT NOT NULL,
            metric_type     TEXT DEFAULT 'Number',
            target_value    REAL DEFAULT 0,
            current_value   REAL DEFAULT 0,
            weight          REAL DEFAULT 1.0,
            last_updated    TEXT DEFAULT (datetime('now')),
            UNIQUE(objective_id, title)
        );

        CREATE TABLE IF NOT EXISTS progress_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            key_result_id   INTEGER NOT NULL REFERENCES key_results(id) ON DELETE CASCADE,
            value           REAL NOT NULL,
            note            TEXT,
            logged_at       TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS objective_actions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            objective_id    INTEGER NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
            level           TEXT NOT NULL,
            title           TEXT NOT NULL,
            task_type       TEXT DEFAULT 'Tipo B — Ejecución Física',
            period_label    TEXT,
            is_done         INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS block_notes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            objective_id    INTEGER NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
            note            TEXT NOT NULL,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS if_then_plans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            objective_id    INTEGER NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
            trigger_text    TEXT NOT NULL,
            action_text     TEXT NOT NULL
        );

        -- ── BACKLOG ──────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS backlog_tasks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            objective_id    INTEGER REFERENCES objectives(id) ON DELETE SET NULL,
            title           TEXT NOT NULL,
            task_type       TEXT DEFAULT 'Tipo B — Ejecución Física',
            is_today        INTEGER DEFAULT 0,
            is_done         INTEGER DEFAULT 0,
            priority        INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now')),
            done_at         TEXT
        );

        -- ── INVESTMENT LOSSES (El Seguro contra el Error) ────────────────────
        CREATE TABLE IF NOT EXISTS investment_lessons (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            objective_id    INTEGER REFERENCES objectives(id) ON DELETE SET NULL,
            ticker          TEXT,
            loss_amount     REAL DEFAULT 0,
            currency        TEXT DEFAULT 'EUR',
            lesson_text     TEXT NOT NULL,
            category        TEXT DEFAULT 'Costo de Formación',
            logged_at       TEXT DEFAULT (datetime('now'))
        );
    """)

    # Migrations: add columns that may not exist in older DB files
    _safe_add_column(c, "key_results",        "last_updated",  "TEXT DEFAULT (datetime('now'))")
    _safe_add_column(c, "objective_actions",  "task_type",     "TEXT DEFAULT 'Tipo B — Ejecución Física'")

    conn.commit()
    conn.close()


def _safe_add_column(cursor, table: str, column: str, col_def: str):
    """Add a column only if it doesn't exist (SQLite has no IF NOT EXISTS for ALTER)."""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
    except sqlite3.OperationalError:
        pass  # Column already exists


# ─── Seed Data ─────────────────────────────────────────────────────────────────

SEED_OBJECTIVES_2026 = [
    {
        "title": "Inversor de Convicción",
        "purpose": "100% de nuevas posiciones con tesis propia. Cero copias de clase. Llegar a Guadalajara siendo el inversor que sé que soy.",
        "is_the_one_thing": True,
        "obj_type": "Committed",
        "metric_type": "Number",
        "target_value": 12,
        "color": "#FFD700",
    },
    {
        "title": "Hardware 99kg",
        "purpose": "Alcanzar los 99.9 kg antes del 31 de diciembre. El cuerpo es la máquina más importante.",
        "is_the_one_thing": False,
        "obj_type": "Committed",
        "metric_type": "Number",
        "target_value": 99.9,
        "color": "#E74C3C",
    },
    {
        "title": "El Nido (Agosto 5)",
        "purpose": "Casa y habitación del bebé 100% terminadas para el 15 de julio. Lo más importante de 2026.",
        "is_the_one_thing": False,
        "obj_type": "Committed",
        "metric_type": "Percentage %",
        "target_value": 100,
        "color": "#3498DB",
    },
    {
        "title": "Foco Digital",
        "purpose": "Cero divagación en PC (YouTube/IA) hasta completar la tarea del día. La atención es el activo más escaso.",
        "is_the_one_thing": False,
        "obj_type": "Aspirational",
        "metric_type": "Number",
        "target_value": 200,
        "color": "#9B59B6",
    },
    {
        "title": "Hábito de Lectura",
        "purpose": "20 minutos diarios de lectura física. Biografías, Historia, Inversión. La mente que no crece, se encoge.",
        "is_the_one_thing": False,
        "obj_type": "Aspirational",
        "metric_type": "Number",
        "target_value": 200,
        "color": "#27AE60",
    },
]

SEED_KEY_RESULTS_2026 = {
    "Inversor de Convicción": [
        {"title": "Tesis documentadas publicadas",      "metric_type": "Number",   "target_value": 12,    "weight": 2.0},
        {"title": "Nuevas posiciones sin tesis propia", "metric_type": "Number",   "target_value": 0,     "weight": 1.0},
        {"title": "Balance sheets analizados",          "metric_type": "Number",   "target_value": 24,    "weight": 1.0},
    ],
    "Hardware 99kg": [
        {"title": "Peso actual (kg)",                   "metric_type": "Number",   "target_value": 99.9,  "weight": 3.0},
        {"title": "Sesiones de gym por semana",         "metric_type": "Number",   "target_value": 156,   "weight": 1.0},
    ],
    "El Nido (Agosto 5)": [
        {"title": "% avance habitación bebé",           "metric_type": "Percentage %", "target_value": 100, "weight": 2.0},
        {"title": "% avance zonas comunes",             "metric_type": "Percentage %", "target_value": 100, "weight": 1.0},
        {"title": "Lista compras/pendientes completada","metric_type": "Boolean",   "target_value": 1,     "weight": 1.0},
    ],
    "Foco Digital": [
        {"title": "Días de Foco Total cumplidos",       "metric_type": "Number",   "target_value": 200,   "weight": 2.0},
        {"title": "Días con YouTube antes de tarea",    "metric_type": "Number",   "target_value": 0,     "weight": 1.0},
    ],
    "Hábito de Lectura": [
        {"title": "Sesiones de lectura completadas",    "metric_type": "Number",   "target_value": 200,   "weight": 2.0},
        {"title": "Libros terminados en el año",        "metric_type": "Number",   "target_value": 6,     "weight": 1.0},
    ],
}

SEED_IF_THEN_2026 = {
    "Inversor de Convicción": [
        {"trigger": "si tengo solo 30 min libres",
         "action": "entonces leo un solo ratio del balance sheet y lo anoto"},
        {"trigger": "si quiero copiar una idea de otro inversor",
         "action": "entonces espero 48h y escribo mi propia tesis primero"},
    ],
    "Hardware 99kg": [
        {"trigger": "si estoy cansado después de la planta",
         "action": "entonces voy al gym solo 20 min (mínimo viable)"},
        {"trigger": "si tengo tentación de saltarme el gym",
         "action": "entonces me pongo las zapatillas primero — el resto es automático"},
    ],
    "El Nido (Agosto 5)": [
        {"trigger": "si la tarea de la habitación parece enorme",
         "action": "entonces elijo un solo microtarea de 15 min y la hago YA"},
    ],
    "Foco Digital": [
        {"trigger": "si siento el impulso de abrir YouTube antes de terminar",
         "action": "entonces cierro el navegador y escribo qué me está bloqueando"},
    ],
    "Hábito de Lectura": [
        {"trigger": "si estoy muy cansado para leer",
         "action": "entonces leo solo 2 páginas — el hábito importa más que la cantidad"},
        {"trigger": "si no tengo el libro a mano",
         "action": "entonces lo pongo encima del teclado antes de acostarme"},
    ],
}


def seed_2026_objectives():
    """Insert the 5 predefined 2026 objectives if none exist for that year."""
    conn = get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM objectives WHERE year=2026"
    ).fetchone()[0]
    conn.close()
    if count > 0:
        return  # Already seeded

    # Insert each
    for seed in SEED_OBJECTIVES_2026:
        obj_id = add_objective(
            year=2026,
            title=seed["title"],
            purpose=seed["purpose"],
            obj_type=seed["obj_type"],
            metric_type=seed["metric_type"],
            target_value=seed["target_value"],
            is_the_one_thing=seed["is_the_one_thing"],
            color=seed["color"],
        )
        # Add KRs
        for kr in SEED_KEY_RESULTS_2026.get(seed["title"], []):
            add_key_result(obj_id, kr["title"], kr["metric_type"],
                           kr["target_value"], kr["weight"])
        # Add if-then plans
        for plan in SEED_IF_THEN_2026.get(seed["title"], []):
            add_if_then_plan(obj_id, plan["trigger"], plan["action"])


# ─── Objectives ────────────────────────────────────────────────────────────────

def get_objectives(year: int) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM objectives WHERE year=? AND status='Active' ORDER BY is_the_one_thing DESC, id ASC",
        (year,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_years() -> List[int]:
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT year FROM objectives ORDER BY year DESC").fetchall()
    conn.close()
    return [r[0] for r in rows]


def add_objective(year: int, title: str, purpose: str, obj_type: str,
                  metric_type: str, target_value: float,
                  is_the_one_thing: bool = False, color: str = '#FF9800') -> int:
    conn = get_conn()
    c = conn.cursor()
    count = conn.execute(
        "SELECT COUNT(*) FROM objectives WHERE year=? AND status='Active'", (year,)
    ).fetchone()[0]
    if count >= MAX_OBJECTIVES:
        conn.close()
        raise ValueError(f"Máximo de {MAX_OBJECTIVES} objetivos activos por año alcanzado.")
    if is_the_one_thing:
        conn.execute("UPDATE objectives SET is_the_one_thing=0 WHERE year=?", (year,))
    c.execute("""
        INSERT INTO objectives (year, title, purpose, obj_type, metric_type, target_value, target_locked, is_the_one_thing, color)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
    """, (year, title, purpose, obj_type, metric_type, target_value, int(is_the_one_thing), color))
    obj_id = c.lastrowid
    conn.commit()
    conn.close()
    return obj_id


def update_objective_meta(obj_id: int, title: str, purpose: str, obj_type: str,
                           is_the_one_thing: bool, color: str, lessons_learned: str = ""):
    conn = get_conn()
    year = conn.execute("SELECT year FROM objectives WHERE id=?", (obj_id,)).fetchone()
    if not year:
        conn.close()
        return
    year = year[0]
    if is_the_one_thing:
        conn.execute("UPDATE objectives SET is_the_one_thing=0 WHERE year=?", (year,))
    conn.execute("""
        UPDATE objectives SET title=?, purpose=?, obj_type=?, is_the_one_thing=?, color=?, lessons_learned=?
        WHERE id=?
    """, (title, purpose, obj_type, int(is_the_one_thing), color, lessons_learned, obj_id))
    conn.commit()
    conn.close()


def archive_objective(obj_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE objectives SET status='Archived', archived_at=datetime('now') WHERE id=?",
        (obj_id,)
    )
    conn.commit()
    conn.close()


def delete_objective(obj_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM objectives WHERE id=?", (obj_id,))
    conn.commit()
    conn.close()


# ─── Key Results ───────────────────────────────────────────────────────────────

def get_key_results(objective_id: int) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM key_results WHERE objective_id=? ORDER BY id ASC",
        (objective_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_key_result(objective_id: int, title: str, metric_type: str,
                   target_value: float, weight: float = 1.0) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO key_results (objective_id, title, metric_type, target_value, weight)
        VALUES (?, ?, ?, ?, ?)
    """, (objective_id, title, metric_type, target_value, weight))
    conn.commit()
    kr_id = c.lastrowid
    conn.close()
    return kr_id


def update_kr_value(kr_id: int, new_value: float, note: str = ""):
    """Update current_value of a KR and log it. Also updates last_updated."""
    conn = get_conn()
    conn.execute(
        "UPDATE key_results SET current_value=?, last_updated=datetime('now') WHERE id=?",
        (new_value, kr_id)
    )
    conn.execute(
        "INSERT INTO progress_logs (key_result_id, value, note) VALUES (?, ?, ?)",
        (kr_id, new_value, note)
    )
    conn.commit()
    conn.close()


def delete_key_result(kr_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM key_results WHERE id=?", (kr_id,))
    conn.commit()
    conn.close()


def get_progress_logs(kr_id: int) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM progress_logs WHERE key_result_id=? ORDER BY logged_at ASC",
        (kr_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_days_since_last_update(objective_id: int) -> int:
    """Return number of days since any KR of this objective was last updated."""
    conn = get_conn()
    row = conn.execute(
        "SELECT MAX(last_updated) FROM key_results WHERE objective_id=?",
        (objective_id,)
    ).fetchone()
    conn.close()
    if not row or not row[0]:
        return 9999  # Never updated → definitely stale
    try:
        last = datetime.strptime(row[0][:19], "%Y-%m-%d %H:%M:%S").date()
        return (date.today() - last).days
    except Exception:
        return 9999


def is_objective_stale(objective_id: int) -> bool:
    return get_days_since_last_update(objective_id) >= STALE_DAYS


# ─── El Peaje de Ejecución ─────────────────────────────────────────────────────

def has_type_b_done_today(objective_id: int) -> bool:
    """Return True if at least one Tipo B action was completed today for this objective."""
    today_str = date.today().isoformat()
    conn = get_conn()
    count = conn.execute("""
        SELECT COUNT(*) FROM objective_actions
        WHERE objective_id=?
          AND task_type LIKE 'Tipo B%'
          AND is_done=1
          AND DATE(created_at) = ?
    """, (objective_id, today_str)).fetchone()[0]
    # Also check backlog
    count2 = conn.execute("""
        SELECT COUNT(*) FROM backlog_tasks
        WHERE objective_id=?
          AND task_type LIKE 'Tipo B%'
          AND is_done=1
          AND DATE(done_at) = ?
    """, (objective_id, today_str)).fetchone()[0]
    conn.close()
    return (count + count2) > 0


# ─── Actions ──────────────────────────────────────────────────────────────────

def get_actions(objective_id: int, level: Optional[str] = None) -> List[Dict]:
    conn = get_conn()
    if level:
        rows = conn.execute(
            "SELECT * FROM objective_actions WHERE objective_id=? AND level=? ORDER BY id ASC",
            (objective_id, level)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM objective_actions WHERE objective_id=? ORDER BY level, id ASC",
            (objective_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_action(objective_id: int, level: str, title: str, period_label: str = "",
               task_type: str = "Tipo B — Ejecución Física") -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO objective_actions (objective_id, level, title, period_label, task_type)
        VALUES (?, ?, ?, ?, ?)
    """, (objective_id, level, title, period_label, task_type))
    conn.commit()
    action_id = c.lastrowid
    conn.close()
    return action_id


def toggle_action(action_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE objective_actions SET is_done = 1 - is_done WHERE id=?",
        (action_id,)
    )
    conn.commit()
    conn.close()


def delete_action(action_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM objective_actions WHERE id=?", (action_id,))
    conn.commit()
    conn.close()


# ─── Block Notes ───────────────────────────────────────────────────────────────

def get_block_notes(objective_id: int) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM block_notes WHERE objective_id=? ORDER BY created_at DESC",
        (objective_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_block_note(objective_id: int, note: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO block_notes (objective_id, note) VALUES (?, ?)",
        (objective_id, note)
    )
    conn.commit()
    conn.close()


# ─── If-Then Plans ─────────────────────────────────────────────────────────────

def get_if_then_plans(objective_id: int) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM if_then_plans WHERE objective_id=? ORDER BY id ASC",
        (objective_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_if_then_plan(objective_id: int, trigger_text: str, action_text: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO if_then_plans (objective_id, trigger_text, action_text) VALUES (?, ?, ?)",
        (objective_id, trigger_text, action_text)
    )
    conn.commit()
    plan_id = c.lastrowid
    conn.close()
    return plan_id


def delete_if_then_plan(plan_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM if_then_plans WHERE id=?", (plan_id,))
    conn.commit()
    conn.close()


# ─── Health Score ──────────────────────────────────────────────────────────────

def compute_health_score(objective: Dict, key_results: List[Dict],
                          apply_grey_penalty: bool = False) -> Dict:
    """
    Returns dict with:
      - overall_pct: 0.0–1.0 weighted progress
      - expected_pct: time-based expected progress
      - health: 'green' | 'yellow' | 'red' | 'grey' (stale)
      - is_stale: bool
      - days_stale: int
      - cost_per_day: float
      - remaining_days: int
      - is_celebratable: bool
    """
    if not key_results:
        overall_pct = 0.0
    else:
        total_weight = sum(kr['weight'] for kr in key_results)
        if total_weight == 0:
            overall_pct = 0.0
        else:
            weighted_sum = 0.0
            for kr in key_results:
                tv = kr['target_value']
                cv = kr['current_value']
                if kr['metric_type'] == 'Boolean':
                    pct = 1.0 if cv >= 1.0 else 0.0
                elif tv == 0:
                    pct = 1.0 if cv >= 1.0 else 0.0
                else:
                    pct = min(cv / tv, 1.0)
                weighted_sum += pct * kr['weight']
            overall_pct = weighted_sum / total_weight

    # Expected progress based on year position
    year = objective['year']
    today = date.today()
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    total_days = (end - start).days + 1
    elapsed = max(0, (today - start).days + 1)
    expected_pct = min(elapsed / total_days, 1.0)

    ratio = overall_pct / expected_pct if expected_pct > 0 else 0.0

    if ratio >= HEALTH_GREEN:
        health = 'green'
    elif ratio >= HEALTH_YELLOW:
        health = 'yellow'
    else:
        health = 'red'

    # Aspirational: celebrate at 70% at year end
    is_year_end = today >= end
    if objective.get('obj_type') == 'Aspirational' and is_year_end and overall_pct >= 0.70:
        health = 'green'

    # ── El Estado Gris ──────────────────────────────────────────────────────
    days_stale = get_days_since_last_update(objective['id'])
    is_stale = days_stale >= STALE_DAYS

    if is_stale:
        health = 'grey'
        if apply_grey_penalty:
            overall_pct = max(0, overall_pct - GREY_HEALTH_PENALTY)

    # Cost of inaction
    remaining_days = max(1, (end - today).days)
    needed = max(0, expected_pct - overall_pct)
    cost_per_day = needed / remaining_days if remaining_days > 0 else 0.0

    return {
        'overall_pct': overall_pct,
        'expected_pct': expected_pct,
        'health': health,
        'is_stale': is_stale,
        'days_stale': days_stale,
        'cost_per_day': cost_per_day,
        'remaining_days': remaining_days,
        'is_celebratable': (objective.get('obj_type') == 'Aspirational' and overall_pct >= 0.70),
    }


def compute_global_health(year: int) -> Dict:
    """Compute an aggregate health score for the year, applying grey penalties."""
    objectives = get_objectives(year)
    if not objectives:
        return {'global_pct': 0.0, 'grey_count': 0, 'penalty_applied': 0.0}

    total_pct = 0.0
    grey_count = 0
    for obj in objectives:
        krs = get_key_results(obj['id'])
        hd = compute_health_score(obj, krs, apply_grey_penalty=True)
        total_pct += hd['overall_pct']
        if hd['is_stale']:
            grey_count += 1

    global_pct = total_pct / len(objectives)
    penalty = grey_count * GREY_HEALTH_PENALTY

    return {
        'global_pct': global_pct,
        'grey_count': grey_count,
        'penalty_applied': penalty,
        'obj_count': len(objectives),
    }


# ─── Backlog ───────────────────────────────────────────────────────────────────

def get_backlog(show_done: bool = False) -> List[Dict]:
    conn = get_conn()
    if show_done:
        rows = conn.execute(
            "SELECT * FROM backlog_tasks ORDER BY is_today DESC, priority DESC, id DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM backlog_tasks WHERE is_done=0 ORDER BY is_today DESC, priority DESC, id DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_backlog_task(title: str, objective_id: Optional[int] = None,
                     task_type: str = "Tipo B — Ejecución Física") -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO backlog_tasks (title, objective_id, task_type) VALUES (?, ?, ?)",
        (title, objective_id, task_type)
    )
    conn.commit()
    task_id = c.lastrowid
    conn.close()
    return task_id


def set_backlog_today(task_id: int, is_today: bool):
    """Move a task to (or remove from) the Today list. Max 3 today tasks enforced."""
    conn = get_conn()
    if is_today:
        today_count = conn.execute(
            "SELECT COUNT(*) FROM backlog_tasks WHERE is_today=1 AND is_done=0"
        ).fetchone()[0]
        if today_count >= MAX_TODAY_TASKS:
            conn.close()
            raise ValueError(f"Máximo de {MAX_TODAY_TASKS} tareas para hoy. Termina una antes de añadir otra.")
    conn.execute("UPDATE backlog_tasks SET is_today=? WHERE id=?", (int(is_today), task_id))
    conn.commit()
    conn.close()


def complete_backlog_task(task_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE backlog_tasks SET is_done=1, is_today=0, done_at=datetime('now') WHERE id=?",
        (task_id,)
    )
    conn.commit()
    conn.close()


def delete_backlog_task(task_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM backlog_tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


def update_backlog_task_objective(task_id: int, objective_id: Optional[int]):
    conn = get_conn()
    conn.execute("UPDATE backlog_tasks SET objective_id=? WHERE id=?", (objective_id, task_id))
    conn.commit()
    conn.close()


def count_today_tasks() -> int:
    conn = get_conn()
    n = conn.execute(
        "SELECT COUNT(*) FROM backlog_tasks WHERE is_today=1 AND is_done=0"
    ).fetchone()[0]
    conn.close()
    return n


# ─── Investment Lessons (El Seguro contra el Error) ───────────────────────────

def add_investment_lesson(ticker: str, loss_amount: float, currency: str,
                           lesson_text: str, objective_id: Optional[int] = None) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO investment_lessons (objective_id, ticker, loss_amount, currency, lesson_text)
        VALUES (?, ?, ?, ?, ?)
    """, (objective_id, ticker, loss_amount, currency, lesson_text))
    conn.commit()
    lesson_id = c.lastrowid
    conn.close()
    return lesson_id


def get_investment_lessons(objective_id: Optional[int] = None) -> List[Dict]:
    conn = get_conn()
    if objective_id:
        rows = conn.execute(
            "SELECT * FROM investment_lessons WHERE objective_id=? ORDER BY logged_at DESC",
            (objective_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM investment_lessons ORDER BY logged_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Year-End Archive ──────────────────────────────────────────────────────────

def close_year(year: int):
    """Archive all active objectives for the given year."""
    conn = get_conn()
    conn.execute("""
        UPDATE objectives
        SET status='Archived', archived_at=datetime('now')
        WHERE year=? AND status='Active'
    """, (year,))
    conn.commit()
    conn.close()


def get_archived_objectives(year: int) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM objectives WHERE year=? AND status='Archived' ORDER BY is_the_one_thing DESC, id",
        (year,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Initialise ───────────────────────────────────────────────────────────────

# ─── App Settings (key/value store) ──────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    conn = get_conn()
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO app_settings(key, value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()


# ─── Daily Popup (once per day) ───────────────────────────────────────────────

def was_popup_shown_today() -> bool:
    last = get_setting("last_popup_date", "")
    return last == date.today().isoformat()


def mark_popup_shown():
    set_setting("last_popup_date", date.today().isoformat())


# ─── Daily Focus (ONE Thing of the day) ──────────────────────────────────────

def get_today_focus() -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM daily_focus WHERE date=?", (date.today().isoformat(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_today_focus(text: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO daily_focus(date, focus_text) VALUES(?,?) "
        "ON CONFLICT(date) DO UPDATE SET focus_text=excluded.focus_text",
        (date.today().isoformat(), text)
    )
    conn.commit()
    conn.close()


def get_recent_focuses(days: int = 14) -> List[Dict]:
    conn = get_conn()
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT * FROM daily_focus WHERE date >= ? ORDER BY date DESC",
        (since,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Monthly Review (simple status per objective per month) ───────────────────

def get_monthly_review(objective_id: int, month: str) -> Optional[Dict]:
    """month = 'YYYY-MM'"""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM monthly_review WHERE objective_id=? AND month=?",
        (objective_id, month)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_monthly_review(objective_id: int, month: str, status: str,
                         monthly_action: str, weekly_action: str = ""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO monthly_review(objective_id, month, status, monthly_action, weekly_action)
        VALUES(?,?,?,?,?)
        ON CONFLICT(objective_id, month)
        DO UPDATE SET status=excluded.status,
                      monthly_action=excluded.monthly_action,
                      weekly_action=excluded.weekly_action
    """, (objective_id, month, status, monthly_action, weekly_action))
    conn.commit()
    conn.close()


def get_all_monthly_reviews(month: str) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM monthly_review WHERE month=?", (month,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Books / Reading Tracker ──────────────────────────────────────────────────

def add_book(title: str, author: str = "", pages: int = 0,
             date_finished: str = "", notes: str = "") -> int:
    conn = get_conn()
    c = conn.cursor()
    df = date_finished or date.today().isoformat()
    c.execute(
        "INSERT INTO books_log(title, author, pages, date_finished, notes) VALUES(?,?,?,?,?)",
        (title, author, pages, df, notes)
    )
    conn.commit()
    book_id = c.lastrowid
    conn.close()
    return book_id


def get_books(year=None) -> List[Dict]:
    conn = get_conn()
    if year:
        rows = conn.execute(
            "SELECT * FROM books_log WHERE date_finished LIKE ? ORDER BY date_finished DESC",
            (f"{year}%",)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM books_log ORDER BY date_finished DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_book(book_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM books_log WHERE id=?", (book_id,))
    conn.commit()
    conn.close()


def get_reading_stats(year=None) -> Dict:
    """Returns total books, total pages, and average pages/day for the period."""
    books = get_books(year)
    total_books = len(books)
    total_pages = sum(b.get("pages", 0) for b in books)

    avg_pages_day = 0.0
    if books:
        first_date_str = min(b["date_finished"] for b in books if b.get("date_finished"))
        try:
            first_date = date.fromisoformat(first_date_str[:10])
            days_elapsed = max((date.today() - first_date).days, 1)
            avg_pages_day = round(total_pages / days_elapsed, 1)
        except Exception:
            pass

    daily_goal = int(get_setting("reading_daily_goal", "20"))

    return {
        "total_books": total_books,
        "total_pages": total_pages,
        "avg_pages_day": avg_pages_day,
        "daily_goal": daily_goal,
        "goal_pct": min(100, round(avg_pages_day / daily_goal * 100)) if daily_goal else 0,
    }


def set_reading_daily_goal(pages: int):
    set_setting("reading_daily_goal", str(pages))


# ─── Extended DB init (new tables for v3 simplified widget) ──────────────────

def _init_extended_tables():
    """Add v3 tables. Safe to call multiple times."""
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_focus (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL UNIQUE,
            focus_text  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS books_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            author          TEXT DEFAULT '',
            pages           INTEGER DEFAULT 0,
            date_finished   TEXT DEFAULT (date('now')),
            notes           TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS monthly_review (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            objective_id    INTEGER NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
            month           TEXT NOT NULL,
            status          TEXT DEFAULT 'yellow',
            monthly_action  TEXT DEFAULT '',
            weekly_action   TEXT DEFAULT '',
            UNIQUE(objective_id, month)
        );
    """)
    conn.commit()
    conn.close()


# ─── Initialise ───────────────────────────────────────────────────────────────
init_objectives_db()
_init_extended_tables()
seed_2026_objectives()
