import datetime
from typing import List, Dict, Any, Optional

from core.database import init_db, get_session_factory, CalendarEvent, Company
from sqlalchemy.orm import joinedload
from sqlalchemy import or_

class CalendarService:
    """
    Service layer for F3 Calendar Events.
    Centralizes database querying and merging Virtual Events (from Special Situations)
    into standard dictionaries for the UI to paint without SQL imports.
    """
    
    def __init__(self):
        engine = init_db()
        self.Session = get_session_factory(engine)
        
    def get_all_events(self, include_virtual: bool = True) -> Dict[datetime.date, List[Dict[str, Any]]]:
        """
        Retrieves all valid events grouped by date to support multi-month widgets like Timeline.
        Returns: { date_obj: [event_dict, ...] }
        """
        session = self.Session()
        events_by_date = {}
        
        try:
            # 1. Fetch from DB
            # We filter loosely by year/month to ensure we grab everything relevant across multi-weeks views
            all_events = session.query(CalendarEvent).options(joinedload(CalendarEvent.company)).all()
            
            for evt in all_events:
                d = evt.event_date.date() if isinstance(evt.event_date, datetime.datetime) else evt.event_date
                if d not in events_by_date:
                    events_by_date[d] = []
                
                events_by_date[d].append({
                    'id': evt.id,
                        'event_date': d,
                        'event_type': evt.event_type,
                        'description': evt.description,
                        'source': evt.source,
                        'est_eps': evt.est_eps,
                        'ticker': evt.company.ticker if evt.company else "???",
                        'company_name': evt.company.name if evt.company else "Unknown",
                        'is_virtual': False
                    })
        except Exception as e:
            print(f"[CalendarService] Error fetching DB events: {e}")
        finally:
            session.close()

        # 2. Inject Virtual Events from SpecialService
        if include_virtual:
            from core.services.special_service import SpecialService
            special_svc = SpecialService()
            sits = special_svc.get_all()
            
            for s in sits:
                spec = s.get('specific_data', {})
                milestones = spec.get('milestones', [])
                
                ticker = s.get('tickers_dict', {}).get('target') or s.get('title', 'Unknown')
                
                for m in milestones:
                    d_str = m.get('date')
                    if not d_str: continue
                    synced = m.get('synced', False)
                    # Only inject if 'synced' is checked
                    if str(synced).lower() != 'true' and synced is not True:
                        continue
                        
                    try:
                        d_obj = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
                        if d_obj not in events_by_date:
                            events_by_date[d_obj] = []
                        
                        events_by_date[d_obj].append({
                            'id': f"virtual_{s.get('id')}_{len(events_by_date[d_obj])}",
                                'event_date': d_obj,
                                'event_type': 'Milestone',
                                'description': m.get('name', 'Milestone'),
                                'source': 'special_situation',
                                'est_eps': None,
                                'ticker': ticker,
                                'company_name': s.get('title', ticker),
                                'is_virtual': True
                            })
                    except Exception as e:
                        print(f"[CalendarService] Error parsing virtual event date {d_str}: {e}")

        return events_by_date

    def get_missing_earnings_companies(self) -> List[Dict[str, Any]]:
        """
        Returns a list of dictionaries representing companies that lack future Earnings updates.
        Filters out 'Done' companies and those explicitly flagged to 'ignore_earnings'.
        """
        session = self.Session()
        missing = []
        try:
            # We must verify if the user's DB actually executed the 'status' migration
            try:
                all_companies = session.query(Company).filter(Company.status != 'Done').all()
            except Exception:
                # Fallback if DB column doesn't exist
                session.rollback()
                all_companies = session.query(Company).all()
            
            today = datetime.date.today()
            
            for comp in all_companies:
                # ignore flagged
                if getattr(comp, 'ignore_earnings', False) is True:
                    continue
                
                has_future_earnings = False
                for e in comp.calendar_events:
                    if e.event_type == 'Earnings':
                        d_val = e.event_date.date() if isinstance(e.event_date, datetime.datetime) else e.event_date
                        if isinstance(d_val, datetime.date) and d_val >= today:
                            has_future_earnings = True
                            break
                            
                if not has_future_earnings:
                    missing.append({
                        'id': comp.id,
                        'ticker': comp.ticker,
                        'name': comp.name,
                        'yahoo_ticker': comp.yahoo_ticker or comp.ticker
                    })
        except Exception as e:
            print(f"[CalendarService] Error checking missing earnings: {e}")
        finally:
            session.close()
            
        return missing

    def add_event(self, event_data: dict) -> bool:
        """Adds a manual calendar event."""
        session = self.Session()
        try:
            comp = session.query(Company).filter_by(ticker=event_data.get('ticker')).first()
            if not comp: return False
            
            evt_date = event_data.get('date')
            if isinstance(evt_date, str):
                 evt_date = datetime.datetime.strptime(evt_date, "%Y-%m-%d").date()
                 
            new_evt = CalendarEvent(
                company_id=comp.id,
                event_date=evt_date,
                event_type=event_data.get('type'),
                description=event_data.get('desc'),
                source="Manual"
            )
            session.add(new_evt)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"[CalendarService] Error adding event: {e}")
            return False
        finally:
            session.close()

    def delete_event(self, event_id: int) -> bool:
        """Deletes a calendar event from DB."""
        session = self.Session()
        try:
            evt = session.query(CalendarEvent).get(event_id)
            if evt:
                session.delete(evt)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"[CalendarService] Error deleting event: {e}")
            return False
        finally:
            session.close()

    def edit_event(self, event_id: int, event_data: dict) -> bool:
        """Edits an existing calendar event."""
        session = self.Session()
        try:
            # Cannot edit virtual events
            if str(event_id).startswith('virtual_'): return False
                
            evt = session.query(CalendarEvent).get(event_id)
            if not evt: return False
            
            evt_date = event_data.get('date')
            if isinstance(evt_date, str):
                 evt_date = datetime.datetime.strptime(evt_date, "%Y-%m-%d").date()
                 
            evt.event_date = evt_date
            evt.event_type = event_data.get('type')
            evt.description = event_data.get('desc')
            evt.source = "Manual"
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"[CalendarService] Error editing event: {e}")
            return False
        finally:
            session.close()
