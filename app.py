"""
Retirement Planner Web App - Flask Backend
"""
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
import sys
import io
from werkzeug.utils import secure_filename
from pathlib import Path

# Import the retirement planner class
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retirement_planner_yr import RetirementSimulator
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:8080", "http://127.0.0.1:8080"]}})
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Home page with upload and form options"""
    return render_template('index.html')

@app.route('/api/run-simulation', methods=['POST'])
def run_simulation():
    """
    Handle both CSV upload and form input to run simulation.
    Request can be:
    1. JSON with form parameters
    2. Form with CSV file upload
    """
    try:
        config_df = None
        config_file = None
        
        # Check if file was uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                # Save uploaded file temporarily
                filename = secure_filename(file.filename)
                config_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(config_file)
            else:
                return jsonify({'error': 'Invalid file format. Please upload a CSV file.'}), 400
        
        # Check if form data was submitted
        elif request.form:
            # Convert form data to DataFrame format
            params = []
            values = []
            
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
            
            for form_key, (param_name, description) in form_mapping.items():
                if form_key in request.form and request.form[form_key]:
                    params.append(param_name)
                    values.append(request.form[form_key])
                    
            if params:
                # Create a temporary CSV in memory
                descriptions = []
                for fk in params:
                    # Find the form_key that maps to this param_name
                    for form_key, (param_name, desc) in form_mapping.items():
                        if param_name == fk:
                            descriptions.append(desc)
                            break
                
                config_df = pd.DataFrame({
                    'parameter': params,
                    'value': values,
                    'description': descriptions
                })
                # Save to temporary file
                config_file = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_form_config.csv')
                config_df.to_csv(config_file, index=False)
            else:
                return jsonify({'error': 'No parameters provided.'}), 400
        
        elif request.json:
            # Handle JSON POST request with form parameters
            form_data = request.json
            params = []
            values = []
            
            form_mapping = {
                'p1_start_age': 'p1_start_age',
                'p2_start_age': 'p2_start_age',
                'end_simulation_age': 'end_simulation_age',
                'inflation_rate': 'inflation_rate',
                'annual_spend_goal': 'annual_spend_goal',
                'p1_employment_income': 'p1_employment_income',
                'p1_employment_until_age': 'p1_employment_until_age',
                'p2_employment_income': 'p2_employment_income',
                'p2_employment_until_age': 'p2_employment_until_age',
                'p1_ss_amount': 'p1_ss_amount',
                'p1_ss_start_age': 'p1_ss_start_age',
                'p2_ss_amount': 'p2_ss_amount',
                'p2_ss_start_age': 'p2_ss_start_age',
                'p1_pension': 'p1_pension',
                'p1_pension_start_age': 'p1_pension_start_age',
                'p2_pension': 'p2_pension',
                'p2_pension_start_age': 'p2_pension_start_age',
                'bal_taxable': 'bal_taxable',
                'bal_pretax_p1': 'bal_pretax_p1',
                'bal_pretax_p2': 'bal_pretax_p2',
                'bal_roth_p1': 'bal_roth_p1',
                'bal_roth_p2': 'bal_roth_p2',
                'growth_rate_taxable': 'growth_rate_taxable',
                'growth_rate_pretax_p1': 'growth_rate_pretax_p1',
                'growth_rate_pretax_p2': 'growth_rate_pretax_p2',
                'growth_rate_roth_p1': 'growth_rate_roth_p1',
                'growth_rate_roth_p2': 'growth_rate_roth_p2',
                'taxable_basis_ratio': 'taxable_basis_ratio',
                'target_tax_bracket_rate': 'target_tax_bracket_rate',
            }
            
            for param_name in form_mapping.values():
                if param_name in form_data and form_data[param_name] is not None:
                    params.append(param_name)
                    values.append(str(form_data[param_name]))
            
            if params:
                config_file = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_json_config.csv')
                config_df = pd.DataFrame({
                    'parameter': params,
                    'value': values,
                    'description': [''] * len(params)
                })
                config_df.to_csv(config_file, index=False)
            else:
                return jsonify({'error': 'No parameters provided.'}), 400
        else:
            return jsonify({'error': 'No file or data provided.'}), 400
        
        if not config_file:
            return jsonify({'error': 'Failed to process input.'}), 400
        
        # Run the simulation
        try:
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
            
            # Reorder columns: keep display columns first, then add any remaining
            existing_cols = [col for col in display_columns if col in results_df.columns]
            remaining_cols = [col for col in results_df.columns if col not in display_columns]
            ordered_cols = existing_cols + remaining_cols
            results_df = results_df[ordered_cols]
            
            # Convert results to JSON-serializable format with explicit column ordering
            # Return as list of lists with header row (more reliable than dicts for column order)
            results_json = []
            header = list(results_df.columns)
            
            for _, row in results_df.iterrows():
                row_list = {}  # Return as dict but with explicit column order in separate header
                for col in header:
                    val = row[col]
                    # Convert numpy types to Python types for JSON serialization
                    if pd.isna(val):
                        row_list[col] = None
                    elif hasattr(val, 'item'):  # numpy types
                        row_list[col] = val.item()
                    else:
                        row_list[col] = val
                results_json.append(row_list)
            
            return jsonify({
                'success': True,
                'results': results_json,
                'columns': header  # Return column order explicitly
            })
        
        except Exception as e:
            import traceback
            error_msg = f'Simulation failed: {str(e)}\n{traceback.format_exc()}'
            print(error_msg)  # Log to console for debugging
            return jsonify({'error': error_msg}), 500
        
        finally:
            # Clean up temp file if it was created
            if config_file and os.path.exists(config_file):
                try:
                    os.remove(config_file)
                except:
                    pass
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sample-config')
def get_sample_config():
    """Return the sample configuration to help users fill the form"""
    try:
        sample_df = pd.read_csv('nisha.csv')
        return jsonify({
            'success': True,
            'config': sample_df.to_dict(orient='records')
        })
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'Sample config not found'}), 404

@app.route('/download-template')
def download_template():
    """Download sample CSV template"""
    try:
        df = pd.read_csv('nisha.csv')
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='retirement_planner_template.csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5001)
