"""
core/services/special_service.py
==================================
Service layer for Special Situations data.

Think of it as the M&A desk specialist. The UI (conference room)
asks for deal data — it never opens the filing cabinet itself.

Returns plain dicts — never SQLAlchemy model objects.
"""

from __future__ import annotations
from typing import Optional


# ── Lazy singleton ────────────────────────────────────────────────────────────
_manager = None


def _get_manager():
    global _manager
    if _manager is None:
        from core.special_manager import SpecialManager
        _manager = SpecialManager()
    return _manager


# ── Service ───────────────────────────────────────────────────────────────────

class SpecialService:
    """
    Service layer for Special Situations (M&A, arbitrage, spin-offs...).

    Usage:
        svc = SpecialService()
        all_sits = svc.get_all()
        active = svc.get_active()
    """

    def __init__(self):
        self._mgr = _get_manager()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_all(self) -> list[dict]:
        """Return all special situations."""
        return self._mgr.get_all_situations()

    def get_by_id(self, situation_id: str) -> Optional[dict]:
        """Return a single situation by ID, or None."""
        return self._mgr.get_situation(situation_id)

    def get_active(self) -> list[dict]:
        """Return only Active situations."""
        return [s for s in self.get_all() if s.get("status") == "Active"]

    def get_pipeline(self) -> list[dict]:
        """Return only Pipeline situations."""
        return [s for s in self.get_all() if s.get("status") == "Pipeline"]

    def get_summary_stats(self) -> dict:
        """
        Return a summary dict for the dashboard:
        {total, active_count, pipeline_count, total_capital_allocated}
        Like a portfolio summary table — one row, key metrics.
        """
        all_sits = self.get_all()
        return {
            "total":                    len(all_sits),
            "active_count":             sum(1 for s in all_sits if s.get("status") == "Active"),
            "pipeline_count":           sum(1 for s in all_sits if s.get("status") == "Pipeline"),
            "total_capital_allocated":  sum(s.get("capital_allocated", 0) or 0 for s in all_sits),
        }

    # ── Calculations ──────────────────────────────────────────────────────────

    def calculate_metrics(self, current_data: dict, live_prices: dict) -> dict:
        """
        Runs the deal calculation math based on current data and live prices.
        Abstracts core.special_definitions away from the UI.
        """
        from core.special_definitions import calculate_global_core, SITUATION_TYPES, resolve_type
        
        stype  = resolve_type(current_data.get('strategy_type', 'Generic'))
        sdata  = current_data.get('specific_data', {})
        t_date = current_data.get('target_date')

        tickers = current_data.get('tickers_dict', {})
        main_ticker = tickers.get('target', '')
        entry_price = float(current_data.get('entry_price', 0.0) or 0.0)
        current_market = entry_price
        
        if main_ticker and main_ticker in live_prices:
            current_market = float(live_prices[main_ticker])

        definition   = SITUATION_TYPES.get(stype, SITUATION_TYPES.get("Generic"))
        calc_func    = definition.get('calc', None)
        specific_res = calc_func(sdata, current_market) if calc_func else {}
        target_implied = specific_res.get('target_price_implied', 0.0)

        if target_implied <= 0.0:
            target_implied = float(sdata.get('deal_value', 0.0))

        close_prob  = float(sdata.get('close_probability', 90)) / 100.0
        break_fee   = float(sdata.get('break_fee_pct', 0.0) or 0.0)
        downside    = float(sdata.get('downside_price', 0.0) or 0.0)

        core = calculate_global_core(
            current_price=current_market,
            target_price=target_implied,
            downside_price=downside,
            target_date=t_date,
            close_probability=close_prob,
            break_fee_pct=break_fee,
            entry_price=entry_price,
            strategy_type=stype,
            scenarios={
                'bear': sdata.get('scenario_bear', {}),
                'base': sdata.get('scenario_base', {}),
                'bull': sdata.get('scenario_bull', {})
            }
        )
        
        if 'error' not in core:
            core['target_implied'] = target_implied
            core['downside'] = downside
            
        return core

    # ── Write ─────────────────────────────────────────────────────────────────

    def add(self, data: dict) -> Optional[str]:
        """
        Create a new special situation.
        Returns the new situation's ID on success, None on failure.
        """
        try:
            return self._mgr.add_situation(data)
        except Exception as e:
            print(f"[SpecialService] Error adding situation: {e}")
            return None

    def update(self, situation_id: str, data: dict) -> bool:
        """Update an existing special situation."""
        try:
            self._mgr.update_situation(situation_id, data)
            return True
        except Exception as e:
            print(f"[SpecialService] Error updating {situation_id}: {e}")
            return False

    def delete(self, situation_id: str) -> bool:
        """Delete a special situation."""
        try:
            self._mgr.delete_situation(situation_id)
            return True
        except Exception as e:
            print(f"[SpecialService] Error deleting {situation_id}: {e}")
            return False

    # ── Time Logging ──────────────────────────────────────────────────────────

    def log_time(self, situation_id: str, duration_seconds: int) -> bool:
        """Log time spent on a situation (Pomodoro integration)."""
        try:
            self._mgr.log_time(situation_id, duration_seconds)
            return True
        except Exception as e:
            print(f"[SpecialService] Error logging time for {situation_id}: {e}")
            return False

    def get_total_hours(self, situation_id: str) -> float:
        """Return total hours invested in a situation."""
        try:
            return self._mgr.get_total_hours(situation_id)
        except Exception:
            return 0.0
