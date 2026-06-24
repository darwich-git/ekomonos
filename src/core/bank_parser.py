import pandas as pd
import csv
import logging
from typing import Dict, Any

def try_read_bos_csv(file_path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        try:
            return pd.read_csv(file_path, encoding='latin1')
        except Exception as e:
            logging.error(f"Failed to read CSV with latin1: {e}")
            return pd.DataFrame()
    except Exception as e:
        logging.error(f"Failed to read CSV with utf-8: {e}")
        return pd.DataFrame()

def analyze_bos_rafa(file_path: str) -> Dict[str, float]:
    """Analyzes Rafa's Bank of Scotland CSV"""
    df = try_read_bos_csv(file_path)
    
    metrics = {
        "ingresos_brutos": 0.0,
        "ingresos_netos": 0.0,
        "gastos_individuales": 0.0,
        "cuota_familia": 0.0,
        "dinero_enviado_ibkr": 0.0,
        "master_balance": 0.0
    }
    
    result = {"metrics": metrics, "transactions": []}
    
    if "Transaction Description" not in df.columns or "Credit Amount" not in df.columns:
        return result
        
    # Get last balance
    if "Balance" in df.columns and not df.empty:
        try:
            # We take the first non-null balance in case it's sorted descending or ascending
            bals = df["Balance"].dropna()
            if not bals.empty:
                result["metrics"]["master_balance"] = float(bals.iloc[0]) # usually balance is at index 0 because CSVs export newest first. Or maybe last. We'll let user check.
        except: pass

    for _, row in df.iterrows():
        desc = str(row.get("Transaction Description", "")).lower()
        debit = row.get("Debit Amount", 0.0)
        credit = row.get("Credit Amount", 0.0)
        
        if pd.isna(debit): debit = 0.0
        if pd.isna(credit): credit = 0.0
        
        cat = "Ignored"
        # Incomes
        if credit > 0:
            if "c catalan" in desc or "cris" in desc:
                cat = "Transfer (Ignored)"
            else:
                cat = "Ingreso Neto"
                
        # Debits
        if debit > 0:
            if "interactive" in desc or "ibkr" in desc:
                # By default assume Rafa IBKR, but user can change it
                cat = "Inversion: Rafa IBKR"
            elif "cuenta comun" in desc or "family" in desc or "scotia" in desc or "catalan" in desc or "darwich" in desc:
                cat = "Cuota a Familia (Traspaso)" 
            elif "fundsmith" in desc:
                cat = "Inversion: Rafa Fundsmith"
            else:
                cat = "Gastos Variables: Otros" # Let the user classify
                
        result["transactions"].append({
            "date": str(row.get("Transaction Date", "")),
            "desc": str(row.get("Transaction Description", "")),
            "debit": debit,
            "credit": credit,
            "category": cat
        })

    return result

def analyze_ibkr(file_path: str) -> Dict[str, float]:
    """Analyzes Interactive Brokers CSV for Deposits and Profit/Total"""
    metrics = {
        "aportado": 0.0,
        "profit": 0.0,
        "total": 0.0
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row: continue
                # Find deposit total
                if len(row) >= 4 and row[0].startswith('Deposits & Withdrawals') and row[1] == 'Data' and row[2] == 'Total':
                    try:
                        vals = [x for x in row if x.strip()]
                        if vals:
                            metrics["aportado"] = float(vals[-1].replace(',', ''))
                    except: pass
                
                # Find Total Nav from Account Summary
                if len(row) >= 7 and row[0] == 'Account Summary' and row[1] == 'Data' and row[2] == 'Total':
                    try:
                        # Current NAV is typically at index 7, but let's grab the second to last value to be safe if there are trailing commas 
                        vals = [x for x in row if x.strip()]
                        if len(vals) >= 4:
                            # Depending on the layout "Prior NAV, Current NAV"
                            # If `vals` is ['Account Summary', 'Data', 'Total', '122220.02', '134018.60'] -> last is Current Nav
                            metrics["total"] = float(vals[-1].replace(',', ''))
                    except: pass
    except:
        pass
        
    return metrics

def analyze_bos_comun(file_path: str) -> Dict[str, float]:
    """Analyzes the Joint Bank of Scotland CSV"""
    df = try_read_bos_csv(file_path)
    
    metrics = {
        "ingresos_comun": 0.0,
        "gastos_comun": 0.0,
        "hipoteca": 0.0,
        "master_balance": 0.0
    }
    
    result = {"metrics": metrics, "transactions": []}
    
    if "Transaction Description" not in df.columns:
        return result
        
    if "Balance" in df.columns and not df.empty:
        try:
            bals = df["Balance"].dropna()
            if not bals.empty: result["metrics"]["master_balance"] = float(bals.iloc[0])
        except: pass

    for _, row in df.iterrows():
        desc = str(row.get("Transaction Description", "")).lower()
        debit = row.get("Debit Amount", 0.0)
        credit = row.get("Credit Amount", 0.0)
        
        if pd.isna(debit): debit = 0.0
        if pd.isna(credit): credit = 0.0
        
        cat = "Ignored"
        # Incomes (Quotas)
        if credit > 0:
            if "r darwich" in desc or "c catalan" in desc or "rafa" in desc or "cris" in desc:
                cat = "Aportacion de Socio"
            else:
                cat = "Ingreso Extra Comun"
                
        # Debits
        if debit > 0:
            if "natwest" in desc or "mortgage" in desc or "hipoteca" in desc:
                cat = "Gastos Fijos: Hipoteca/Alquiler"
            elif "e.on" in desc or "council" in desc:
                cat = "Gastos Fijos: Casa/Facturas"
            elif "manypets" in desc or "admiral" in desc:
                cat = "Gastos Fijos: Seguros"
            elif "aldi" in desc or "lidl" in desc or "asda" in desc or "tesco" in desc or "pou" in desc or "sainsbury" in desc:
                cat = "Gastos Variables: Supermercado"
            elif "lothian" in desc or "tram" in desc or "train" in desc or "fuel" in desc:
                cat = "Gastos Variables: Transporte"
            else:
                cat = "Gastos Variables: Otros"
                
        result["transactions"].append({
            "date": str(row.get("Transaction Date", "")),
            "desc": str(row.get("Transaction Description", "")),
            "debit": debit,
            "credit": credit,
            "category": cat
        })
                
    return result
