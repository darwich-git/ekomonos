import sys
sys.path.insert(0, 'd:/Proyectos/EKKOMONOS')
from core.special_definitions import (
    SITUATION_CATEGORIES, SITUATION_TYPES, CHECKLIST_GLOBAL, CHECKLIST_BY_TYPE,
    calculate_global_core, calculate_xirr, resolve_type
)
import datetime

print("CATEGORIES:", list(SITUATION_CATEGORIES.keys()))
print("TYPES:", len(SITUATION_TYPES), "types defined")
print("CHECKLIST_GLOBAL:", len(CHECKLIST_GLOBAL), "items")

print("\n--- calculate_global_core test ---")
r = calculate_global_core(
    current_price=54.20,
    target_price=56.10,
    downside_price=48.00,
    target_date='2026-06-30',
    close_probability=0.90,
    break_fee_pct=2.0,
    entry_price=52.00
)
print(f"  spread_pct      = {r['spread_pct']:.2f}%")
print(f"  irr_market      = {r['irr_market']:.1f}%")
print(f"  irr_entry       = {r['irr_entry']:.1f}%")
print(f"  irr_no_deal     = {r['irr_no_deal']:.1f}%")
print(f"  ev_weighted_pct = {r['ev_weighted_pct']:.2f}%")
print(f"  ev_price        = {r['ev_price']:.2f}")
print(f"  risk_reward     = {r['risk_reward']:.2f}")
print(f"  break_fee_sig   = {r['break_fee_signal']:.2f}x")
print(f"  days_to_close   = {r['days_to_close']}")

print("\n--- XIRR test ---")
cf = [-52.0, 56.10]
dates = [datetime.date(2026, 1, 1), datetime.date(2026, 6, 30)]
irr = calculate_xirr(cf, dates)
if irr is not None:
    print(f"  XIRR = {irr*100:.2f}%")
else:
    print("  XIRR = None (convergence failed)")

print("\n--- resolve_type test ---")
print("  Dutch Auction ->", resolve_type("Dutch Auction"))
print("  Bankruptcy (Ch11) ->", resolve_type("Bankruptcy (Ch11)"))
print("  Merger Arbitrage (Cash) ->", resolve_type("Merger Arbitrage (Cash)"))

print("\nALL OK")
