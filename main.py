"""
Retirement Planner Web App - FastAPI Backend (Complete Migration)
Features:
- Multiple withdrawal strategies (standard, taxable_first)
- Monte Carlo simulation with volatility
- Real Estate & Mortgage support
- Full parameter validation
- Export/Import configuration
"""
import pandas as pd
import numpy as np
import os
import sys
import io
import shutil
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import the retirement planner class
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retirement_planner_yr import RetirementSimulator

app = FastAPI(
    title="Retirement Planner API",
    description="Complete retirement planning with Monte Carlo simulation and real estate support",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'csv'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
if os.path.exists("templates"):
    templates = Jinja2Templates(directory="templates")

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# Pydantic Models
# ============================================================================

class SimulationParams(BaseModel):
    """Complete simulation parameters with validation"""
    # Demographics
    p1_start_age: int = Field(ge=0, le=100)
    p2_start_age: int = Field(ge=0, le=100)
    end_simulation_age: int = Field(ge=0, le=120)
    inflation_rate: float = Field(ge=0, le=0.5)
    
    # Spending & Tax
    annual_spend_goal: float = Field(ge=0)
    filing_status: Optional[str] = 'MFJ'
    target_tax_bracket_rate: float = Field(ge=0, le=1, default=0.24)
    previous_year_taxes: Optional[float] = Field(ge=0, default=0)
    
    # Employment
    p1_employment_income: float = Field(ge=0, default=0)
    p1_employment_until_age: int = Field(ge=0, le=100, default=65)
    p2_employment_income: float = Field(ge=0, default=0)
    p2_employment_until_age: int = Field(ge=0, le=100, default=65)
    
    # Social Security
    p1_ss_amount: float = Field(ge=0, default=0)
    p1_ss_start_age: int = Field(ge=62, le=75, default=67)
    p2_ss_amount: float = Field(ge=0, default=0)
    p2_ss_start_age: int = Field(ge=62, le=75, default=67)
    
    # Pensions
    p1_pension: float = Field(ge=0, default=0)
    p1_pension_start_age: int = Field(ge=0, le=100, default=65)
    p2_pension: float = Field(ge=0, default=0)
    p2_pension_start_age: int = Field(ge=0, le=100, default=65)
    
    # Account Balances
    bal_taxable: float = Field(ge=0)
    bal_pretax_p1: float = Field(ge=0)
    bal_pretax_p2: float = Field(ge=0)
    bal_roth_p1: float = Field(ge=0)
    bal_roth_p2: float = Field(ge=0)
    
    # Growth Rates
    growth_rate_taxable: float = Field(ge=-0.5, le=0.5)
    growth_rate_pretax_p1: float = Field(ge=-0.5, le=0.5)
    growth_rate_pretax_p2: float = Field(ge=-0.5, le=0.5)
    growth_rate_roth_p1: float = Field(ge=-0.5, le=0.5)
    growth_rate_roth_p2: float = Field(ge=-0.5, le=0.5)
    taxable_basis_ratio: float = Field(ge=0, le=1)
    
    # Real Estate
    primary_home_value: Optional[float] = Field(ge=0, default=0)
    primary_home_growth_rate: Optional[float] = Field(ge=0, le=0.5, default=0.03)
    primary_home_mortgage_principal: Optional[float] = Field(ge=0, default=0)
    primary_home_mortgage_rate: Optional[float] = Field(ge=0, le=0.5, default=0)
    primary_home_mortgage_years: Optional[float] = Field(ge=0, le=50, default=0)
    
    # Rental Properties
    rental_1_value: Optional[float] = Field(ge=0, default=0)
    rental_1_income: Optional[float] = Field(ge=0, default=0)
    rental_1_growth_rate: Optional[float] = Field(ge=0, le=0.5, default=0.03)
    rental_1_income_growth_rate: Optional[float] = Field(ge=0, le=0.5, default=0.03)
    rental_1_mortgage_principal: Optional[float] = Field(ge=0, default=0)
    rental_1_mortgage_rate: Optional[float] = Field(ge=0, le=0.5, default=0)
    rental_1_mortgage_years: Optional[float] = Field(ge=0, le=50, default=0)
    
    rental_2_value: Optional[float] = Field(ge=0, default=0)
    rental_2_income: Optional[float] = Field(ge=0, default=0)
    rental_2_growth_rate: Optional[float] = Field(ge=0, le=0.5, default=0.03)
    rental_2_income_growth_rate: Optional[float] = Field(ge=0, le=0.5, default=0.03)
    rental_2_mortgage_principal: Optional[float] = Field(ge=0, default=0)
    rental_2_mortgage_rate: Optional[float] = Field(ge=0, le=0.5, default=0)
    rental_2_mortgage_years: Optional[float] = Field(ge=0, le=50, default=0)


class MonteCarloParams(SimulationParams):
    """Extends simulation params with Monte Carlo specific fields"""
    volatility: float = Field(ge=0, le=1, default=0.15)
    num_simulations: int = Field(ge=1, le=1000, default=100)


# ============================================================================
# Helper Functions
# ============================================================================

def params_to_csv(params: Dict[str, Any], filename: str) -> str:
    """Convert parameters dict to CSV config file"""
    records = []
    for k, v in params.items():
        # Include all values, even 0 and empty strings
        # Only skip if explicitly None
        if v is not None:
            records.append({'parameter': k, 'value': v})
    
    if not records:
        print(f"WARNING: No parameters to write to CSV. Received params: {params}")
        raise ValueError("No parameters provided for simulation")
    
    df = pd.DataFrame(records)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    df.to_csv(filepath, index=False)
    print(f"Created CSV with {len(records)} parameters at {filepath}")
    return filepath


def format_results(df: pd.DataFrame) -> Dict[str, Any]:
    """Format simulation results for JSON response"""
    results_json = []
    header = list(df.columns)
    
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


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page"""
    if os.path.exists("templates/index.html"):
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse(content="<h1>Retirement Planner API</h1><p>Use /docs for API documentation</p>")


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment"""
    return {"status": "healthy", "service": "retirement-planner-api"}


@app.post("/api/run-simulation")
async def run_simulation(
    request: Request,
    file: Optional[UploadFile] = File(None)
):
    """
    Run retirement simulation with BOTH strategies (standard and taxable_first).
    Supports:
    - CSV file upload
    - JSON body with parameters
    - Form data
    """
    config_file = None
    temp_file_created = False
    
    try:
        # Handle file upload
        if file and file.filename:
            if not allowed_file(file.filename):
                raise HTTPException(status_code=400, detail="Invalid file format")
            
            filename = os.path.basename(file.filename)
            config_file = os.path.join(UPLOAD_FOLDER, filename)
            
            with open(config_file, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_file_created = True
            
            # Persist as current config
            current_config_path = os.path.join(UPLOAD_FOLDER, 'current_config.csv')
            shutil.copy(config_file, current_config_path)
        
        # Handle JSON body
        elif request.headers.get("content-type", "").startswith("application/json"):
            json_body = await request.json()
            config_file = params_to_csv(json_body, 'temp_json_config.csv')
            temp_file_created = True
            
            # Persist
            current_config_path = os.path.join(UPLOAD_FOLDER, 'current_config.csv')
            shutil.copy(config_file, current_config_path)
        
        else:
            raise HTTPException(status_code=400, detail="No file or data provided")
        
        # Run BOTH strategies for comparison
        scenarios = {}
        
        # Standard strategy
        sim_standard = RetirementSimulator(config_file=config_file, year=2025, strategy='standard')
        results_standard = sim_standard.run()
        scenarios['standard'] = format_results(results_standard)
        
        # Taxable-first strategy
        sim_tf = RetirementSimulator(config_file=config_file, year=2025, strategy='taxable_first')
        results_tf = sim_tf.run()
        scenarios['taxable_first'] = format_results(results_tf)
        
        # Return config for form population
        config_dict = {}
        try:
            current_config_path = os.path.join(UPLOAD_FOLDER, 'current_config.csv')
            if os.path.exists(current_config_path):
                config_df = pd.read_csv(current_config_path)
                config_dict = dict(zip(config_df['parameter'], config_df['value']))
        except:
            pass
        
        return {
            'success': True,
            'config': config_dict,
            'scenarios': scenarios
        }
    
    except Exception as e:
        import traceback
        error_msg = f'Simulation failed: {str(e)}\n{traceback.format_exc()}'
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    finally:
        # Clean up temp files
        if temp_file_created and config_file and os.path.exists(config_file):
            try:
                # Keep current_config.csv, remove temp files
                if 'temp_' in config_file:
                    os.remove(config_file)
            except:
                pass


@app.post("/api/run-monte-carlo")
async def run_monte_carlo(request: Request):
    """
    Run Monte Carlo simulation with volatility.
    Returns:
    - Success rate
    - Percentile statistics (10th, 50th, 90th)
    - All individual runs
    - Baseline deterministic scenarios
    """
    try:
        json_body = await request.json()
        
        # Extract Monte Carlo params
        volatility = float(json_body.get('volatility', 0.15))
        num_sims = int(json_body.get('num_simulations', 100))
        
        # Create config file
        config_file = params_to_csv(json_body, 'temp_mc_config.csv')
        
        runs = []
        success_count = 0
        
        # Run Monte Carlo simulations
        for _ in range(num_sims):
            sim = RetirementSimulator(config_file=config_file, year=2025, strategy='standard')
            results = sim.run(volatility=volatility)
            
            # Check success (Net Worth > 0 at end)
            final_nw = results.iloc[-1]['Net_Worth']
            if final_nw > 0:
                success_count += 1
            
            # Add totals for stats
            results['Bal_Roth_Total'] = results['Bal_Roth_P1'] + results['Bal_Roth_P2']
            results['Bal_PreTax_Total'] = results['Bal_PreTax_P1'] + results['Bal_PreTax_P2']
            
            runs.append(results)
        
        success_rate = (success_count / num_sims) * 100
        
        # Aggregate statistics
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
        stats.columns = ['_'.join(col).strip('_').replace('p10', 'P10').replace('p25', 'P25').replace('p75', 'P75').replace('p90', 'P90') for col in stats.columns.values]
        stats_json = stats.to_dict(orient='records')
        
        # Run deterministic baselines
        baselines = {}
        sim_s = RetirementSimulator(config_file=config_file, year=2025, strategy='standard')
        baselines['standard'] = format_results(sim_s.run())
        sim_tf = RetirementSimulator(config_file=config_file, year=2025, strategy='taxable_first')
        baselines['taxable_first'] = format_results(sim_tf.run())
        
        # All runs for drill-down
        all_runs_json = []
        for i, df in enumerate(runs):
            run_data = df.to_dict(orient='records')
            all_runs_json.append({
                'run_id': i,
                'final_nw': float(df.iloc[-1]['Net_Worth']),
                'data': run_data
            })
        
        # Clean up
        if os.path.exists(config_file):
            os.remove(config_file)
        
        return {
            'success': True,
            'success_rate': success_rate,
            'stats': stats_json,
            'all_runs': all_runs_json,
            'num_simulations': num_sims,
            'volatility': volatility,
            'baselines': baselines
        }
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export-config")
async def export_config(data: Dict[str, Any]):
    """Export current form data as CSV file"""
    try:
        # Define all possible fields
        fields = [
            'p1_name', 'p2_name',
            'p1_start_age', 'p2_start_age', 'end_simulation_age',
            'inflation_rate', 'annual_spend_goal', 'filing_status',
            'p1_employment_income', 'p1_employment_until_age',
            'p2_employment_income', 'p2_employment_until_age',
            'p1_ss_amount', 'p1_ss_start_age',
            'p2_ss_amount', 'p2_ss_start_age',
            'p1_pension', 'p1_pension_start_age',
            'p2_pension', 'p2_pension_start_age',
            'bal_taxable', 'bal_pretax_p1', 'bal_pretax_p2', 'bal_roth_p1', 'bal_roth_p2',
            'growth_rate_taxable', 'growth_rate_pretax_p1', 'growth_rate_pretax_p2', 'growth_rate_roth_p1', 'growth_rate_roth_p2',
            'taxable_basis_ratio', 'target_tax_bracket_rate', 'previous_year_taxes',
            'primary_home_value', 'primary_home_growth_rate',
            'primary_home_mortgage_principal', 'primary_home_mortgage_rate', 'primary_home_mortgage_years',
            'rental_1_value', 'rental_1_income', 'rental_1_growth_rate', 'rental_1_income_growth_rate',
            'rental_1_mortgage_principal', 'rental_1_mortgage_rate', 'rental_1_mortgage_years',
            'rental_2_value', 'rental_2_income', 'rental_2_growth_rate', 'rental_2_income_growth_rate',
            'rental_2_mortgage_principal', 'rental_2_mortgage_rate', 'rental_2_mortgage_years'
        ]
        
        records = []
        for field in fields:
            val = data.get(field, 0)
            records.append({'parameter': field, 'value': val})
        
        df = pd.DataFrame(records)
        
        # Create CSV in memory
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=retirement_config.csv"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get-current-config")
async def get_current_config():
    """Get the currently saved configuration"""
    try:
        current_config_path = os.path.join(UPLOAD_FOLDER, 'current_config.csv')
        
        if not os.path.exists(current_config_path):
            return {}
        
        df = pd.read_csv(current_config_path)
        config_dict = dict(zip(df['parameter'], df['value']))
        
        return config_dict
    
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


@app.get("/api/sample-config")
async def get_sample_config():
    """Return the sample configuration"""
    try:
        sample_df = pd.read_csv('nisha.csv')
        config_data = sample_df.to_dict(orient='records')
        return {
            'success': True,
            'config': config_data
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Sample config not found')


@app.get("/download-template")
async def download_template():
    """Download sample CSV template"""
    file_path = "nisha.csv"
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            filename="retirement_planner_template.csv",
            media_type='text/csv'
        )
    else:
        raise HTTPException(status_code=404, detail='Template file not found')


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)
