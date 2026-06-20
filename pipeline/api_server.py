import os
import json
import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("groww_api_server")

app = FastAPI(
    title="Groww Weekly Product Insights API",
    description="Backend API serving synthesized weekly insights and raw customer reviews.",
    version="2.0.0"
)

# Enable CORS for frontend API consumption
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development; tighten in production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORKSPACE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
WEEKS_DATA_DIR = os.path.join(WORKSPACE_DATA_DIR, "weeks")
PATH_PREFIX = "/api/v1/groww-product-insights"

@app.get(f"{PATH_PREFIX}/health")
async def health():
    """Returns the health status of the API server."""
    return {"status": "healthy"}

@app.get(f"{PATH_PREFIX}/available-periods")
async def get_available_periods():
    """Returns the month-to-weeks hierarchical metadata index."""
    periods_file = os.path.join(WEEKS_DATA_DIR, "periods.json")
    if not os.path.exists(periods_file):
        raise HTTPException(status_code=404, detail="Periods metadata file not found.")
    try:
        with open(periods_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error reading periods metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to read available periods metadata.")

@app.get(f"{PATH_PREFIX}/insights-report")
async def get_insights_report(
    start_date: str = Query(..., description="The start date YYYY-MM-DD"),
    end_date: str = Query(..., description="The end date YYYY-MM-DD")
):
    """Retrieves the synthesized weekly report for the given date range."""
    file_key = f"{start_date}_{end_date}"
    report_file = os.path.join(WEEKS_DATA_DIR, "reports", f"{file_key}.json")
    if not os.path.exists(report_file):
        raise HTTPException(status_code=404, detail=f"Weekly report not found for period: {start_date} to {end_date}")
    try:
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error reading weekly report for {file_key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read weekly report data.")

@app.get(f"{PATH_PREFIX}/customer-reviews")
async def get_customer_reviews(
    start_date: str = Query(..., description="The start date YYYY-MM-DD"),
    end_date: str = Query(..., description="The end date YYYY-MM-DD")
):
    """Retrieves the reviews for the given date range."""
    file_key = f"{start_date}_{end_date}"
    reviews_file = os.path.join(WEEKS_DATA_DIR, "reviews", f"{file_key}.json")
    if not os.path.exists(reviews_file):
        raise HTTPException(status_code=404, detail=f"Weekly reviews not found for period: {start_date} to {end_date}")
    try:
        with open(reviews_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error reading weekly reviews for {file_key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read weekly reviews data.")

# Legacy Endpoints for Backwards Compatibility

@app.get(f"{PATH_PREFIX}/months")
async def get_months():
    """Returns a list of all available months (legacy support)."""
    try:
        periods_file = os.path.join(WEEKS_DATA_DIR, "periods.json")
        if os.path.exists(periods_file):
            with open(periods_file, "r", encoding="utf-8") as f:
                periods = json.load(f)
            return [p["month_code"] for p in periods]
        return []
    except Exception as e:
        logger.error(f"Error reading periods for months: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get(f"{PATH_PREFIX}/weeks")
async def get_weeks():
    """Fallback endpoint mapping to months for backward compatibility."""
    try:
        periods_file = os.path.join(WEEKS_DATA_DIR, "periods.json")
        if os.path.exists(periods_file):
            with open(periods_file, "r", encoding="utf-8") as f:
                periods = json.load(f)
            return [p["month_code"] for p in periods]
        return []
    except Exception as e:
        logger.error(f"Error reading periods: {e}")
        return []

@app.get(f"{PATH_PREFIX}/report")
async def get_report(
    month: str = Query(None, description="The month code, e.g. 2026-06"),
    week: str = Query(None, description="Deprecated. Maps to first week of month.")
):
    """Legacy report endpoint mapping to the first week of the month."""
    target_month = month or week
    if not target_month:
        raise HTTPException(status_code=400, detail="Missing required query parameter: 'month'")
    try:
        periods_file = os.path.join(WEEKS_DATA_DIR, "periods.json")
        if os.path.exists(periods_file):
            with open(periods_file, "r", encoding="utf-8") as f:
                periods = json.load(f)
            month_data = next((p for p in periods if p["month_code"] == target_month), None)
            if month_data and len(month_data["weeks"]) > 0:
                first_week = month_data["weeks"][0]
                start_date = first_week["start_date"]
                end_date = first_week["end_date"]
                file_key = f"{start_date}_{end_date}"
                report_file = os.path.join(WEEKS_DATA_DIR, "reports", f"{file_key}.json")
                if os.path.exists(report_file):
                    with open(report_file, "r", encoding="utf-8") as f:
                        return json.load(f)
        raise HTTPException(status_code=404, detail=f"No data found for month: {target_month}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error mapping legacy report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get(f"{PATH_PREFIX}/reviews")
async def get_reviews(
    month: str = Query(None, description="The month code, e.g. 2026-06"),
    week: str = Query(None, description="Deprecated. Maps to first week of month.")
):
    """Legacy reviews endpoint mapping to the first week of the month."""
    target_month = month or week
    if not target_month:
        raise HTTPException(status_code=400, detail="Missing required query parameter: 'month'")
    try:
        periods_file = os.path.join(WEEKS_DATA_DIR, "periods.json")
        if os.path.exists(periods_file):
            with open(periods_file, "r", encoding="utf-8") as f:
                periods = json.load(f)
            month_data = next((p for p in periods if p["month_code"] == target_month), None)
            if month_data and len(month_data["weeks"]) > 0:
                first_week = month_data["weeks"][0]
                start_date = first_week["start_date"]
                end_date = first_week["end_date"]
                file_key = f"{start_date}_{end_date}"
                reviews_file = os.path.join(WEEKS_DATA_DIR, "reviews", f"{file_key}.json")
                if os.path.exists(reviews_file):
                    with open(reviews_file, "r", encoding="utf-8") as f:
                        return json.load(f)
        raise HTTPException(status_code=404, detail=f"No data found for month: {target_month}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error mapping legacy reviews: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

