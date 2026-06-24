

from datetime import datetime, date
import logging
from sqlalchemy.orm import Session
from core.database import CalendarEvent, Company

class EarningsManager:
    """
    Manages fetching and storing earnings dates for companies.
    Supports hybrid model: Auto (Yahoo) + Manual.
    """
    
    SOURCE_AUTO = "Yahoo"
    SOURCE_MANUAL = "Manual"
    
    def __init__(self, session_factory):
        """
        Args:
            session_factory: SQLAlchemy session maker.
        """
        self.Session = session_factory
        self.logger = logging.getLogger("EarningsManager")

    def fetch_earnings_data(self, ticker_symbol):
        """
        Fetches next earnings date and EPS estimate from Yahoo Finance.
        Returns:
            dict: {
                "date": datetime object or None, 
                "eps_estimate": float or None,
                "source": SOURCE_AUTO
            }
        """
        def get_data_for_ticker(symbol):
            try:
                import yfinance as yf
                import pandas as pd
                ticker = yf.Ticker(symbol)
                earnings_dates = ticker.earnings_dates
                
                if earnings_dates is None or earnings_dates.empty:
                    return None

                # Find next earnings
                # Ensure timezone compatibility for comparison
                now = pd.Timestamp.now(tz=earnings_dates.index.tz) 
                future_earnings = earnings_dates[earnings_dates.index > now].sort_index()
                
                next_date_val = None
                eps_est = None
                
                if not future_earnings.empty:
                    next_date_val = future_earnings.index[0]
                    if 'EPS Estimate' in future_earnings.columns:
                        val = future_earnings.loc[next_date_val, 'EPS Estimate']
                        if pd.notna(val):
                            eps_est = float(val)
                else:
                    # FALLBACK: Try ticker.calendar
                    print(f"[DEBUG] earnings_dates empty for {symbol}, trying ticker.calendar")
                    cal = ticker.calendar
                    if cal and 'Earnings Date' in cal:
                        ed = cal['Earnings Date']
                        if isinstance(ed, list) and len(ed) > 0:
                            next_date_val = ed[0]
                        else:
                            next_date_val = ed
                
                if next_date_val is None:
                    return None

                # Handle next_date_val being a date or timestamp
                if hasattr(next_date_val, 'to_pydatetime'):
                    next_dt = next_date_val.to_pydatetime().replace(tzinfo=None)
                elif isinstance(next_date_val, (date, datetime)):
                    if isinstance(next_date_val, date) and not isinstance(next_date_val, datetime):
                        next_dt = datetime.combine(next_date_val, datetime.min.time())
                    else:
                        next_dt = next_date_val.replace(tzinfo=None)
                else:
                    return None
                
                return {
                    "date": next_dt,
                    "eps_estimate": eps_est,
                    "source": self.SOURCE_AUTO,
                    "long_name": ticker.info.get('longName', '') 
                }
            except Exception as e:
                print(f"[DEBUG] Error fetching {symbol}: {e}")
                return None

        # Logic with fallback
        # If user provides a specific yahoo_ticker (passed as ticker_symbol arg if we change signature, 
        # but let's assume valid symbol is passed)
        
        # We need to change signature or handle it in loop
        result = get_data_for_ticker(ticker_symbol)
        if result: return result
        
        # Fallback if no specific region provided and primary failed
        if "." not in ticker_symbol: 
             fallback = f"{ticker_symbol}.DE"
             # self.logger.info(f"Trying fallback: {fallback}")
             return get_data_for_ticker(fallback)
             
        return None   
    
    MAX_DAYS_AHEAD = 365 # Only look 1 year ahead

    def update_calendar_event(self, session: Session, company: Company, event_date: datetime, est_eps: float, source: str):
        """
        Helper to update or create a CalendarEvent for earnings.
        """
        today = datetime.now()
        existing_event = session.query(CalendarEvent).filter(
            CalendarEvent.company_id == company.id,
            CalendarEvent.event_type == "Earnings",
            CalendarEvent.event_date >= today
        ).order_by(CalendarEvent.event_date).first()

        if existing_event:
            existing_event.event_date = event_date
            existing_event.est_eps = est_eps
            existing_event.source = source
        else:
            new_event = CalendarEvent(
                company_id=company.id,
                event_date=event_date,
                event_type="Earnings",
                status="Confirmed",
                description="", 
                source=source,
                est_eps=est_eps
            )
            session.add(new_event)

    def update_company(self, ticker, session=None):
        """
        Updates earnings for a single company by ticker.
        If session provided, uses it (doesn't commit). If not, creates new (commits).
        """
        local_session = False
        if session is None:
            session = self.Session()
            local_session = True
            
        try:
            comp = session.query(Company).filter_by(ticker=ticker).first()
            if not comp: return False
            
            search_ticker = comp.yahoo_ticker if comp.yahoo_ticker else comp.ticker
            data = self.fetch_earnings_data(search_ticker)
            
            if data:
                # Validation (Same logic as sync_all, could refactor)
                fetched_name = data.get('long_name', '').lower()
                db_name = comp.name.lower()
                
                if "spyro" in db_name and "spirit" in fetched_name:
                        print(f"SAFETY BLOCK: Ignored {fetched_name} for {db_name}")
                        return False

                self.update_calendar_event(session, comp, data['date'], data['eps_estimate'], self.SOURCE_AUTO)
                if local_session: session.commit()
                return True
            
            return False
            
        except Exception as e:
            print(f"Update error {ticker}: {e}")
            return False
        finally:
            if local_session: session.close()

    def sync_all_companies(self):
        """
        Iterates through all companies in DB and attempts to update them.
        Returns:
            dict: {"success": int, "failed": int}
        """
        session = self.Session()
        companies = session.query(Company).filter(Company.status != 'Done').all()
        # tickers = [c.ticker for c in companies] # No longer needed
        # session.close() # Close to avoid holding during long fetch - keep open for updates
        
        stats = {"updated": 0, "failed": 0, "details": []}
        
        print(f"Syncing earnings for {len(companies)} companies...")
        
        # Skip manual override? Use logic "If source==Manual, skip"? 
        # User wants "Action Required" list. If they hit "SyncAll", maybe we SHOULD check all.
        # Usually Manual is only for those where Yahoo failed. If Yahoo suddenly works, great.
        # But if User manually set a different date than Yahoo, overwriting is risky.
        # For now, let's just Try Update. If Yahoo has data, it's usually authoritative.
        for comp in companies:
            # Use yahoo_ticker if set, else ticker
            search_ticker = comp.yahoo_ticker if comp.yahoo_ticker else comp.ticker
            
            try:
                data = self.fetch_earnings_data(search_ticker)
                
                if data:
                    # Safety Validation
                    fetched_name = data.get('long_name', '').lower()
                    db_name = comp.name.lower()
                    
                    # Simple safety check: 
                    # If ticker was "SPR" (3 chars) and fetched name "Spirit..." vs DB Name "Spyrosoft..."
                    # Reject if very different?
                    # Use simple heurestic: if both names are long enough (>4 chars), check token overlap?
                    # Or checking if DB name appears in fetched name?
                    
                    # Warning logic for Spyrosoft/SPR (Spirit)
                    if "spyro" in db_name and "spirit" in fetched_name:
                         print(f"SAFETY BLOCK: Ignored {fetched_name} for {db_name} (SPR confusion)")
                         stats['failed'] += 1
                         continue

                    # Update data
                    self.update_calendar_event(
                        session, 
                        comp, 
                        data['date'], 
                        data['eps_estimate'], 
                        source=self.SOURCE_AUTO
                    )
                    stats['updated'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                print(f"Error syncing {comp.ticker}: {e}")
                stats['failed'] += 1
        
        session.commit() # Commit all changes at once
        session.close()
        return stats
