import json
import uuid
import os
from datetime import datetime, date
from sqlalchemy.orm import Session
from core.database import get_session_factory, SpecialSituation, SpecialTimeLog, init_db
from config import LIBRARY_ROOT

LIBRARY_ROOT = str(LIBRARY_ROOT)  # str() for os.path compatibility

class SpecialManager:
    def __init__(self, db_path=None):
        if db_path:
             self.engine = init_db(db_path)
        else:
             self.engine = init_db() # Uses default path
        self.Session = get_session_factory(self.engine)

    def add_situation(self, title, event_type, tickers_dict, entry_price, deal_value, target_date, 
                      strategy_type="Generic", specific_data={}, capital_allocated=0.0, probability=0.0,
                      doc_links_list=[], notes="", status="Pipeline", start_date=None):
        """
        Adds a new special situation and creates its folder.
        """
        session = self.Session()
        try:
            # 1. Create Folder
            safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
            folder_path = os.path.join(LIBRARY_ROOT, "SPECIAL", safe_title)
            
            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
                
            # Update specific_data with folder path for reference
            specific_data['folder_path'] = folder_path
            
            def to_dt(v):
                if isinstance(v, str) and v.strip():
                    try: return datetime.strptime(v, "%Y-%m-%d")
                    except: return None
                return v

            situation = SpecialSituation(
                id=str(uuid.uuid4()),
                title=title,
                event_type=event_type,
                strategy_type=strategy_type,
                tickers=json.dumps(tickers_dict),
                entry_price=entry_price,
                deal_value=deal_value,
                capital_allocated=capital_allocated,
                current_value=capital_allocated, # Init with allocated
                target_date=to_dt(target_date),
                start_date=to_dt(start_date),
                specific_data=json.dumps(specific_data),
                probability=probability,
                doc_links=json.dumps(doc_links_list),
                notes=notes,
                status=status
            )
            session.add(situation)
            session.commit()
            return situation.id
        except Exception as e:
            session.rollback()
            print(f"Error adding situation: {e}")
            return None
        finally:
            session.close()

    def get_all_situations(self):
        """Returns all situations."""
        session = self.Session()
        try:
            situations = session.query(SpecialSituation).all()
            results = []
            for s in situations:
                # Safely load JSONs
                try: tickers = json.loads(s.tickers)
                except: tickers = {}
                try: docs = json.loads(s.doc_links)
                except: docs = []
                try: specific = json.loads(s.specific_data)
                except: specific = {}
                
                data = {
                    "id": s.id,
                    "title": s.title,
                    "status": s.status,
                    "event_type": s.event_type,
                    "strategy_type": s.strategy_type,
                    "tickers": tickers,
                    "entry_price": s.entry_price,
                    "deal_value": s.deal_value,
                    "capital_allocated": s.capital_allocated,
                    "current_value": s.current_value,
                    "target_date": s.target_date,
                    "start_date": s.start_date,
                    "doc_links": docs,
                    "specific_data": specific,
                    "probability": s.probability,
                    "notes": s.notes,
                    "created_at": s.created_at,
                    "total_seconds": sum(log.duration_seconds for log in s.time_logs)
                }
                results.append(data)
            return results
        finally:
            session.close()

    def get_situation(self, situation_id):
        """Returns a single situation dict by ID."""
        session = self.Session()
        try:
            s = session.query(SpecialSituation).filter_by(id=situation_id).first()
            if not s: return None
            
            # Safely load JSONs
            try: tickers = json.loads(s.tickers)
            except: tickers = {}
            try: docs = json.loads(s.doc_links)
            except: docs = []
            try: specific = json.loads(s.specific_data)
            except: specific = {}
            
            data = {
                "id": s.id,
                "title": s.title,
                "status": s.status,
                "event_type": s.event_type,
                "strategy_type": s.strategy_type,
                "tickers": tickers,
                "tickers_dict": tickers, # Compat alias
                "entry_price": s.entry_price,
                "deal_value": s.deal_value,
                "capital_allocated": s.capital_allocated,
                "current_value": s.current_value,
                "target_date": s.target_date,
                "start_date": s.start_date,
                "doc_links": docs,
                "specific_data": specific,
                "probability": s.probability,
                "notes": s.notes,
                "created_at": s.created_at,
                "total_seconds": sum(log.duration_seconds for log in s.time_logs)
            }
            return data
        finally:
            session.close()

    def update_situation(self, situation_id, **kwargs):
        """Updates fields of a situation."""
        session = self.Session()
        try:
            s = session.query(SpecialSituation).filter_by(id=situation_id).first()
            if not s:
                return False
            
            old_title = s.title
            new_title = kwargs.get('title', old_title)
            
            # Explicit conversions and handlers
            for key, value in kwargs.items():
                if key == "tickers": 
                     s.tickers = json.dumps(value)
                elif key == "doc_links":
                    s.doc_links = json.dumps(value)
                elif key == "specific_data":
                    s.specific_data = json.dumps(value)
                elif key == "sensitivity_data":
                    s.sensitivity_data = json.dumps(value)
                elif key in ["start_date", "target_date"]:
                    # DB Column is DateTime, expects datetime objects.
                    if isinstance(value, str) and value.strip():
                        s_val = None
                        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                            try:
                                s_val = datetime.strptime(value.strip(), fmt)
                                break
                            except ValueError:
                                pass
                        setattr(s, key, s_val)
                    elif not value:
                        setattr(s, key, None)
                    else:
                        setattr(s, key, value)
                elif hasattr(s, key):
                     setattr(s, key, value)
            
            # Renaming Folder if Title updated
            if new_title != old_title:
                try:
                    # Rename Folder
                    old_safe = "".join([c for c in old_title if c.isalnum() or c in (' ', '-', '_')]).strip()
                    new_safe = "".join([c for c in new_title if c.isalnum() or c in (' ', '-', '_')]).strip()
                    old_path = os.path.join(LIBRARY_ROOT, "SPECIAL", old_safe)
                    new_path = os.path.join(LIBRARY_ROOT, "SPECIAL", new_safe)
                    
                    if os.path.exists(old_path) and not os.path.exists(new_path):
                        os.rename(old_path, new_path)
                        # Update folder_path inside specific_data
                        spec = json.loads(s.specific_data) if s.specific_data else {}
                        spec['folder_path'] = new_path
                        s.specific_data = json.dumps(spec)
                except Exception as ex:
                    print(f"Non-critical folder rename error: {ex}")

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            import traceback
            print(f"Error updating situation: {e}\n{traceback.format_exc()}")
            return False
        finally:
            session.close()

    def delete_situation(self, situation_id):
        session = self.Session()
        try:
            s = session.query(SpecialSituation).filter_by(id=situation_id).first()
            if s:
                session.delete(s)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error deleting situation: {e}")
            return False
        finally:
            session.close()

    def log_time(self, situation_id, duration_seconds):
        session = self.Session()
        try:
            log = SpecialTimeLog(
                situation_id=situation_id,
                start_time=datetime.utcnow(), # Approximate start
                end_time=datetime.utcnow(),
                duration_seconds=duration_seconds
            )
            session.add(log)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error logging time: {e}")
            return False
        finally:
            session.close()


    def update_situation_prices(self, situation_id, prices_dict):

        """

        Update prices for a situation.

        prices_dict = {'target': 123.45, 'acquirer': 67.89} or {'target': 123.45}

        """

        session = self.Session()

        try:

            s = session.query(SpecialSituation).filter_by(id=situation_id).first()

            if not s:

                return False

            

            # Load existing specific_data

            try:

                specific_data = json.loads(s.specific_data)

            except:

                specific_data = {}

            

            # Update prices in specific_data

            if 'prices' not in specific_data:

                specific_data['prices'] = {}

            

            specific_data['prices'].update(prices_dict)

            

            # Save back

            s.specific_data = json.dumps(specific_data)

            session.commit()

            return True

        except Exception as e:

            session.rollback()

            print(f"Error updating prices: {e}")

            return False

        finally:

            session.close()

    

    def get_all_yahoo_tickers(self):

        """

        Returns dict mapping yahoo_ticker -> (situation_id, role)

        For use in bulk price fetching.

        Example: {'GOOG': ('sit-123', 'target'), 'TSLA': ('sit-456', 'acquirer')}

        """

        session = self.Session()

        try:

            situations = session.query(SpecialSituation).all()

            ticker_map = {}

            

            for s in situations:

                try:

                    specific_data = json.loads(s.specific_data)

                except:

                    specific_data = {}

                

                yahoo_tickers = specific_data.get('yahoo_tickers', {})

                

                # Add target ticker

                if 'target' in yahoo_tickers:

                    ticker_map[yahoo_tickers['target']] = (s.id, 'target')

                

                # Add acquirer ticker if exists

                if 'acquirer' in yahoo_tickers:

                    ticker_map[yahoo_tickers['acquirer']] = (s.id, 'acquirer')

            

            return ticker_map

        finally:

            session.close()


    # --- Calculation Logic ---

    @staticmethod
    def calculate_days_to_close(target_date):
        if not target_date:
            return 1
        
        if isinstance(target_date, datetime):
            d_target = target_date.date()
        else:
            d_target = target_date
            
        d_current = date.today()
        delta = (d_target - d_current).days
        return max(1, delta)

    @staticmethod
    def calculate_spread(deal_value, market_price):
        if market_price <= 0:
            return 0.0
        return (deal_value - market_price) / market_price

    @staticmethod
    def calculate_annualized_irr(spread, days_to_close):
        # TIR_a = (1 + S)^(365/d) - 1
        if days_to_close <= 0:
            return 0.0
        exponent = 365 / days_to_close
        try:
            irr = (pow(1 + spread, exponent) - 1) * 100
            return irr
        except:
             return 0.0
