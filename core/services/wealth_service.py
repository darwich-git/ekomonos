import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.database import DB_PATH, MonthlySnapshot, AccountBalance, Account, IncomeRecord

class WealthService:
    """
    Service layer for Wealth Analytics (F7).
    Handles all the complex SQL math for calculating Net Worth, Cashflow,
    asset allocations across Family, Rafa, and Cris profiles.
    Returns plain dictionaries for the UI to paint without knowing DB mechanics.
    """
    def __init__(self):
        # We spawn engines locally to avoid multithreading issues in Qt
        self.db_url = f"sqlite:///{DB_PATH}"

    def get_overview_data(self, owner_name: str) -> dict:
        """
        Returns a dictionary containing all KPIs and historical series
        for the Main Dashboard in F7.
        """
        engine = create_engine(self.db_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        result = {
            'error': False,
            'kpis': {
                'total_nw': 0, 'total_cash': 0, 'total_ibkr': 0, 'total_fund': 0,
                'inc_month': 0, 'inc_ytd': 0, 'exp_month': 0, 'exp_ytd': 0,
                'ytd_savings': 0, 'month_savings': 0,
                'nw_cagr': 0, 'nw_growth_monthly': 0,
                'latest_snap_month': ""
            },
            'charts': {
                'history_x': [], 'history_nw': [], 'months_labels': [],
                'pie': {'cash': 0, 'ibkr': 0, 'fund': 0, 'house': 0}
            }
        }

        try:
            snaps = session.query(MonthlySnapshot).order_by(MonthlySnapshot.month_id.asc()).all()
            if not snaps:
                result['error'] = True
                return result

            result['charts']['months_labels'] = [snap.month_id for snap in snaps]
            all_accounts = {a.id: a for a in session.query(Account).all()}
            
            history_x = []
            history_nw = []
            
            latest_nws = {}
            latest_cash = {}
            latest_ibkr = {}
            latest_fund = {}
            latest_snap_month = ""
            
            dist_cash = 0; dist_ibkr = 0; dist_fund = 0; dist_house = 0

            for i, snap in enumerate(snaps):
                bals = session.query(AccountBalance).filter_by(snapshot_id=snap.id).all()
                house = 0; mort = 0; ap_rafa = 0; ap_cris = 0; real_debt = 0
                nws = {'Rafa': 0, 'Cris': 0, 'Comun': 0}
                cash = {'Rafa': 0, 'Cris': 0, 'Comun': 0}
                ibkr = {'Rafa': 0, 'Cris': 0}
                fund = {'Rafa': 0, 'Cris': 0}
                
                for b in bals:
                    acc = all_accounts.get(b.account_id)
                    if not acc: continue
                    val = b.current_value or 0
                    
                    if acc.type == 'real_estate': house += val; nws['Comun'] += val
                    elif acc.type == 'mortgage': mort += val; nws['Comun'] -= val
                    elif 'aportado hipoteca rafa' in acc.name.lower(): ap_rafa += val
                    elif 'aportado hipoteca cris' in acc.name.lower(): ap_cris += val
                    elif 'deuda equity' in acc.name.lower() or 'interna rafa' in acc.name.lower(): real_debt += val
                    else:
                        if acc.type == 'equity': continue
                        owner_group = acc.owner if acc.owner in ['Rafa', 'Cris'] else 'Comun'
                        nws[owner_group] += val
                        
                        if acc.type in ['cash', 'bank'] or 'monetario' in acc.name.lower(): cash[owner_group] += val
                        elif 'ibkr' in acc.name.lower(): ibkr[owner_group] += val
                        elif 'fundsmith' in acc.name.lower():
                            if owner_group in ['Rafa', 'Cris']: fund[owner_group] += val
                
                half_house = (house - mort) / 2
                if real_debt == 0 and (ap_rafa > 0 or ap_cris > 0):
                    calc_debt = (ap_cris - ap_rafa) / 2
                    nws['Rafa'] -= calc_debt; nws['Cris'] += calc_debt
                else:
                    nws['Rafa'] -= real_debt; nws['Cris'] += real_debt

                nws['Rafa'] += half_house; nws['Cris'] += half_house
                
                if owner_name == 'Rafa': nw = nws['Rafa']
                elif owner_name == 'Cris': nw = nws['Cris']
                else: nw = nws['Rafa'] + nws['Cris']
                
                history_x.append(i)
                history_nw.append(nw)
                
                if i == len(snaps) - 1:
                    latest_nws = nws; latest_cash = cash; latest_ibkr = ibkr; latest_fund = fund
                    latest_snap_month = snap.month_id
                    if owner_name == 'Rafa':
                        dist_cash = cash['Rafa']; dist_ibkr = ibkr['Rafa']; dist_fund = fund['Rafa']; dist_house = half_house
                    elif owner_name == 'Cris':
                        dist_cash = cash['Cris']; dist_ibkr = ibkr['Cris']; dist_fund = fund['Cris']; dist_house = half_house
                    else:
                        dist_cash = cash['Rafa'] + cash['Cris'] + cash['Comun']
                        dist_ibkr = ibkr['Rafa'] + ibkr['Cris']
                        dist_fund = fund['Rafa'] + fund['Cris']
                        dist_house = (house - mort)

            # Incomes/Expenses
            current_year = latest_snap_month.split('-')[0] if latest_snap_month != "" else str(datetime.datetime.now().year)
            latest_m = latest_snap_month if latest_snap_month != "" else f"{current_year}-01"
            
            incomes_db = session.query(IncomeRecord).all()
            monthly_incomes = {}
            for inc in incomes_db:
                if inc.month_id not in monthly_incomes:
                    monthly_incomes[inc.month_id] = {"Rafa": 0, "Cris": 0, "Gastos_Rafa": 0, "Gastos_Cris": 0}
                monthly_incomes[inc.month_id][inc.owner] = (inc.net_amount or 0)
                monthly_incomes[inc.month_id][f"Gastos_{inc.owner}"] = (inc.total_expenses or 0)
                
            inc_ytd = 0; exp_ytd = 0; inc_month = 0; exp_month = 0
            for m, vals in monthly_incomes.items():
                if m.startswith(current_year):
                    if owner_name == 'Rafa': i_val = vals['Rafa']; e_val = vals['Gastos_Rafa']
                    elif owner_name == 'Cris': i_val = vals['Cris']; e_val = vals['Gastos_Cris']
                    else:
                        i_val = vals['Rafa'] + vals['Cris']
                        c_exp = 0
                        s = session.query(MonthlySnapshot).filter_by(month_id=m).first()
                        if s: c_exp = s.comun_expenses or 0
                        e_val = vals['Gastos_Rafa'] + vals['Gastos_Cris'] + c_exp
                    inc_ytd += i_val; exp_ytd += e_val
                    if m == latest_m: inc_month = i_val; exp_month = e_val

            ytd_savings = ((inc_ytd - exp_ytd) / inc_ytd) * 100 if inc_ytd > 0 else 0
            month_savings = ((inc_month - exp_month) / inc_month) * 100 if inc_month > 0 else 0
            
            if owner_name == 'Rafa':
                total_nw, total_cash, total_ibkr, total_fund = latest_nws.get('Rafa',0), latest_cash.get('Rafa',0), latest_ibkr.get('Rafa',0), latest_fund.get('Rafa',0)
            elif owner_name == 'Cris':
                total_nw, total_cash, total_ibkr, total_fund = latest_nws.get('Cris',0), latest_cash.get('Cris',0), latest_ibkr.get('Cris',0), latest_fund.get('Cris',0)
            else:
                total_nw = latest_nws.get('Rafa',0) + latest_nws.get('Cris',0)
                total_cash = latest_cash.get('Rafa',0) + latest_cash.get('Cris',0) + latest_cash.get('Comun',0)
                total_ibkr = latest_ibkr.get('Rafa',0) + latest_ibkr.get('Cris',0)
                total_fund = latest_fund.get('Rafa',0) + latest_fund.get('Cris',0)

            nw_growth_monthly = 0; nw_cagr = 0
            if len(history_nw) > 1 and history_nw[-2] != 0:
                nw_growth_monthly = (history_nw[-1] - history_nw[-2]) / history_nw[-2] * 100
            if len(history_nw) > 1 and history_nw[0] != 0:
                years = len(history_nw) / 12.0
                if years > 0:
                    try: nw_cagr = (((history_nw[-1] / history_nw[0]) ** (1 / years)) - 1) * 100
                    except: nw_cagr = 0

            # Store in result schema
            kpis = result['kpis']
            kpis['total_nw'] = total_nw; kpis['total_cash'] = total_cash; kpis['total_ibkr'] = total_ibkr; kpis['total_fund'] = total_fund
            kpis['inc_month'] = inc_month; kpis['exp_month'] = exp_month; kpis['inc_ytd'] = inc_ytd; kpis['exp_ytd'] = exp_ytd
            kpis['ytd_savings'] = ytd_savings; kpis['month_savings'] = month_savings; kpis['nw_cagr'] = nw_cagr; kpis['nw_growth_monthly'] = nw_growth_monthly
            kpis['latest_snap_month'] = latest_snap_month
            kpis['cashflow_month'] = inc_month - exp_month
            
            charts = result['charts']
            charts['history_x'] = history_x
            charts['history_nw'] = history_nw
            charts['pie']['cash'] = dist_cash; charts['pie']['ibkr'] = dist_ibkr; charts['pie']['fund'] = dist_fund; charts['pie']['house'] = dist_house

        except Exception as e:
            print(f"[WealthService.get_overview_data] Error: {e}")
            result['error'] = True
        finally:
            session.close()

        return result

    def get_detail_series(self, category_id: str, owner_name: str) -> dict:
        """
        Returns { 'timestamps': [ts1, ts2], 'data': [val1, val2] }
        """
        engine = create_engine(self.db_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        result = { 'error': False, 'timestamps': [], 'data': [], 'cagr_total': 0, 'cagr_ytd': 0, 'cagr_1m': 0 }

        try:
            snaps = session.query(MonthlySnapshot).order_by(MonthlySnapshot.month_id.asc()).all()
            if not snaps:
                result['error'] = True
                return result

            all_accounts = {a.id: a for a in session.query(Account).all()}
            timestamps = []
            for c in [snap.month_id for snap in snaps]:
                y_str, m_str = c.split('-')
                dt = datetime.datetime(int(y_str), int(m_str), 1)
                timestamps.append(int(dt.timestamp() * 1000))
            
            monthly_incomes = {}
            for inc in session.query(IncomeRecord).all():
                if inc.month_id not in monthly_incomes:
                    monthly_incomes[inc.month_id] = {"Rafa": 0, "Cris": 0, "Gastos_Rafa": 0, "Gastos_Cris": 0}
                monthly_incomes[inc.month_id][inc.owner] = (inc.net_amount or 0)
                monthly_incomes[inc.month_id][f"Gastos_{inc.owner}"] = (inc.total_expenses or 0)

            data = []
            
            if category_id == "net_worth":
                for i, snap in enumerate(snaps):
                    bals = session.query(AccountBalance).filter_by(snapshot_id=snap.id).all()
                    nw = 0; house = 0; mort = 0; ap_rafa = 0; ap_cris = 0; real_debt = 0
                    for b in bals:
                        acc = all_accounts.get(b.account_id)
                        if not acc: continue
                        if acc.type == 'equity' and 'aportado' not in acc.name.lower(): continue
                        val = b.current_value or 0
                        
                        if acc.type == 'real_estate': house += val
                        elif acc.type == 'mortgage': mort += val
                        elif 'aportado hipoteca rafa' in acc.name.lower(): ap_rafa += val
                        elif 'aportado hipoteca cris' in acc.name.lower(): ap_cris += val
                        elif 'deuda equity' in acc.name.lower() or 'interna rafa' in acc.name.lower(): real_debt += val
                        else:
                            if acc.type == 'equity': continue
                            owner_group = acc.owner if acc.owner in ['Rafa', 'Cris'] else 'Comun'
                            if owner_name in ['Family', owner_group]: nw += val
                                
                    calc_debt = (ap_cris - ap_rafa) / 2 if real_debt == 0 and (ap_rafa > 0 or ap_cris > 0) else real_debt
                    if owner_name == 'Family': nw += (house - mort)
                    elif owner_name == 'Rafa': nw += (house - mort) / 2 - calc_debt
                    elif owner_name == 'Cris': nw += (house - mort) / 2 + calc_debt
                        
                    data.append(nw)

            elif category_id == "cash":
                for snap in snaps:
                    val = sum(b.current_value for b in session.query(AccountBalance).filter_by(snapshot_id=snap.id).all() 
                            if all_accounts.get(b.account_id) and all_accounts[b.account_id].type in ['cash', 'bank']
                            and (owner_name == 'Family' or all_accounts[b.account_id].owner in [owner_name, 'Comun']))
                    data.append(val)
                    
            elif category_id == "ibkr":
                for snap in snaps:
                    val = sum(b.current_value for b in session.query(AccountBalance).filter_by(snapshot_id=snap.id).all() 
                            if all_accounts.get(b.account_id) and 'ibkr' in all_accounts[b.account_id].name.lower()
                            and (owner_name == 'Family' or all_accounts[b.account_id].owner == owner_name))
                    data.append(val)
                    
            elif category_id == "fundsmith":
                for snap in snaps:
                    val = sum(b.current_value for b in session.query(AccountBalance).filter_by(snapshot_id=snap.id).all() 
                            if all_accounts.get(b.account_id) and ('fundsmith' in all_accounts[b.account_id].name.lower() or all_accounts[b.account_id].type == 'fund')
                            and (owner_name == 'Family' or all_accounts[b.account_id].owner == owner_name))
                    data.append(val)

            elif category_id == "savings":
                for snap in snaps:
                    inc_obj = monthly_incomes.get(snap.month_id, {})
                    if owner_name == 'Rafa': i_v = inc_obj.get('Rafa',0); e_v = inc_obj.get('Gastos_Rafa',0)
                    elif owner_name == 'Cris': i_v = inc_obj.get('Cris',0); e_v = inc_obj.get('Gastos_Cris',0)
                    else: i_v = inc_obj.get('Rafa',0)+inc_obj.get('Cris',0); e_v = inc_obj.get('Gastos_Rafa',0)+inc_obj.get('Gastos_Cris',0)+snap.comun_expenses
                    data.append(((i_v - e_v) / i_v * 100) if i_v > 0 else 0)

            elif category_id == "cashflow":
                for snap in snaps:
                    inc_obj = monthly_incomes.get(snap.month_id, {})
                    if owner_name == 'Rafa': i_v = inc_obj.get('Rafa',0); e_v = inc_obj.get('Gastos_Rafa',0)
                    elif owner_name == 'Cris': i_v = inc_obj.get('Cris',0); e_v = inc_obj.get('Gastos_Cris',0)
                    else: i_v = inc_obj.get('Rafa',0)+inc_obj.get('Cris',0); e_v = inc_obj.get('Gastos_Rafa',0)+inc_obj.get('Gastos_Cris',0)+snap.comun_expenses
                    data.append(i_v - e_v)
            else:
                data = [0]*len(snaps)

            # Calculations CAGR
            if len(data) > 0 and data[0] != 0:
                y_tot = len(data)/12.0
                if y_tot > 0:
                    try: result['cagr_total'] = (((data[-1]/data[0])**(1/y_tot))-1)*100
                    except: pass
            if len(data) > 1 and data[-2] != 0:
                result['cagr_1m'] = ((data[-1] - data[-2])/data[-2])*100
                
            ytd_idx = -1
            current_y = snaps[-1].month_id.split('-')[0]
            for i, snap in enumerate(snaps):
                if snap.month_id.startswith(current_y):
                    ytd_idx = i - 1
                    break
            
            if ytd_idx >= 0 and data[ytd_idx] != 0:
                result['cagr_ytd'] = ((data[-1] - data[ytd_idx])/data[ytd_idx])*100
            
            result['timestamps'] = timestamps
            result['data'] = data

        except Exception as e:
            print(f"[WealthService.get_detail_series] Error: {e}")
            result['error'] = True
        finally:
            session.close()

        return result
