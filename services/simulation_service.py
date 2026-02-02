import pandas as pd
from schemas.simulation import SimulationParams, MonteCarloParams
from engine.core import SimulationConfig, run_deterministic
import copy

def map_to_engine_config(params: SimulationParams) -> SimulationConfig:
    """Convert Pydantic model to Engine Config"""
    return SimulationConfig(start_year=2025, **params.model_dump())

def format_results(records: list) -> dict:
    """Format engine results for API response"""
    if not records:
        return {'results': [], 'columns': []}
        
    df = pd.DataFrame(records)
    header = list(df.columns)
    
    results_json = []
    for _, row in df.iterrows():
        row_dict = {}
        for col in header:
            val = row[col]
            if pd.isna(val):
                row_dict[col] = None
            elif hasattr(val, 'item'):
                row_dict[col] = val.item()
            else:
                row_dict[col] = val
        results_json.append(row_dict)
        
    return {
        'results': results_json,
        'columns': header
    }

def run_simulation_service(params: SimulationParams):
    """
    Service to run both strategies and return formatted results.
    """
    config = map_to_engine_config(params)
    
    # Run Standard
    records_s = run_deterministic(config, strategy_name='standard')
    formatted_s = format_results(records_s)
    
    # Run Taxable First
    records_tf = run_deterministic(config, strategy_name='taxable_first')
    formatted_tf = format_results(records_tf)
    
    return {
        'success': True,
        'config': params.model_dump(),
        'scenarios': {
            'standard': formatted_s,
            'taxable_first': formatted_tf
        }
    }

def run_monte_carlo_service(params: MonteCarloParams):
    """
    Service to run Monte Carlo simulation.
    """
    config = map_to_engine_config(params)
    volatility = params.volatility
    num_sims = params.num_simulations
    
    runs = []
    success_count = 0
    
    for i in range(num_sims):
        # We pass volatility to run_deterministic which handles randomization internally per year
        # Note: The user requested a wrapper logic:
        # "randomized_config = apply_random_returns(config, volatility); run = ... "
        # However, typical Monte Carlo varies returns year-over-year inside the loop.
        # My engine/core.py implementation handles volatility inside the yearly loop.
        # So calling run_deterministic(..., volatility=v) is correct.
        
        sim_records = run_deterministic(config, strategy_name='standard', volatility=volatility)
        
        # Check Success (Net Worth > 0 at end)
        final_nw = sim_records[-1]['Net_Worth']
        if final_nw > 0:
            success_count += 1
            
        # Convert to DF for aggregation logic (reusing existing logic idea)
        df = pd.DataFrame(sim_records)
        df['Bal_Roth_Total'] = df['Bal_Roth_P1'] + df['Bal_Roth_P2']
        df['Bal_PreTax_Total'] = df['Bal_PreTax_P1'] + df['Bal_PreTax_P2']
        
        runs.append(df)

    success_rate = (success_count / num_sims) * 100
    
    # Aggregate Stats
    all_runs = pd.concat(runs)
    
    def p10(x): return x.quantile(0.10)
    def p25(x): return x.quantile(0.25)
    def p75(x): return x.quantile(0.75)
    def p90(x): return x.quantile(0.90)
    
    stats = all_runs.groupby('Year').agg({
        'Net_Worth': ['median', p10, p25, p75, p90],
        'Bal_Roth_Total': ['median', p10, p90],
        'Bal_PreTax_Total': ['median', p10, p90],
        'Bal_Taxable': ['median', p10, p90]
    }).reset_index()
    
    # Flatten columns
    stats.columns = ['_'.join(col).strip('_').replace('p10', 'P10').replace('p25', 'P25').replace('p75', 'P75').replace('p90', 'P90') 
                     for col in stats.columns.values]
    
    stats_json = stats.to_dict(orient='records')
    
    # Deterministic Baselines
    config_det = map_to_engine_config(params)
    base_s = format_results(run_deterministic(config_det, 'standard'))
    base_tf = format_results(run_deterministic(config_det, 'taxable_first'))
    
    # All Runs (for drill down)
    all_runs_json = []
    # Only return top 50 runs to avoid massive payloads if high sim count? 
    # Or simplified. Existing logic returned all. We keep it same.
    for i, df in enumerate(runs):
        all_runs_json.append({
            'run_id': i,
            'final_nw': float(df.iloc[-1]['Net_Worth']),
            'data': df.to_dict(orient='records')
        })
        
    return {
        'success': True,
        'success_rate': success_rate,
        'stats': stats_json,
        'all_runs': all_runs_json,
        'num_simulations': num_sims,
        'volatility': volatility,
        'baselines': {
            'standard': base_s,
            'taxable_first': base_tf
        }
    }
