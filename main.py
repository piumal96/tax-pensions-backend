"""
Retirement Planner Web App - FastAPI Backend
"""
import pandas as pd
import os
import sys
import io
import shutil
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import the retirement planner class
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retirement_planner_yr import RetirementSimulator

app = FastAPI(title="Retirement Planner")

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
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page with upload and form options"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/run-simulation")
async def run_simulation(
    request: Request,
    file: Optional[UploadFile] = File(None),
    # Form fields - using Form(...) for each field as FastAPI doesn't automatically group them
    p1_start_age: Optional[str] = Form(None),
    p2_start_age: Optional[str] = Form(None),
    end_simulation_age: Optional[str] = Form(None),
    inflation_rate: Optional[str] = Form(None),
    annual_spend_goal: Optional[str] = Form(None),
    p1_employment_income: Optional[str] = Form(None),
    p1_employment_until_age: Optional[str] = Form(None),
    p2_employment_income: Optional[str] = Form(None),
    p2_employment_until_age: Optional[str] = Form(None),
    p1_ss_amount: Optional[str] = Form(None),
    p1_ss_start_age: Optional[str] = Form(None),
    p2_ss_amount: Optional[str] = Form(None),
    p2_ss_start_age: Optional[str] = Form(None),
    p1_pension: Optional[str] = Form(None),
    p1_pension_start_age: Optional[str] = Form(None),
    p2_pension: Optional[str] = Form(None),
    p2_pension_start_age: Optional[str] = Form(None),
    bal_taxable: Optional[str] = Form(None),
    bal_pretax_p1: Optional[str] = Form(None),
    bal_pretax_p2: Optional[str] = Form(None),
    bal_roth_p1: Optional[str] = Form(None),
    bal_roth_p2: Optional[str] = Form(None),
    growth_rate_taxable: Optional[str] = Form(None),
    growth_rate_pretax_p1: Optional[str] = Form(None),
    growth_rate_pretax_p2: Optional[str] = Form(None),
    growth_rate_roth_p1: Optional[str] = Form(None),
    growth_rate_roth_p2: Optional[str] = Form(None),
    taxable_basis_ratio: Optional[str] = Form(None),
    target_tax_bracket_rate: Optional[str] = Form(None),
):
    """
    Handle both CSV upload and form input to run simulation.
    """
    config_file = None
    temp_file_created = False
    
    try:
        # Check if file was uploaded
        if file and file.filename:
            if not allowed_file(file.filename):
                return JSONResponse(
                    status_code=400,
                    content={'error': 'Invalid file format. Please upload a CSV file.'}
                )
            
            # Save uploaded file temporarily
            filename = file.filename # In FastAPI secure_filename is not built-in but we can just use the name or UUID
            # Simple sanitization
            filename = os.path.basename(filename)
            config_file = os.path.join(UPLOAD_FOLDER, filename)
            
            with open(config_file, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_file_created = True

        # Check if form data was submitted (if no file)
        elif request.headers.get("content-type", "").startswith("application/json"):
             # Handle JSON POST request
             try:
                json_body = await request.json()
                # Create a dictionary of all form values from JSON
                # Reuse the logic below by populating form_mapping logic here or refactoring
                # For simplicity, we will adapt the logic to handle both sources
                
                # Reuse mapping logic
                params = []
                values = []
                descriptions = []
                
                # Define mapping (same as below)
                form_mapping = {
                    'p1_start_age': ('p1_start_age', 'Person 1 Current Age'),
                    'p2_start_age': ('p2_start_age', 'Person 2 Current Age'),
                    'end_simulation_age': ('end_simulation_age', 'Age when simulation stops'),
                    'inflation_rate': ('inflation_rate', 'Annual inflation rate'),
                    'annual_spend_goal': ('annual_spend_goal', 'Annual spending goal'),
                    'p1_employment_income': ('p1_employment_income', 'P1 Annual Employment Income'),
                    'p1_employment_until_age': ('p1_employment_until_age', 'P1 Works until this age'),
                    'p2_employment_income': ('p2_employment_income', 'P2 Annual Employment Income'),
                    'p2_employment_until_age': ('p2_employment_until_age', 'P2 Works until this age'),
                    'p1_ss_amount': ('p1_ss_amount', 'P1 Social Security Annual Amount'),
                    'p1_ss_start_age': ('p1_ss_start_age', 'P1 Age SS begins'),
                    'p2_ss_amount': ('p2_ss_amount', 'P2 Social Security Annual Amount'),
                    'p2_ss_start_age': ('p2_ss_start_age', 'P2 Age SS begins'),
                    'p1_pension': ('p1_pension', 'P1 Annual Pension'),
                    'p1_pension_start_age': ('p1_pension_start_age', 'P1 Pension Start Age'),
                    'p2_pension': ('p2_pension', 'P2 Annual Pension'),
                    'p2_pension_start_age': ('p2_pension_start_age', 'P2 Pension Start Age'),
                    'bal_taxable': ('bal_taxable', 'Joint Taxable Account Balance'),
                    'bal_pretax_p1': ('bal_pretax_p1', 'P1 Pre-Tax Balance'),
                    'bal_pretax_p2': ('bal_pretax_p2', 'P2 Pre-Tax Balance'),
                    'bal_roth_p1': ('bal_roth_p1', 'P1 Roth IRA Balance'),
                    'bal_roth_p2': ('bal_roth_p2', 'P2 Roth IRA Balance'),
                    'growth_rate_taxable': ('growth_rate_taxable', 'Annual return on Taxable Account'),
                    'growth_rate_pretax_p1': ('growth_rate_pretax_p1', 'Annual return on P1 Pre-Tax'),
                    'growth_rate_pretax_p2': ('growth_rate_pretax_p2', 'Annual return on P2 Pre-Tax'),
                    'growth_rate_roth_p1': ('growth_rate_roth_p1', 'Annual return on P1 Roth'),
                    'growth_rate_roth_p2': ('growth_rate_roth_p2', 'Annual return on P2 Roth'),
                    'taxable_basis_ratio': ('taxable_basis_ratio', 'Fraction of Taxable withdrawal that is basis'),
                    'target_tax_bracket_rate': ('target_tax_bracket_rate', 'Target bracket for Roth conversions'),
                }
                
                # Extract keys from mapping
                form_mapping_values = {k: v[0] for k,v in form_mapping.items()}
                
                for key, val in json_body.items():
                     if key in form_mapping_values and val is not None:
                         params.append(form_mapping_values[key])
                         values.append(str(val))
                         descriptions.append('')
                
                if params:
                    config_df = pd.DataFrame({
                        'parameter': params,
                        'value': values,
                        'description': descriptions
                    })
                    config_file = os.path.join(UPLOAD_FOLDER, 'temp_json_config.csv')
                    config_df.to_csv(config_file, index=False)
                    temp_file_created = True

             except Exception as e:
                 print(f"JSON Parse Error: {e}")
                 pass 

            
        else:
            # Construct params from the Form arguments
            # Create a dictionary of all form values
            form_values = {
                'p1_start_age': p1_start_age,
                'p2_start_age': p2_start_age,
                'end_simulation_age': end_simulation_age,
                'inflation_rate': inflation_rate,
                'annual_spend_goal': annual_spend_goal,
                'p1_employment_income': p1_employment_income,
                'p1_employment_until_age': p1_employment_until_age,
                'p2_employment_income': p2_employment_income,
                'p2_employment_until_age': p2_employment_until_age,
                'p1_ss_amount': p1_ss_amount,
                'p1_ss_start_age': p1_ss_start_age,
                'p2_ss_amount': p2_ss_amount,
                'p2_ss_start_age': p2_ss_start_age,
                'p1_pension': p1_pension,
                'p1_pension_start_age': p1_pension_start_age,
                'p2_pension': p2_pension,
                'p2_pension_start_age': p2_pension_start_age,
                'bal_taxable': bal_taxable,
                'bal_pretax_p1': bal_pretax_p1,
                'bal_pretax_p2': bal_pretax_p2,
                'bal_roth_p1': bal_roth_p1,
                'bal_roth_p2': bal_roth_p2,
                'growth_rate_taxable': growth_rate_taxable,
                'growth_rate_pretax_p1': growth_rate_pretax_p1,
                'growth_rate_pretax_p2': growth_rate_pretax_p2,
                'growth_rate_roth_p1': growth_rate_roth_p1,
                'growth_rate_roth_p2': growth_rate_roth_p2,
                'taxable_basis_ratio': taxable_basis_ratio,
                'target_tax_bracket_rate': target_tax_bracket_rate,
            }
            
            # Filter None values
            active_params = {k: v for k, v in form_values.items() if v is not None}
            
            if active_params:
                params = []
                values = []
                descriptions = []
                
                form_mapping = {
                    'p1_start_age': ('p1_start_age', 'Person 1 Current Age'),
                    'p2_start_age': ('p2_start_age', 'Person 2 Current Age'),
                    'end_simulation_age': ('end_simulation_age', 'Age when simulation stops'),
                    'inflation_rate': ('inflation_rate', 'Annual inflation rate'),
                    'annual_spend_goal': ('annual_spend_goal', 'Annual spending goal'),
                    'p1_employment_income': ('p1_employment_income', 'P1 Annual Employment Income'),
                    'p1_employment_until_age': ('p1_employment_until_age', 'P1 Works until this age'),
                    'p2_employment_income': ('p2_employment_income', 'P2 Annual Employment Income'),
                    'p2_employment_until_age': ('p2_employment_until_age', 'P2 Works until this age'),
                    'p1_ss_amount': ('p1_ss_amount', 'P1 Social Security Annual Amount'),
                    'p1_ss_start_age': ('p1_ss_start_age', 'P1 Age SS begins'),
                    'p2_ss_amount': ('p2_ss_amount', 'P2 Social Security Annual Amount'),
                    'p2_ss_start_age': ('p2_ss_start_age', 'P2 Age SS begins'),
                    'p1_pension': ('p1_pension', 'P1 Annual Pension'),
                    'p1_pension_start_age': ('p1_pension_start_age', 'P1 Pension Start Age'),
                    'p2_pension': ('p2_pension', 'P2 Annual Pension'),
                    'p2_pension_start_age': ('p2_pension_start_age', 'P2 Pension Start Age'),
                    'bal_taxable': ('bal_taxable', 'Joint Taxable Account Balance'),
                    'bal_pretax_p1': ('bal_pretax_p1', 'P1 Pre-Tax Balance'),
                    'bal_pretax_p2': ('bal_pretax_p2', 'P2 Pre-Tax Balance'),
                    'bal_roth_p1': ('bal_roth_p1', 'P1 Roth IRA Balance'),
                    'bal_roth_p2': ('bal_roth_p2', 'P2 Roth IRA Balance'),
                    'growth_rate_taxable': ('growth_rate_taxable', 'Annual return on Taxable Account'),
                    'growth_rate_pretax_p1': ('growth_rate_pretax_p1', 'Annual return on P1 Pre-Tax'),
                    'growth_rate_pretax_p2': ('growth_rate_pretax_p2', 'Annual return on P2 Pre-Tax'),
                    'growth_rate_roth_p1': ('growth_rate_roth_p1', 'Annual return on P1 Roth'),
                    'growth_rate_roth_p2': ('growth_rate_roth_p2', 'Annual return on P2 Roth'),
                    'taxable_basis_ratio': ('taxable_basis_ratio', 'Fraction of Taxable withdrawal that is basis'),
                    'target_tax_bracket_rate': ('target_tax_bracket_rate', 'Target bracket for Roth conversions'),
                }
                
                for key, val in active_params.items():
                    if key in form_mapping:
                        param_name, desc = form_mapping[key]
                        params.append(param_name)
                        values.append(val)
                        descriptions.append(desc)
                
                config_df = pd.DataFrame({
                    'parameter': params,
                    'value': values,
                    'description': descriptions
                })
                
                config_file = os.path.join(UPLOAD_FOLDER, 'temp_form_config.csv')
                config_df.to_csv(config_file, index=False)
                temp_file_created = True
                
            # Fallback for JSON body if Form fields are empty
            elif 'application/json' in request.headers.get('content-type', ''):
                 # We can't easily read body again if it was consumed, but Starlette Request allows it
                 # However, better to rely on a separate Pydantic model for JSON requests.
                 # Let's just handle the "JSON with form parameters" case if the UI sends it like that.
                 # For simplicity in this migration, if the frontend sends FormData, we are good.
                 # If it sends JSON, we need to read it.
                 try:
                    json_body = await request.json()
                    # Re-use logic for JSON
                    params = []
                    values = []
                    
                    # Reuse mapping...
                    form_mapping_values = {k: v[0] for k,v in form_mapping.items()}
                     
                    # The Flask code had a slightly different mapping for JSON, checking...
                    # It was essentially the same keys.
                    
                    for key, val in json_body.items():
                         if key in form_mapping_values and val is not None:
                             params.append(form_mapping_values[key])
                             values.append(str(val))
                    
                    if params:
                        config_file = os.path.join(UPLOAD_FOLDER, 'temp_json_config.csv')
                        config_df = pd.DataFrame({
                            'parameter': params,
                            'value': values,
                            'description': [''] * len(params)
                        })
                        config_df.to_csv(config_file, index=False)
                        temp_file_created = True

                 except Exception:
                     pass # Not JSON or failed to parse

        if not config_file:
             return JSONResponse(status_code=400, content={'error': 'No file or data provided.'})

        # Run the simulation
        try:
            # We want to run this in a threadpool because it's CPU bound (and uses pandas)
            # FastAPI runs async functions in the event loop, so blocking code creates issues.
            # But run_simulation logic is synchronous. 
            # We can define this route as 'def' instead of 'async def' to run in threadpool,
            # BUT we need 'await request.json()' above.
            # So we keep it async and might block briefly or we can use run_in_executor if valid.
            # For simplicity, let's keep it here, assuming simulation is fast enough.
            
            sim = RetirementSimulator(config_file=config_file, year=2025)
            results_df = sim.run()
            
            # Reorder columns to match web display order
            display_columns = [
                'Year', 'P1_Age', 'P2_Age', 'Employment_P1', 'Employment_P2',
                'SS_P1', 'SS_P2', 'Pension_P1', 'Pension_P2', 'RMD_P1', 'RMD_P2',
                'Total_Income', 'Spend_Goal', 'Previous_Taxes', 'Cash_Need',
                'WD_PreTax_P1', 'WD_PreTax_P2', 'WD_Taxable', 'WD_Roth_P1', 'WD_Roth_P2',
                'Roth_Conversion', 'Conv_P1', 'Conv_P2', 'Ord_Income', 'Cap_Gains',
                'Tax_Bill', 'Taxes_Paid', 'Bal_PreTax_P1', 'Bal_PreTax_P2',
                'Bal_Roth_P1', 'Bal_Roth_P2', 'Bal_Taxable', 'Net_Worth'
            ]
            
            # Reorder columns
            existing_cols = [col for col in display_columns if col in results_df.columns]
            remaining_cols = [col for col in results_df.columns if col not in display_columns]
            ordered_cols = existing_cols + remaining_cols
            results_df = results_df[ordered_cols]
            
            # Convert results to JSON-serializable format
            results_json = []
            header = list(results_df.columns)
            
            for _, row in results_df.iterrows():
                row_list = {}
                for col in header:
                    val = row[col]
                    # Convert numpy types
                    if pd.isna(val):
                         row_list[col] = None
                    elif hasattr(val, 'item'):
                        row_list[col] = val.item()
                    else:
                        row_list[col] = val
                results_json.append(row_list)
            
            return {
                'success': True,
                'results': results_json,
                'columns': header
            }
            
        except Exception as e:
            import traceback
            error_msg = f'Simulation failed: {str(e)}\n{traceback.format_exc()}'
            print(error_msg)
            return JSONResponse(status_code=500, content={'error': error_msg})
        
        finally:
            # Clean up temp file
            if temp_file_created and config_file and os.path.exists(config_file):
                try:
                    os.remove(config_file)
                except:
                    pass

    except Exception as e:
         return JSONResponse(status_code=500, content={'error': str(e)})


@app.get("/api/sample-config")
async def get_sample_config():
    """Return the sample configuration"""
    try:
        sample_df = pd.read_csv('nisha.csv')
        # Convert to dict
        config_data = sample_df.to_dict(orient='records')
        return {
            'success': True,
            'config': config_data
        }
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={'success': False, 'error': 'Sample config not found'})

@app.get("/download-template")
async def download_template():
    """Download sample CSV template"""
    # Simply return the file response if it exists
    file_path = "nisha.csv"
    if os.path.exists(file_path):
        return FileResponse(file_path, filename="retirement_planner_template.csv", media_type='text/csv')
    else:
        return JSONResponse(status_code=500, content={'error': 'Template file not found'})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)
