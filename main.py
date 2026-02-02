"""
Retirement Planner Web App - FastAPI Backend (Refactored Architecture)
Layered Architecture:
- API Layer (api/)
- Schemas Layer (schemas/)
- Service Layer (services/)
- Engine Layer (engine/) - Pure Python
"""
import uvicorn
import os
import io
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from api.simulations import router as simulation_router

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

# Include refactored routers
app.include_router(simulation_router, prefix="/api")

# Static & Templates
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if os.path.exists("templates"):
    templates = Jinja2Templates(directory="templates")

# ============================================================================
# Legacy/Utility Endpoints (Keep for frontend compatibility)
# ============================================================================

# Upload folder for temp CSV storage (legacy support for export)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

@app.post("/api/export-config")
async def export_config(data: Dict[str, Any]):
    """Export current form data as CSV file"""
    try:
        # Flattening logic could be moved to service, but keeping simple here
        records = []
        for k, v in data.items():
            if v is not None:
                records.append({'parameter': k, 'value': v})
        
        df = pd.DataFrame(records)
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=retirement_config.csv"}
        )
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/get-current-config")
async def get_current_config():
    """Get the currently saved configuration - Legacy Stub"""
    # In the new architecture, we might not persist to disk automatically on every run
    # to keep the engine pure. 
    # If this is critical, we'd add persistence to the service layer.
    # For now, returning empty or check file if it exists from previous runs.
    current_config_path = os.path.join(UPLOAD_FOLDER, 'current_config.csv')
    if os.path.exists(current_config_path):
        try:
            df = pd.read_csv(current_config_path)
            return dict(zip(df['parameter'], df['value']))
        except:
            pass
    return {}

@app.get("/api/sample-config")
async def get_sample_config():
    """Return the sample configuration"""
    try:
        if os.path.exists('nisha.csv'):
            sample_df = pd.read_csv('nisha.csv')
            return {'success': True, 'config': sample_df.to_dict(orient='records')}
    except:
        pass
    return {'success': False, 'message': 'Sample not found'}

@app.get("/download-template")
async def download_template():
    """Download sample CSV template"""
    file_path = "nisha.csv"
    if os.path.exists(file_path):
        return FileResponse(file_path, filename="retirement_planner_template.csv", media_type='text/csv')
    return {"error": "Template not found"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5050, reload=True)
