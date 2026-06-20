import os
import sys
import json
import logging
from dotenv import load_dotenv

# Add project root to python path to allow relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.delivery.mcp_client import WorkspaceMCPClient
from pipeline.rendering.renderer import format_docs_content

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("groww_backfill_docs")

def main():
    load_dotenv()
    doc_id = os.getenv("GOOGLE_DOC_ID")
    
    if not doc_id or doc_id == "CREATE":
        logger.error("A valid GOOGLE_DOC_ID must be configured in your .env file.")
        sys.exit(1)
        
    logger.info(f"Starting Google Doc backfill for Document ID: {doc_id}")
    
    # Load periods
    periods_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "weeks", "periods.json")
    if not os.path.exists(periods_file):
        logger.error("periods.json not found! Run pipeline/seed_weeks.py first.")
        sys.exit(1)
        
    with open(periods_file, "r", encoding="utf-8") as f:
        periods = json.load(f)
        
    # Collect all weeks chronologically
    weeks_to_backfill = []
    for month_data in periods:
        month_label = month_data["month_label"]
        month_code = month_data["month_code"]
        for idx, week in enumerate(month_data["weeks"]):
            weeks_to_backfill.append({
                "month_label": month_label,
                "month_code": month_code,
                "week_num": idx + 1,
                "week_label": week["week_label"],
                "start_date": week["start_date"],
                "end_date": week["end_date"]
            })
            
    # Connect to MCP Workspace Server
    mcp_client = WorkspaceMCPClient()
    try:
        logger.info("Connecting to Google Workspace MCP Server...")
        mcp_client.connect()
        logger.info("Connected successfully.")
        
        # Append weekly reports chronologically
        for week in weeks_to_backfill:
            start_date = week["start_date"]
            end_date = week["end_date"]
            file_key = f"{start_date}_{end_date}"
            
            report_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "weeks", "reports", f"{file_key}.json"
            )
            
            if not os.path.exists(report_path):
                logger.warning(f"Report file not found for {file_key}, skipping.")
                continue
                
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)
                
            doc_title = f"Groww Review Pulse — Week {week['month_code']}-W{week['week_num']} ({datetime_format(start_date)} - {datetime_format(end_date)})"
            docs_body = format_docs_content(report)
            
            logger.info(f"Appending weekly report: '{doc_title}' to Google Doc...")
            
            doc_result = mcp_client.call_tool(
                "append_weekly_report",
                {
                    "docId": doc_id,
                    "title": doc_title,
                    "content": docs_body
                }
            )
            logger.info(f"Status: {doc_result.get('status')} | Link: {doc_result.get('docLink')}")
            
        logger.info("Google Doc backfill process completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during Google Doc backfill: {e}")
        sys.exit(1)
    finally:
        mcp_client.close()

def datetime_format(date_str):
    from datetime import datetime
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%b %d, %Y")

if __name__ == "__main__":
    main()
