"""
special_definitions.py — Special Situations V2
Motor de cálculo alineado con el marco Hielco.
Incluye: XIRR, EV ponderado, IRR dual (entrada/mercado), escenarios Bear/Base/Bull.
"""
from datetime import date, datetime
import math

# ---------------------------------------------------------------------------
# XIRR — Newton-Raphson (sin dependencias externas)
# ---------------------------------------------------------------------------

def calculate_xirr(cashflows, dates, guess=0.10, max_iter=300, tol=1e-6):
    """
    Calcula la TIR real para flujos de caja en fechas arbitrarias.
    cashflows: lista de floats (negativo=inversión, positivo=cobro)
    dates:     lista de datetime.date o datetime.datetime
    Devuelve IRR como float (ej: 0.15 = 15%), o None si no converge.

    Si solo hay 1 flujo válido, devuelve el IRR simple de 1 período como fallback.
    """
    if not cashflows or not dates or len(cashflows) != len(dates):
        return None

    # Convertir todas las fechas a date
    d_dates = []
    for d in dates:
        if isinstance(d, datetime):
            d_dates.append(d.date())
        elif isinstance(d, str):
            try:
                d_dates.append(datetime.strptime(d, "%Y-%m-%d").date())
            except:
                return None
        elif isinstance(d, date):
            d_dates.append(d)
        else:
            return None

    d0 = d_dates[0]

    def xnpv(rate):
        return sum(
            cf / pow(1 + rate, (d - d0).days / 365.0)
            for cf, d in zip(cashflows, d_dates)
        )

    def dxnpv(rate):
        """Derivada de xnpv para Newton-Raphson."""
        return sum(
            -cf * (d - d0).days / 365.0 / pow(1 + rate, (d - d0).days / 365.0 + 1)
            for cf, d in zip(cashflows, d_dates)
        )

    # Fallback: si solo 2 flujos (inversión + pago único), IRR simple
    if len(cashflows) == 2:
        try:
            inv = abs(cashflows[0])
            rec = cashflows[1]
            days = (d_dates[1] - d_dates[0]).days
            if inv > 0 and rec > 0 and days > 0:
                simple_spread = (rec - inv) / inv
                return pow(1 + simple_spread, 365.0 / days) - 1
        except:
            pass

    # Newton-Raphson
    rate = guess
    for _ in range(max_iter):
        try:
            npv = xnpv(rate)
            d_npv = dxnpv(rate)
            if abs(d_npv) < 1e-12:
                break
            new_rate = rate - npv / d_npv
            if abs(new_rate - rate) < tol:
                return new_rate
            rate = new_rate
            # Evitar explotar
            if rate < -0.999 or rate > 100:
                break
        except (OverflowError, ZeroDivisionError):
            break
    return None


# ---------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL — calculate_global_core
# ---------------------------------------------------------------------------

def calculate_global_core(current_price, target_price, downside_price, target_date,
                           close_probability=0.90, break_fee_pct=0.0,
                           entry_price=None, strategy_type="Generic", scenarios=None):
    """
    Calcula todas las métricas universales para cualquier situación especial.

    Parámetros:
      current_price    : Precio actual de mercado (usado para IRR de mercado)
      target_price     : Precio objetivo si el deal cierra
      downside_price   : Precio estimado si el deal no ocurre
      target_date      : Fecha esperada de cierre
      close_probability: Probabilidad de cierre 0.0-1.0 (default 0.90)
      break_fee_pct    : Break fee como % del precio oferta (default 0.0)
      entry_price      : Precio de entrada real (para IRR de entrada)
                         Si es None, se usa current_price como base

    Retorna: dict con todas las métricas calculadas.
    """
    results = {}

    # 0. Safety Checks
    if not current_price or current_price <= 0:
        return {"error": "Invalid Current Price", "spread_pct": 0, "irr": 0,
                "irr_entry": 0, "ev_weighted_pct": 0, "ev_price": 0,
                "days_to_close": 0, "risk_reward": 0, "irr_no_deal": 0,
                "break_fee_signal": 0}

    p = float(close_probability)  # 0.0 – 1.0
    if p > 1.0:
        p = p / 100.0  # Si vino como 0-100, normalizar
    p = max(0.0, min(1.0, p))

    e_price = float(entry_price) if entry_price and float(entry_price) > 0 else current_price
    t_price = float(target_price) if target_price else 0.0
    d_price = float(downside_price) if downside_price else 0.0

    # 1. Days to Close
    today = date.today()
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    elif isinstance(target_date, str) and target_date:
        # Try multiple formats
        parsed = None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(target_date, fmt).date()
                break
            except ValueError:
                pass
        target_date = parsed if parsed else today

    if not target_date:
        target_date = today

    days_to_close = (target_date - today).days
    results['days_to_close'] = days_to_close

    # 2. Spread (vs precio actual de mercado)
    if t_price > 0:
        spread = (t_price - current_price) / current_price
        results['spread'] = spread
        results['spread_pct'] = spread * 100
    else:
        results['spread'] = 0.0
        results['spread_pct'] = 0.0

    # 3. Spread (vs precio de entrada — para comparar con lo que pagaste)
    if t_price > 0 and e_price > 0:
        spread_entry = (t_price - e_price) / e_price
        results['spread_entry'] = spread_entry
        results['spread_entry_pct'] = spread_entry * 100
    else:
        results['spread_entry'] = 0.0
        results['spread_entry_pct'] = 0.0

    # 4. IRR anualizada — precio de mercado (cuánto gana hoy si compras ahora)
    try:
        if days_to_close <= 0:
            irr_market = results['spread'] * 100
        else:
            irr_market = (pow(1 + results['spread'], 365.0 / max(15, days_to_close)) - 1) * 100
    except (ValueError, ZeroDivisionError, OverflowError):
        irr_market = 0.0
    results['irr'] = irr_market          # alias legacy
    results['irr_market'] = irr_market

    # 5. IRR anualizada — precio de entrada (tu rentabilidad real)
    try:
        if days_to_close <= 0:
            irr_entry = results['spread_entry'] * 100
        else:
            irr_entry = (pow(1 + results['spread_entry'], 365.0 / max(15, days_to_close)) - 1) * 100
    except (ValueError, ZeroDivisionError, OverflowError):
        irr_entry = 0.0
    results['irr_entry'] = irr_entry

    # 6. IRR si no-deal (pérdida anualizada si el deal muere y cotiza al downside)
    if d_price > 0 and current_price > 0:
        spread_no_deal = (d_price - current_price) / current_price
        try:
            if days_to_close <= 0:
                irr_no_deal = spread_no_deal * 100
            else:
                irr_no_deal = (pow(1 + spread_no_deal, 365.0 / max(15, days_to_close)) - 1) * 100
        except:
            irr_no_deal = 0.0
    else:
        irr_no_deal = 0.0
    results['irr_no_deal'] = irr_no_deal

    # 7 & 8. Expected Value (EV) Calculation
    # Adapt to strategy type / scenarios if available
    is_ma = strategy_type in ["Merger Arbitrage (Cash)", "Merger Arbitrage (Stock)", "Going Private (LBO)", "Tender Offer / Dutch Auction"]
    
    use_scenarios_for_ev = False
    if scenarios and not is_ma:
        # Check if scenarios sum to ~100
        prob_sum = scenarios.get('bear', {}).get('prob', 0) + scenarios.get('base', {}).get('prob', 0) + scenarios.get('bull', {}).get('prob', 0)
        if prob_sum >= 99.0 and prob_sum <= 101.0:
            use_scenarios_for_ev = True

    if use_scenarios_for_ev:
        bear_p = scenarios['bear'].get('price', 0)
        bear_prob = scenarios['bear'].get('prob', 0) / 100.0
        base_p = scenarios['base'].get('price', 0)
        base_prob = scenarios['base'].get('prob', 0) / 100.0
        bull_p = scenarios['bull'].get('price', 0)
        bull_prob = scenarios['bull'].get('prob', 0) / 100.0
        
        ev_price = (bear_p * bear_prob) + (base_p * base_prob) + (bull_p * bull_prob)
        if current_price > 0:
            ev_weighted = (ev_price - current_price) / current_price
        else:
            ev_weighted = 0.0
    else:
        # Classic binary (Hielco) probability weighting
        if d_price > 0 and current_price > 0:
            downside_pct = (d_price - current_price) / current_price
            ev_weighted = p * results['spread'] + (1 - p) * downside_pct
        else:
            ev_weighted = p * results['spread']
            
        if t_price > 0:
            if d_price > 0:
                ev_price = p * t_price + (1 - p) * d_price
            else:
                ev_price = p * t_price + (1 - p) * current_price
        else:
            ev_price = current_price

    results['ev_weighted'] = ev_weighted
    results['ev_weighted_pct'] = ev_weighted * 100
    results['ev_price'] = ev_price

    # --- When scenarios drive the EV, override spread & IRR with EV-based values ---
    # This prevents annualizing a raw bull-case spread (e.g. 78%) when
    # the probability-weighted expected return is much lower (e.g. 29%).
    if use_scenarios_for_ev and ev_price > 0:
        ev_spread = (ev_price - current_price) / current_price
        results['spread'] = ev_spread
        results['spread_pct'] = ev_spread * 100

        ev_spread_entry = (ev_price - e_price) / e_price if e_price > 0 else 0.0
        results['spread_entry'] = ev_spread_entry
        results['spread_entry_pct'] = ev_spread_entry * 100

        try:
            if days_to_close <= 0:
                results['irr_market'] = ev_spread * 100
            else:
                results['irr_market'] = (pow(1 + ev_spread, 365.0 / max(15, days_to_close)) - 1) * 100
        except (ValueError, ZeroDivisionError, OverflowError):
            results['irr_market'] = 0.0
        results['irr'] = results['irr_market']

        try:
            if days_to_close <= 0:
                results['irr_entry'] = ev_spread_entry * 100
            else:
                results['irr_entry'] = (pow(1 + ev_spread_entry, 365.0 / max(15, days_to_close)) - 1) * 100
        except (ValueError, ZeroDivisionError, OverflowError):
            results['irr_entry'] = 0.0

    # 9. Risk / Reward = upside / downside (en unidades de precio)
    upside = t_price - current_price if t_price > 0 else 0
    if d_price > 0 and d_price < current_price:
        loss = current_price - d_price
        results['risk_reward'] = upside / loss if loss != 0 else 0.0
    else:
        results['risk_reward'] = 0.0

    # 10. Break Fee Signal (ratio de protección: break_fee / spread en $)
    if break_fee_pct > 0 and t_price > 0:
        break_fee_usd = t_price * (break_fee_pct / 100.0)
        spread_usd = t_price - current_price
        results['break_fee_signal'] = break_fee_usd / spread_usd if spread_usd > 0 else 0.0
    else:
        results['break_fee_signal'] = 0.0

    # 11. Probabilidad ajustada legacy
    results['roi_prob'] = results['spread'] * p

    return results


def calculate_scenario_irr(scenario_price, current_price, days_to_close):
    """Calcula IRR de un escenario específico (Bear/Base/Bull)."""
    if not current_price or current_price <= 0:
        return 0.0
    try:
        spread = (scenario_price - current_price) / current_price
        if days_to_close <= 0:
            return spread * 100
        return (pow(1 + spread, 365.0 / max(15, days_to_close)) - 1) * 100
    except:
        return 0.0


# ---------------------------------------------------------------------------
# CHECKLISTS HIELCO
# ---------------------------------------------------------------------------

CHECKLIST_GLOBAL = [
    ("tesis_catalizador",      "Tesis y catalizador claros y fechados"),
    ("doc_oficial",            "Documentación oficial verificada (filing/folleto)"),
    ("estructura_evento",      "Estructura del evento clara (cash/stock/collar)"),
    ("financiacion",           "Financiación asegurada y contrapartes creíbles"),
    ("alineacion_accionarial", "Alineación accionarial y gobernanza"),
    ("valoracion_downside",    "Valoración y downside modelizado"),
    ("cronograma",             "Cronograma y riesgo de tiempo calculado"),
    ("prob_cierre",            "Probabilidad de cierre apoyada en precedentes"),
    ("liquidez_operativa",     "Liquidez, operativa y costes calculados"),
    ("plan_salida",            "Plan de posición y reglas de salida definidas"),
]

CHECKLIST_BY_TYPE = {
    "Merger Arbitrage (Cash)": [
        ("oferta_firme",        "Oferta firme y precio fijo confirmado"),
        ("break_fees",          "Break/reverse-break fees suficientes"),
        ("aprobaciones",        "Aprobaciones antitrust/FDI identificadas"),
        ("outside_date_ok",     "Outside date y posibles extensiones revisadas"),
        ("downside_nodeal",     "Downside en escenario no-deal calculado"),
    ],
    "Merger Arbitrage (Stock)": [
        ("collar_ratio",        "Collar o ratio de canje bien definido"),
        ("riesgo_adquirente",   "Riesgo de mercado en precio del adquirente analizado"),
        ("hedge_posible",       "Posibilidad de hedge del adquirente evaluada"),
    ],
    "Contingent Value Rights (CVR)": [
        ("trigger_claro",       "Trigger(s) del CVR bien definidos y medibles"),
        ("ventana_temporal",    "Ventana temporal y fecha de vencimiento clara"),
        ("garantia_cvr",        "CVR garantizado o no garantizado identificado"),
        ("reporting_auditado",  "Mecanismo de reporting y auditoría verificado"),
    ],
    "Spin-off": [
        ("motivacion_estrategica", "Motivación estratégica del spin-off clara"),
        ("incentivos_mgmt",     "Incentivos nueva directiva (LTIP/opciones) revisados"),
        ("deuda_asignada",      "Deuda asignada al SpinCo razonable y documentada"),
        ("presion_tecnica",     "Presión técnica de venta forzada identificada"),
        ("sotp_calculado",      "SOTP calculado (padre + spinco vs. consolidated)"),
    ],
    "Split-off": [
        ("ratio_canje_justo",   "Ratio de canje favorable calculado vs. valor real"),
        ("proration_estimada",  "Proration estimada en escenario de sobresuscripción"),
        ("hedge_padre",         "Hedge en acciones del padre evaluado"),
    ],
    "Equity Carve-out": [
        ("precio_ipo_sub",      "Precio IPO de la filial y descuento vs. padre"),
        ("stub_calculado",      "Valor del stub del padre calculado post-carve-out"),
        ("lockup_expiry",       "Fecha de lock-up del padre y riesgo de dilución"),
    ],
    "Liquidations": [
        ("inventario_activos",  "Inventario de activos y valores de liquidación estimados"),
        ("costes_liquidacion",  "Costes totales de liquidación estimados (fees, taxes, etc.)"),
        ("pasivos_contingentes","Pasivos contingentes y provisiones revisados"),
        ("calendario_pagos",    "Calendario de pagos parciales definido"),
        ("incentivos_gestor",   "Incentivos del gestor/liquidator alineados"),
    ],
    "Rights Offering": [
        ("necesidad_capital",   "Necesidad real de capital justificada y creíble"),
        ("aseguramiento",       "Underwriter/backstop confirmado"),
        ("terp_calculado",      "TERP calculado correctamente (precio teórico ex-derecho)"),
        ("uso_fondos",          "Uso de fondos específico y creíble"),
    ],
    "Odd Lot Tender": [
        ("prioridad_confirmada","Prioridad odd-lot confirmada en los términos de la oferta"),
        ("elegibilidad",        "Elegibilidad jurisdiccional y de cuenta verificada"),
        ("fechas_custodios",    "Fechas exactas y custodios confirmados"),
    ],
    "Post-Bankruptcy (Emergence)": [
        ("plan_confirmado",     "Plan de reorganización confirmado por el tribunal"),
        ("nueva_estructura",    "Nueva estructura de capital clara (deuda, equity)"),
        ("overhang_forzado",    "Overhang de vendedores forzados estimado"),
        ("covenants_revisados", "Covenants de la nueva deuda revisados"),
    ],
    "Going Private (LBO)": [
        ("oferta_firme",        "Oferta firme y fuente de financiación confirmada"),
        ("go_shop_ok",          "Período go-shop sin ofertas competidoras relevantes"),
        ("fairness_opinion",    "Fairness opinion del consejo independiente emitida"),
        ("minoritarios",        "Protecciones para accionistas minoritarios verificadas"),
    ],
    "Tender Offer / Dutch Auction": [
        ("precio_tender_ok",    "Precio del tender/rango del Dutch Auction claro"),
        ("proration_riesgo",    "Riesgo de proration estimado"),
        ("condiciones_minimas", "Condiciones mínimas de aceptación revisadas"),
    ],
    "Litigation Arbitrage": [
        ("jurisdiccion_clara",  "Jurisdicción y legislación aplicable identificada"),
        ("precedentes",         "Precedentes legales relevantes analizados"),
        ("costes_legales",      "Costes legales y tiempo estimados"),
        ("acuerdo_extrajudicial","Posibilidad de acuerdo extrajudicial evaluada"),
    ],
    "Holding Discount / SOTP": [
        ("sotp_detallado",      "Suma de partes (SOTP) calculado con cada activo"),
        ("descuento_estimado",  "Descuento de holding vs. NAV estimado"),
        ("catalizador_reduccion","Catalizador concreto para reducción del descuento"),
        ("activism_riesgo",     "Riesgo de activismo o ausencia de catalizador"),
    ],
    "Index Inclusion/Exclusion": [
        ("criterios_inclusion", "Criterios de inclusión/exclusión verificados"),
        ("fecha_rebalanceo",    "Fecha de rebalanceo y anuncio confirmada"),
        ("flujos_estimados",    "Flujos de fondos pasivos estimados"),
        ("liqudez_mercado",     "Liquidez del mercado suficiente para el flujo"),
    ],
    "SPAC Arbitrage": [
        ("trust_value_ok",      "Valor del trust por acción verificado"),
        ("warrant_value",       "Valor de los warrants/derechos separado del trust"),
        ("deadline_merger",     "Deadline para completar fusión revisado"),
    ],
    "Generic": [],
}


# ---------------------------------------------------------------------------
# CATEGORÍAS Y TIPOS SIMPLIFICADOS (V2)
# ---------------------------------------------------------------------------

SITUATION_CATEGORIES = {
    "M&A Arbitrage": [
        "Merger Arbitrage (Cash)",
        "Merger Arbitrage (Stock)",
        "Going Private (LBO)",
        "Tender Offer / Dutch Auction",
    ],
    "Contingent Rights": [
        "Contingent Value Rights (CVR)",
        "Litigation Arbitrage",
    ],
    "Restructuring & Spinoffs": [
        "Spin-off",
        "Split-off",
        "Equity Carve-out",
    ],
    "Capital Events": [
        "Rights Offering",
        "Odd Lot Tender",
        "Special Dividend / Asset Sale",
        "SPAC Arbitrage",
    ],
    "Distress & Liquidation": [
        "Liquidations",
        "Post-Bankruptcy (Emergence)",
    ],
    "Activist & Catalyst": [
        "Holding Discount / SOTP",
        "Index Inclusion/Exclusion",
    ],
    "Other": [
        "Generic",
    ],
}


# ---------------------------------------------------------------------------
# FUNCIONES DE CÁLCULO POR TIPO
# ---------------------------------------------------------------------------

def calc_merger_arb_cash(inputs, current_price):
    offer = inputs.get('offer_price', 0.0)
    return {
        'target_price_implied': offer,
        'info': f"Offer: {offer:.2f}"
    }

def calc_merger_arb_stock(inputs, current_price):
    acq_price = inputs.get('acquirer_price', 0.0)
    ratio = inputs.get('exchange_ratio', 0.0)
    implied_offer = acq_price * ratio
    return {
        'target_price_implied': implied_offer,
        'info': f"Implied: {implied_offer:.2f} (Acq: {acq_price} x {ratio})"
    }

def calc_cvr(inputs, current_price):
    p_max = inputs.get('max_payout', 0.0)
    prob = inputs.get('milestone_prob', 0.0) / 100.0
    expected_val = p_max * prob
    return {
        'target_price_implied': expected_val,
        'info': f"EV: {expected_val:.2f} ({prob*100:.0f}% of {p_max})"
    }

def calc_lbo(inputs, current_price):
    offer = inputs.get('offer_price', 0.0)
    return {'target_price_implied': offer, 'info': f"LBO Offer: {offer:.2f}"}

def calc_tender_dutch(inputs, current_price):
    tender = inputs.get('tender_price', 0.0)
    min_p = inputs.get('min_price', 0.0)
    max_p = inputs.get('max_price', 0.0)
    if tender > 0:
        return {'target_price_implied': tender, 'info': f"Tender: {tender:.2f}"}
    elif max_p > 0:
        mid = (min_p + max_p) / 2
        return {'target_price_implied': mid, 'info': f"Dutch midpoint: {mid:.2f}"}
    return {'target_price_implied': 0, 'info': "No price set"}

def calc_litigation(inputs, current_price):
    claim = inputs.get('claim_value', 0.0)
    cost = inputs.get('legal_cost', 0.0)
    prob = inputs.get('success_prob', 0.0) / 100.0
    ev_legal = (prob * claim) - ((1 - prob) * cost)
    return {
        'target_price_implied': ev_legal,
        'info': f"EV Legal: {ev_legal:.2f}"
    }

def calc_spinoff(inputs, current_price):
    spin_price = inputs.get('spinco_price', 0.0)
    ratio = inputs.get('distribution_ratio', 0.0)
    val_received = spin_price * ratio
    return {
        'target_price_implied': current_price + val_received,
        'calculated_value': val_received,
        'info': f"Spin Value: {val_received:.2f}/share"
    }

def calc_splitoff(inputs, current_price):
    sub_price = inputs.get('sub_price', 0.0)
    ratio = inputs.get('exchange_ratio', 0.0)
    proration = inputs.get('proration_est', 0.0) / 100.0
    value_package = sub_price * ratio
    profit_raw = value_package - current_price
    return {
        'target_price_implied': value_package,
        'info': f"Arb Spread: {profit_raw:.2f} (Proration ~{proration*100:.0f}%)"
    }

def calc_carve_out(inputs, current_price):
    ipo_val = inputs.get('ipo_val', 0.0)
    parent_mcap = inputs.get('parent_mcap', 0.0)
    pct_sold = inputs.get('pct_sold', 0.0) / 100.0
    sub_retained = ipo_val * (1 - pct_sold)
    stub_implied = parent_mcap - sub_retained
    return {
        'calculated_value': stub_implied,
        'info': f"Stub Implied: {stub_implied:,.0f}"
    }

def calc_liquidation(inputs, current_price):
    net_cash = inputs.get('net_cash', 0.0)
    assets = inputs.get('assets', 0.0)
    liabilities = inputs.get('liabilities', 0.0)
    shares = inputs.get('shares', 1.0)
    if not shares or shares <= 0:
        shares = 1.0
    nav_per_share = (net_cash + assets - liabilities) / shares
    return {
        'target_price_implied': nav_per_share,
        'info': f"NAV/Share: {nav_per_share:.2f}"
    }

def calc_rights(inputs, current_price):
    sub_price = inputs.get('subscription_price', 0.0)
    ratio = inputs.get('rights_ratio', 0.0)
    if ratio + 1 == 0:
        val = 0
    else:
        val = (current_price - sub_price) / (ratio + 1)
    terp = (current_price * ratio + sub_price) / (ratio + 1) if ratio + 1 != 0 else 0
    return {
        'calculated_value': val,
        'target_price_implied': sub_price,
        'info': f"Right Val: {val:.2f} | TERP: {terp:.2f}"
    }

def calc_odd_lot(inputs, current_price):
    tender = inputs.get('tender_price', 0.0)
    fee = inputs.get('commissions', 0.0)
    profit = (tender * 99) - (current_price * 99) - fee
    return {
        'target_price_implied': tender,
        'calculated_value': profit,
        'info': f"Net Profit (99sh): {profit:.2f}"
    }

def calc_special_dividend(inputs, current_price):
    div = inputs.get('div_amount', 0.0)
    stub_min = inputs.get('stub_est_min', 0.0)
    stub_max = inputs.get('stub_est_max', 0.0)
    stub_val = (stub_min + stub_max) / 2 if stub_max > 0 else stub_min
    total_val = div + stub_val
    adj_entry = current_price - div
    return {
        'target_price_implied': total_val,
        'calculated_value': stub_val,
        'info': f"Adj Entry: {adj_entry:.2f} | Stub: {stub_min:.2f}–{stub_max:.2f}"
    }

def calc_post_bankruptcy(inputs, current_price):
    new_equity = inputs.get('new_equity', 0.0)
    recovery = inputs.get('recovery', 0.0) / 100.0
    val = new_equity * recovery
    return {
        'target_price_implied': val,
        'info': f"Emergence Value: {val:.2f}"
    }

def calc_spac(inputs, current_price):
    trust_value = inputs.get('trust_value', 10.0)
    return {'target_price_implied': trust_value, 'info': f"Trust: {trust_value:.2f}"}

def calc_holding_sotp(inputs, current_price):
    sotp_total = inputs.get('sotp_total', 0.0)
    holding_costs = inputs.get('holding_costs', 0.0)
    nav = sotp_total - holding_costs
    discount = (nav - current_price) / nav * 100 if nav > 0 else 0
    return {
        'target_price_implied': nav,
        'info': f"Discount al NAV: {discount:.1f}%"
    }

def calc_index_event(inputs, current_price):
    target = inputs.get('target_price', 0.0)
    return {
        'target_price_implied': target,
        'info': f"Post-inclusion target: {target:.2f}"
    }

def calc_simple_target(inputs, current_price):
    return {'target_price_implied': inputs.get('target_price', 0.0)}


# ---------------------------------------------------------------------------
# SITUATION_TYPES — Inputs por tipo y función de cálculo
# ---------------------------------------------------------------------------

SITUATION_TYPES = {
    # --- M&A Arbitrage ---
    "Merger Arbitrage (Cash)": {
        "inputs": [
            {'label': 'Offer Price',           'key': 'offer_price',     'type': 'double'},
            {'label': 'Termination Fee',       'key': 'term_fee',        'type': 'double'},
        ],
        "calc": calc_merger_arb_cash
    },
    "Merger Arbitrage (Stock)": {
        "inputs": [
            {'label': 'Acquirer Ticker',       'key': 'acquirer_ticker', 'type': 'text'},
            {'label': 'Acquirer Price',        'key': 'acquirer_price',  'type': 'double'},
            {'label': 'Exchange Ratio',        'key': 'exchange_ratio',  'type': 'double'},
        ],
        "calc": calc_merger_arb_stock
    },
    "Going Private (LBO)": {
        "inputs": [
            {'label': 'Offer Price',           'key': 'offer_price',     'type': 'double'},
            {'label': 'Financing Secured?',    'key': 'financing_ok',    'type': 'bool'},
            {'label': 'Go-Shop End Date',      'key': 'goshop_date',     'type': 'date'},
        ],
        "calc": calc_lbo
    },
    "Tender Offer / Dutch Auction": {
        "inputs": [
            {'label': 'Tender Price',          'key': 'tender_price',    'type': 'double'},
            {'label': 'Min Price (Dutch)',      'key': 'min_price',       'type': 'double'},
            {'label': 'Max Price (Dutch)',      'key': 'max_price',       'type': 'double'},
        ],
        "calc": calc_tender_dutch
    },

    # --- Contingent Rights ---
    "Contingent Value Rights (CVR)": {
        "inputs": [
            {'label': 'Max Payout',            'key': 'max_payout',      'type': 'double'},
            {'label': 'Milestone Prob (%)',    'key': 'milestone_prob',  'type': 'double'},
            {'label': 'Expiration Date',       'key': 'expiry_date',     'type': 'date'},
        ],
        "calc": calc_cvr
    },
    "Litigation Arbitrage": {
        "inputs": [
            {'label': 'Claim Value',           'key': 'claim_value',     'type': 'double'},
            {'label': 'Legal Cost Est.',       'key': 'legal_cost',      'type': 'double'},
            {'label': 'Success Prob (%)',      'key': 'success_prob',    'type': 'double'},
        ],
        "calc": calc_litigation
    },

    # --- Restructuring & Spinoffs ---
    "Spin-off": {
        "inputs": [
            {'label': 'Parent Ticker',         'key': 'parent_ticker',   'type': 'text'},
            {'label': 'SpinCo Price (WI)',      'key': 'spinco_price',    'type': 'double'},
            {'label': 'Distribution Ratio',    'key': 'distribution_ratio', 'type': 'double'},
        ],
        "calc": calc_spinoff
    },
    "Split-off": {
        "inputs": [
            {'label': 'Sub/Split Price',       'key': 'sub_price',       'type': 'double'},
            {'label': 'Exchange Ratio',        'key': 'exchange_ratio',  'type': 'double'},
            {'label': 'Proration Est. (%)',    'key': 'proration_est',   'type': 'double'},
        ],
        "calc": calc_splitoff
    },
    "Equity Carve-out": {
        "inputs": [
            {'label': '% Sold in IPO',         'key': 'pct_sold',        'type': 'double'},
            {'label': 'Sub IPO Mkt Cap',       'key': 'ipo_val',         'type': 'double'},
            {'label': 'Parent Mkt Cap',        'key': 'parent_mcap',     'type': 'double'},
        ],
        "calc": calc_carve_out
    },

    # --- Capital Events ---
    "Rights Offering": {
        "inputs": [
            {'label': 'Subscription Price',    'key': 'subscription_price', 'type': 'double'},
            {'label': 'Rights per Share',      'key': 'rights_ratio',    'type': 'double'},
        ],
        "calc": calc_rights
    },
    "Odd Lot Tender": {
        "inputs": [
            {'label': 'Tender Price',          'key': 'tender_price',    'type': 'double'},
            {'label': 'Commissions',           'key': 'commissions',     'type': 'double'},
            {'label': 'Priority Confirmed?',   'key': 'priority',        'type': 'bool'},
        ],
        "calc": calc_odd_lot
    },
    "Special Dividend / Asset Sale": {
        "inputs": [
            {'label': 'Cash Dist. / Share',    'key': 'div_amount',      'type': 'double'},
            {'label': 'Stub Val (Min)',         'key': 'stub_est_min',    'type': 'double'},
            {'label': 'Stub Val (Max)',         'key': 'stub_est_max',    'type': 'double'},
        ],
        "calc": calc_special_dividend
    },
    "SPAC Arbitrage": {
        "inputs": [
            {'label': 'Trust Value / Share',   'key': 'trust_value',     'type': 'double'},
        ],
        "calc": calc_spac
    },

    # --- Distress & Liquidation ---
    "Liquidations": {
        "inputs": [
            {'label': 'Net Cash',              'key': 'net_cash',        'type': 'double'},
            {'label': 'Asset Value',           'key': 'assets',          'type': 'double'},
            {'label': 'Liabilities',           'key': 'liabilities',     'type': 'double'},
            {'label': 'Total Shares (M)',      'key': 'shares',          'type': 'double'},
        ],
        "calc": calc_liquidation
    },
    "Post-Bankruptcy (Emergence)": {
        "inputs": [
            {'label': 'New Equity Val',        'key': 'new_equity',      'type': 'double'},
            {'label': 'Recovery % (Old Eq)',   'key': 'recovery',        'type': 'double'},
        ],
        "calc": calc_post_bankruptcy
    },

    # --- Activist & Catalyst ---
    "Holding Discount / SOTP": {
        "inputs": [
            {'label': 'SOTP Total Value',      'key': 'sotp_total',      'type': 'double'},
            {'label': 'Holding Costs (PV)',    'key': 'holding_costs',   'type': 'double'},
        ],
        "calc": calc_holding_sotp
    },
    "Index Inclusion/Exclusion": {
        "inputs": [
            {'label': 'Post-Event Target',     'key': 'target_price',    'type': 'double'},
        ],
        "calc": calc_index_event
    },

    # --- Other ---
    "Generic": {
        "inputs": [
            {'label': 'Target Price',          'key': 'target_price',    'type': 'double'},
        ],
        "calc": calc_simple_target
    },
}

# ---------------------------------------------------------------------------
# ALIASES para compatibilidad con situaciones creadas antes de V2
# ---------------------------------------------------------------------------
TYPE_ALIASES = {
    # Nombres viejos -> nombre nuevo
    "Merger Arb Cash":          "Merger Arbitrage (Cash)",
    "Merger Arbitrage Cash":    "Merger Arbitrage (Cash)",
    "Merger Arb Stock":         "Merger Arbitrage (Stock)",
    "Merger Arbitrage Stock":   "Merger Arbitrage (Stock)",
    "Going Private":            "Going Private (LBO)",
    "Dutch Auction":            "Tender Offer / Dutch Auction",
    "CVR":                      "Contingent Value Rights (CVR)",
    "Spinoff":                   "Spin-off",
    "Splitoff":                  "Split-off",
    "Bankruptcy (Ch11)":        "Post-Bankruptcy (Emergence)",
    "Bankruptcy Ch11":          "Post-Bankruptcy (Emergence)",
    "Reverse Morris Trust":     "Spin-off",
    "Debt-Equity Swap":         "Generic",
    "Reflexivity":              "Generic",
    "Currency Arbitrage":       "Generic",
    "Dark Pool":                "Generic",
    "Reverse Stock Splits":     "Generic",
}

def resolve_type(raw_type):
    """Resuelve un nombre de tipo antiguo al nuevo canonical."""
    if raw_type in SITUATION_TYPES:
        return raw_type
    return TYPE_ALIASES.get(raw_type, "Generic")
