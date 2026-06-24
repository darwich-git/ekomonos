"""
migrate_ss_v2.py
Fase 0 — Special Situations V2
Migra las situaciones existentes añadiendo los campos nuevos con defaults seguros.
Hace backup de la BD ANTES de modificar.
Ejecutar UNA SOLA VEZ antes de implementar el resto de fases.
"""
import sys
import os
import shutil
import json
from datetime import datetime

# Asegurar que el path raíz del proyecto esté en sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.database import init_db, get_session_factory, SpecialSituation

DB_PATH = os.path.join(ROOT, "db", "fortress_vault.db")
BACKUP_PATH = os.path.join(ROOT, "db", f"fortress_vault_BACKUP_SS_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")

# Campos nuevos con sus valores por defecto seguros
NEW_FIELDS_DEFAULTS = {
    "close_probability":  90,       # % (0-100), usamos 90 como default Hielco
    "outside_date":       None,     # Fecha límite del deal
    "break_fee_pct":      0.0,      # % sobre el precio de oferta
    "downside_price":     0.0,      # Precio de caída si no hay deal
    "reinforce_price":    0.0,      # Umbral de compra (para F2)
    "reduce_price":       0.0,      # Umbral de venta (para F2)
    "checklist_global":   {},       # {key: {checked: bool, notes: str}}
    "checklist_specific": {},       # {key: {checked: bool, notes: str}}
    "scenario_bear":      {"price": 0.0, "prob": 20},   # Escenario pesimista
    "scenario_base":      {"price": 0.0, "prob": 65},   # Escenario base
    "scenario_bull":      {"price": 0.0, "prob": 15},   # Escenario optimista
    "files_metadata":     [],       # Lista de {name, category, date, read, url}
    "xirr_cashflows":     [],       # Para Liquidaciones: [{date, amount}]
}


def backup_db():
    """Crea una copia de seguridad de la BD antes de modificar."""
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] No se encontró la BD en: {DB_PATH}")
        return False
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"[BACKUP] BD copiada a: {BACKUP_PATH}")
    return True


def migrate():
    print("=" * 60)
    print("  Special Situations V2 — Migración de Datos")
    print("=" * 60)

    # 1. Backup
    if not backup_db():
        print("[ABORT] No se puede continuar sin backup.")
        return False

    # 2. Conectar a la BD
    engine = init_db(DB_PATH)
    Session = get_session_factory(engine)
    session = Session()

    try:
        situations = session.query(SpecialSituation).all()
        count = len(situations)
        print(f"\n[INFO] Encontradas {count} situaciones especiales.\n")

        for s in situations:
            print(f"  Procesando: {s.title} ({s.id[:8]}...)")

            # Cargar specific_data existente
            try:
                specific = json.loads(s.specific_data) if s.specific_data else {}
            except json.JSONDecodeError:
                specific = {}
                print(f"    [WARN] specific_data inválido, inicializando vacío.")

            # Añadir solo los campos que NO existen ya (sin sobreescribir)
            added_fields = []
            for field, default_val in NEW_FIELDS_DEFAULTS.items():
                if field not in specific:
                    specific[field] = default_val
                    added_fields.append(field)

            if added_fields:
                print(f"    [ADD] Campos nuevos: {', '.join(added_fields)}")
            else:
                print(f"    [OK] Ya tenía todos los campos nuevos.")

            # Guardar de vuelta
            s.specific_data = json.dumps(specific, ensure_ascii=False)

        session.commit()
        print(f"\n[OK] Migración completada. {count} situaciones actualizadas.")
        print(f"[BACKUP] Si algo es incorrecto, restaura desde: {BACKUP_PATH}")
        return True

    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] Fallo durante la migración: {e}")
        import traceback
        traceback.print_exc()
        print(f"[ROLLBACK] Los cambios han sido revertidos.")
        print(f"[BACKUP] La BD original sigue intacta en: {BACKUP_PATH}")
        return False
    finally:
        session.close()


def verify():
    """Verifica que la migración fue correcta leyendo los datos."""
    print("\n" + "=" * 60)
    print("  Verificación post-migración")
    print("=" * 60)

    engine = init_db(DB_PATH)
    Session = get_session_factory(engine)
    session = Session()

    try:
        situations = session.query(SpecialSituation).all()
        all_ok = True
        for s in situations:
            try:
                specific = json.loads(s.specific_data)
            except:
                specific = {}

            missing = [f for f in NEW_FIELDS_DEFAULTS if f not in specific]
            if missing:
                print(f"  [FAIL] {s.title}: faltan campos: {missing}")
                all_ok = False
            else:
                close_prob = specific.get('close_probability', '?')
                print(f"  [OK]   {s.title}")
                print(f"         close_probability={close_prob}%, "
                      f"checklist_global={len(specific.get('checklist_global', {}))}/10 marcados")

        if all_ok:
            print("\n[ALL OK] Todas las situaciones tienen los campos nuevos correctamente.")
        else:
            print("\n[ERRORS] Algunas situaciones tienen problemas. Revisar arriba.")
        return all_ok
    finally:
        session.close()


if __name__ == "__main__":
    success = migrate()
    if success:
        verify()
    else:
        print("\n[ABORT] La migración falló. No se han modificado datos.")
        sys.exit(1)
