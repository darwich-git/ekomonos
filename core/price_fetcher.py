

from typing import Dict, List, Optional
import time
import threading

# Mapping: Exchange Name -> Yahoo Suffix
# Users select "Frankfurt", we append ".DE"

# Mapping: Exchange Name -> Yahoo Suffix
EXCHANGE_SUFFIXES = {
    # --- AMERICAS ---
    "NYSE - New York Stock Exchange (USA)": "",
    "NASDAQ - National Association of Securities Dealers (USA)": "",
    "AMEX - American Stock Exchange (USA)": "",
    "OTC - Over-The-Counter (USA)": "", 
    "TSX - Toronto Stock Exchange (Canada)": ".TO",
    "TSX-V - TSX Venture Exchange (Canada)": ".V",
    "BMV - Bolsa Mexicana de Valores (Mexico)": ".MX",
    "B3 - Sao Paulo Stock Exchange (Brazil)": ".SA",
    "BCBA - Buenos Aires Stock Exchange (Argentina)": ".BA",
    "BCS - Santiago Stock Exchange (Chile)": ".SN",
    "BVC - Colombia Stock Exchange (Colombia)": ".CL",
    "BVL - Lima Stock Exchange (Peru)": ".LM",
    
    # --- EUROPE ---
    "LSE - London Stock Exchange (UK)": ".L",
    "FSE - Frankfurt Stock Exchange (Germany)": ".DE",
    "XETRA - Xetra (Germany)": ".DE",
    "EURONEXT - Amsterdam (Netherlands)": ".AS",
    "EURONEXT - Paris (France)": ".PA",
    "EURONEXT - Brussels (Belgium)": ".BR",
    "EURONEXT - Lisbon (Portugal)": ".LS",
    "EURONEXT - Dublin (Ireland)": ".IR",
    "BME - Madrid Stock Exchange (Spain)": ".MC",
    "MIL - Borsa Italiana (Italy)": ".MI",
    "SWX - SIX Swiss Exchange (Switzerland)": ".SW",
    "WSE - Warsaw Stock Exchange (Poland)": ".WA",
    "OMX - Stockholm Stock Exchange (Sweden)": ".ST",
    "OMX - Helsinki Stock Exchange (Finland)": ".HE",
    "OMX - Copenhagen Stock Exchange (Denmark)": ".CO",
    "OSL - Oslo Stock Exchange (Norway)": ".OL",
    "VIE - Vienna Stock Exchange (Austria)": ".VI",
    "PSE - Prague Stock Exchange (Czech Republic)": ".PR",
    "ATHEX - Athens Stock Exchange (Greece)": ".AT",
    "IST - Istanbul Stock Exchange (Turkey)": ".IS",
    "MOEX - Moscow Exchange (Russia)": ".ME",
    
    # --- ASIA PACIFIC ---
    "TSE - Tokyo Stock Exchange (Japan)": ".T",
    "HKEX - Hong Kong Stock Exchange (Hong Kong)": ".HK",
    "SSE - Shanghai Stock Exchange (China)": ".SS",
    "SZSE - Shenzhen Stock Exchange (China)": ".SZ",
    "TWSE - Taiwan Stock Exchange (Taiwan)": ".TW",
    "KRX - Korea Exchange (South Korea)": ".KS",
    "KOSDAQ - KOSDAQ (South Korea)": ".KQ",
    "ASX - Australian Securities Exchange (Australia)": ".AX",
    "NZX - New Zealand Exchange (New Zealand)": ".NZ",
    "SGX - Singapore Exchange (Singapore)": ".SI",
    "NSE - National Stock Exchange (India)": ".NS",
    "BSE - Bombay Stock Exchange (India)": ".BO",
    "IDX - Indonesia Stock Exchange (Indonesia)": ".JK",
    "KLSE - Bursa Malaysia (Malaysia)": ".KL",
    "SET - Stock Exchange of Thailand (Thailand)": ".BK",
    "PSE - Philippine Stock Exchange (Philippines)": ".PS",
    "HOSE - Ho Chi Minh Stock Exchange (Vietnam)": ".VN",
    
    # --- MIDDLE EAST & AFRICA ---
    "TASE - Tel Aviv Stock Exchange (Israel)": ".TA",
    "TADAWUL - Saudi Stock Exchange (Saudi Arabia)": ".SR",
    "ADX - Abu Dhabi Securities Exchange (UAE)": ".AE",
    "DFM - Dubai Financial Market (UAE)": ".DU",
    "QSE - Qatar Stock Exchange (Qatar)": ".QA",
    "EGX - Egyptian Exchange (Egypt)": ".CA",
    "JSE - Johannesburg Stock Exchange (South Africa)": ".JO",
}

class PriceFetcher:
    def __init__(self):
        self.prices = {}

    def get_yahoo_ticker(self, ticker: str, exchange: str) -> str:
        """
        Converts internal ticker + exchange to Yahoo Ticker.
        Example: "NA9", "FSE - Frankfurt..." -> "NA9.DE"
        """
        ticker = ticker.upper().strip()
        if "." in ticker and not ticker.startswith("."): 
             return ticker
             
        suffix = EXCHANGE_SUFFIXES.get(exchange, "")
        return f"{ticker}{suffix}"

    def validate_ticker(self, ticker: str) -> bool:
        """
        Checks if a ticker exists on Yahoo Finance.
        Returns True if valid data found.
        """
        try:
            # We fetch 1d history. If empty, likely invalid.
            # Using Ticker object is lighter than download for metadata check sometimes,
            # but download is robust.
            import yfinance as yf
            data = yf.download(ticker, period="5d", progress=False)
            if data.empty:
                return False
            return True
        except:
            return False

    def fetch_prices(self, companies: List[Dict]) -> Dict[str, float]:
        """
        Fetches prices for a list of company dicts.
        Returns: { 'TICKER': price }
        """
        yahoo_map = {} 
        to_download = []
        
        print(f"DEBUG: PriceFetcher fetching for {len(companies)} companies...")
        
        for comp in companies:
            if isinstance(comp, str):
                internal = comp
                exchange = ""
                yahoo_override = ""
            else:
                internal = comp.get('ticker')
                exchange = comp.get('primary_exchange', '')
                yahoo_override = (comp.get('yahoo_ticker') or '').strip()
            
            if not internal: continue

            # Prioritize manual yahoo_ticker override
            if yahoo_override:
                yt = yahoo_override
            elif not exchange: 
                yt = internal
            else:
                yt = self.get_yahoo_ticker(internal, exchange)
            
            # De-duplicate: If multiple internal point to same yahoo, store list or just overwrite?
            # Simple overwrite matches current logic.
            yahoo_map[yt] = internal
            to_download.append(yt)
            
        if not to_download: return {}
        
        # Unique list for download
        unique_download = list(set(to_download))
            
        try:
            import yfinance as yf
            import pandas as pd
            
            # Force group_by='ticker' to get (Ticker, Price) structure mostly
            data = yf.download(unique_download, period="5d", progress=False, group_by='ticker')
            
            results = {}
            
            if data.empty:
                return {}

            # Helper to safely extract scalar float
            def extract_val(series_or_val):
                if hasattr(series_or_val, 'item'): 
                    val = series_or_val.item()
                elif hasattr(series_or_val, 'iloc'):
                    val = series_or_val.iloc[-1]
                else:
                    val = series_or_val
                
                try: return float(val)
                except: return 0.0

            # Iterate over REQUESTED tickers to ensure we check everything
            for yt in unique_download:
                val = 0.0
                try:
                    # SCENARIO A: MultiIndex Columns (typical batch)
                    if isinstance(data.columns, pd.MultiIndex):
                        # Try standard group_by='ticker' access: data['TICKER']['Close']
                        # Check if yt is in level 0
                        if yt in data.columns.get_level_values(0):
                             # This returns a Series or DataFrame depending on structure
                             ticker_data = data[yt]
                             if 'Close' in ticker_data:
                                 val = extract_val(ticker_data['Close'].dropna().iloc[-1])
                        
                        # Fallback: Try tuple access if simpler Access failed
                        elif (yt, 'Close') in data.columns:
                            val = extract_val(data[(yt, 'Close')].dropna().iloc[-1])
                        
                        elif ('Close', yt) in data.columns:
                            val = extract_val(data[('Close', yt)].dropna().iloc[-1])
                            
                    # SCENARIO B: Single Index (e.g. only 1 valid ticker returned, or batch=1)
                    else:
                        if len(unique_download) == 1:
                            if 'Close' in data.columns:
                                val = extract_val(data['Close'].dropna().iloc[-1])
                        pass

                except Exception as ex:
                    # print(f"Error parsing {yt}: {ex}")
                    val = 0.0
                
                if yt in yahoo_map:
                    results[yahoo_map[yt]] = val
                    
            return results
                    
            return results
            
        except Exception as e:
            print(f"Price Fetch Error: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_price(self, ticker: str) -> float:
        """
        Helper to get a single price.
        """
        results = self.fetch_prices([{'ticker': ticker}])
        return results.get(ticker, 0.0)

# Global instance
price_fetcher = PriceFetcher()
