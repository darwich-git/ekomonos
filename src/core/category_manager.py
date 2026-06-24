import json
import os

CATEGORIES_FILE = "custom_categories.json"

DEFAULT_CATEGORIES = {
    "11": "Ingreso Neto (Nómina)",
    "12": "Ingreso Extra",
    "13": "Aportacion de Socio Comun",
    "2": "Cuota a Familia (Traspaso)",
    "3": "Transferencia / Ignorado",
    "0": "Ignorado",
    "41": "Inversion: Rafa IBKR",
    "42": "Inversion: Rafa Fundsmith",
    "43": "Inversion: Cris IBKR",
    "44": "Inversion: Cris Fondo Monetario",
    "45": "Inversion: Cris Fundsmith",
    "51": "Gastos Fijos: Hipoteca/Alquiler",
    "52": "Gastos Fijos: Casa/Facturas",
    "53": "Gastos Fijos: Seguros",
    "54": "Gastos Fijos: Suscripciones",
    "61": "Gastos Variables: Supermercado",
    "62": "Gastos Variables: Transporte",
    "63": "Gastos Variables: Ocio/Restaurantes",
    "64": "Gastos Variables: Ropa/Vestimenta",
    "65": "Gastos Variables: Viajes",
    "66": "Gastos Variables: Salud",
    "67": "Gastos Variables: Educacion",
    "68": "Gastos Variables: Otros",
    "69": "Gastos Variables: Amazon"
}

def get_categories():
    if os.path.exists(CATEGORIES_FILE):
        try:
            with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                if loaded:
                    return loaded
        except Exception:
            pass
    return DEFAULT_CATEGORIES.copy()

def save_categories(cats_dict):
    with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(cats_dict, f, ensure_ascii=False, indent=4)
