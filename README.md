# Retirement Planner FastAPI - Complete Migration

## Overview
Complete retirement planning API with Monte Carlo simulation, real estate support, and multiple withdrawal strategies.

## Features
- ✅ **Monte Carlo Simulation** - Run 1-1000 simulations with volatility
- ✅ **Multiple Strategies** - Standard vs. Taxable-First withdrawal comparison
- ✅ **Real Estate Support** - Primary home + rental properties with mortgages
- ✅ **51 Validated Parameters** - Comprehensive input validation
- ✅ **8 API Endpoints** - Full REST API
- ✅ **Deployment Ready** - Docker + Cloud Run + Heroku

---

## Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --host 0.0.0.0 --port 5001 --reload

# Access interactive docs
open http://localhost:5001/docs
```

### Docker
```bash
# Build
docker build -t retirement-api .

# Run
docker run -p 5001:5001 -e PORT=5001 retirement-api

# Test
curl http://localhost:5001/health
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/run-simulation` | POST | Run both strategies |
| `/api/run-monte-carlo` | POST | Monte Carlo simulation |
| `/api/export-config` | POST | Export as CSV |
| `/api/get-current-config` | GET | Get last config |
| `/api/sample-config` | GET | Sample data |
| `/download-template` | GET | CSV template |

---

## Example Request

```bash
curl -X POST http://localhost:5001/api/run-simulation \
  -H "Content-Type: application/json" \
  -d '{
    "p1_start_age": 65,
    "p2_start_age": 63,
    "end_simulation_age": 95,
    "inflation_rate": 0.03,
    "annual_spend_goal": 200000,
    "bal_taxable": 700000,
    "bal_pretax_p1": 1250000,
    "bal_pretax_p2": 1250000,
    "bal_roth_p1": 60000,
    "bal_roth_p2": 60000,
    "growth_rate_taxable": 0.07,
    "growth_rate_pretax_p1": 0.07,
    "growth_rate_pretax_p2": 0.07,
    "growth_rate_roth_p1": 0.07,
    "growth_rate_roth_p2": 0.07,
    "taxable_basis_ratio": 0.75,
    "target_tax_bracket_rate": 0.24,
    "primary_home_value": 800000,
    "rental_1_value": 500000,
    "rental_1_income": 30000
  }'
```

---

## Deployment

### Google Cloud Run
```bash
gcloud run deploy retirement-planner \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Heroku
```bash
git push heroku main
```

---

## Migration from Flask

**All Flask features migrated**:
- ✅ Core calculations (RetirementSimulator + Mortgage)
- ✅ Multiple withdrawal strategies
- ✅ Monte Carlo with volatility
- ✅ Real estate & rental properties
- ✅ Export/Import configuration
- ✅ All 51 parameters

**Enhancements**:
- ✅ Pydantic validation
- ✅ Auto-generated API docs
- ✅ Health check endpoint
- ✅ Better error handling
- ✅ Async support

---

## Tech Stack
- **FastAPI** - Modern async web framework
- **Pydantic** - Data validation
- **Pandas & NumPy** - Calculations
- **Uvicorn** - ASGI server
- **Docker** - Containerization

---

## Documentation
- Interactive API docs: `http://localhost:5001/docs`
- Redoc: `http://localhost:5001/redoc`

---

## Status
✅ **COMPLETE** - 100% feature parity with Flask + enhancements
