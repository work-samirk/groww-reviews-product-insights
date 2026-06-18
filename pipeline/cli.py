import os
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "true"
import sys
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add project root to python path to allow relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.ingestion.app_store import fetch_app_store_reviews
from pipeline.ingestion.play_store import fetch_play_store_reviews
from pipeline.security.scrubber import scrub_review
from pipeline.reasoning.clusterer import perform_clustering
from pipeline.reasoning.synthesizer import generate_report_json
from pipeline.state import state_manager
from pipeline.rendering.renderer import format_docs_content, format_email_body
from pipeline.delivery.mcp_client import WorkspaceMCPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("groww_pulse_cli")

def get_current_iso_week():
    """Calculates the current year and ISO week, e.g. '2026-W24'."""
    today = datetime.now()
    year, week, _ = today.isocalendar()
    return f"{year}-W{week:02d}"

def main():
    # Load .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Groww Weekly Product Review Pulse Pipeline")
    parser.add_argument(
        "--week", 
        type=str, 
        default=get_current_iso_week(),
        help="Target ISO week for backfill/run (e.g. 2026-W24). Defaults to current week."
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force execution even if a completed run for the week already exists."
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Execute data extraction, clustering and summarization, but skip MCP delivery."
    )
    parser.add_argument(
        "--doc-id", 
        type=str, 
        default=os.getenv("GOOGLE_DOC_ID"),
        help="Google Doc ID. Overrides GOOGLE_DOC_ID environment variable."
    )
    parser.add_argument(
        "--email-to", 
        type=str, 
        default=os.getenv("STAKEHOLDER_EMAIL"),
        help="Recipient email address. Overrides STAKEHOLDER_EMAIL environment variable."
    )
    
    args = parser.parse_args()
    iso_week = args.week
    
    logger.info(f"=== Starting Groww Review Pulse Pipeline for week: {iso_week} ===")
    
    # 1. Enforce Idempotency Check
    if not args.force and not args.dry_run:
        if state_manager.is_already_run("groww", iso_week):
            logger.info(f"Idempotency Guard: A completed run already exists for Groww and week {iso_week}. Exiting.")
            sys.exit(0)
            
    # 2. Resolve parameters
    doc_id = args.doc_id
    email_to = args.email_to
    
    if not args.dry_run:
        if not doc_id:
            logger.error("Missing GOOGLE_DOC_ID. Set it in .env or provide via --doc-id.")
            sys.exit(1)
        if not email_to:
            logger.error("Missing STAKEHOLDER_EMAIL. Set it in .env or provide via --email-to.")
            sys.exit(1)
            
    # 3. Data Ingestion
    logger.info("Step 1/5: Ingesting app reviews...")
    app_store_reviews = fetch_app_store_reviews(limit_weeks=12)
    play_store_reviews = fetch_play_store_reviews(limit_weeks=12)
    
    all_reviews = app_store_reviews + play_store_reviews
    logger.info(f"Ingested {len(all_reviews)} total reviews (App Store: {len(app_store_reviews)}, Play Store: {len(play_store_reviews)}).")
    
    if not all_reviews:
        logger.error("No reviews fetched for the specified window. Exiting.")
        sys.exit(1)
        
    # 4. Security: PII Scrubbing
    logger.info("Step 2/5: Cleaning data and scrubbing PII...")
    scrubbed_reviews = [scrub_review(r) for r in all_reviews]
    logger.info("PII scrubbing complete.")
    
    # 5. Reasoning: Clustering
    logger.info("Step 3/5: Running clustering and dimensionality reduction...")
    # Retrieve embeddings explicitly for logging and debug export
    from pipeline.reasoning.clusterer import get_embeddings
    texts = [r["review_text"] for r in scrubbed_reviews]
    embeddings = get_embeddings(texts)
    logger.info(f"Embeddings matrix generated with shape: {embeddings.shape}")
    
    clustered_reviews = perform_clustering(scrubbed_reviews, embeddings=embeddings)
    logger.info("Review clustering complete.")
    
    # 6. Reasoning: LLM Synthesis & Quote Validation
    logger.info("Step 4/5: Synthesizing themes and validating quotes...")
    report = generate_report_json(clustered_reviews, iso_week)
    logger.info("Insights generation complete.")
    
    # 7. Check if dry-run
    if args.dry_run:
        import json
        # Create debug directory
        debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Save raw reviews
        raw_path = os.path.join(debug_dir, "1_raw_reviews.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(all_reviews, f, indent=2, ensure_ascii=False)
            
        # Save scrubbed reviews
        scrubbed_path = os.path.join(debug_dir, "2_scrubbed_reviews.json")
        with open(scrubbed_path, "w", encoding="utf-8") as f:
            json.dump(scrubbed_reviews, f, indent=2, ensure_ascii=False)
            
        # Save embeddings
        embeddings_path = os.path.join(debug_dir, "3_embeddings.json")
        embeddings_meta = {
            "matrix_shape": list(embeddings.shape),
            "sample_vector_first_10_elements": embeddings[0][:10].tolist() if len(embeddings) > 0 else []
        }
        with open(embeddings_path, "w", encoding="utf-8") as f:
            json.dump(embeddings_meta, f, indent=2)
            
        # Save clustered reviews
        clustered_path = os.path.join(debug_dir, "4_clustered_reviews.json")
        with open(clustered_path, "w", encoding="utf-8") as f:
            json.dump(clustered_reviews, f, indent=2, ensure_ascii=False)
            
        logger.info(f"--- DRY RUN MODE ACTIVE: Debug Files Exported to {debug_dir} ---")
        logger.info(f"1. Raw Ingested Reviews saved to: {raw_path}")
        logger.info(f"2. Scrubbed Reviews saved to: {scrubbed_path}")
        logger.info(f"3. Embeddings Metadata saved to: {embeddings_path}")
        logger.info(f"4. Clustered Reviews (with Cluster IDs) saved to: {clustered_path}")
        
        logger.info("--- Report Output Preview ---")
        print(json.dumps(report, indent=2))
        
        # Test Doc formatting
        logger.info("--- Google Docs Content Preview ---")
        print(format_docs_content(report))
        
        # Test Email formatting
        logger.info("--- Gmail Teaser Content Preview ---")
        _, text_preview = format_email_body(report, "https://docs.google.com/document/d/MOCK_ID/edit#heading=h.mock")
        print(text_preview)
        
        logger.info("Dry run execution completed successfully.")
        sys.exit(0)
        
    # 8. Delivery via MCP Server
    logger.info("Step 5/5: Connecting to custom Google Workspace MCP server...")
    
    # Log run in DB as IN_PROGRESS
    review_count = len(all_reviews)
    window_weeks = 12
    run_id = state_manager.start_run("groww", iso_week, review_count, window_weeks)
    
    mcp_client = WorkspaceMCPClient()
    try:
        mcp_client.connect()
        
        # Deliver to Google Doc
        doc_title = f"Groww Review Pulse — Week {iso_week}"
        docs_body = format_docs_content(report)
        
        logger.info(f"Appending report to Google Doc: {doc_id} under heading: '{doc_title}'")
        doc_result = mcp_client.call_tool(
            "append_weekly_report",
            {
                "docId": doc_id,
                "title": doc_title,
                "content": docs_body
            }
        )
        
        doc_link = doc_result.get("docLink")
        heading_id = doc_result.get("headingId")
        status = doc_result.get("status")
        returned_doc_id = doc_result.get("docId", doc_id)
        
        if returned_doc_id != doc_id:
            logger.info("=======================================================================")
            logger.info(f"*** NEW GOOGLE DOC CREATED: {returned_doc_id} ***")
            logger.info("Please copy this ID and replace YOUR_GOOGLE_DOC_ID_HERE in your .env file.")
            logger.info("=======================================================================")
            
        logger.info(f"Docs append complete. Status: {status}, Link: {doc_link}")
        
        # Deliver to Gmail
        logger.info(f"Sending notification email to stakeholders: {email_to}")
        html_body, text_body = format_email_body(report, doc_link)
        email_subject = f"Groww Weekly Review Pulse — {iso_week}"
        email_idempotency_key = f"groww-{iso_week}-email"
        
        email_result = mcp_client.call_tool(
            "send_stakeholder_teaser",
            {
                "to": email_to,
                "subject": email_subject,
                "bodyHtml": html_body,
                "bodyText": text_body
            }
        )
        
        message_id = email_result.get("messageId")
        logger.info(f"Gmail delivery complete. Message ID: {message_id}")
        
        # Log successful completion
        state_manager.complete_run(run_id, returned_doc_id, heading_id, doc_link, message_id, email_idempotency_key)
        logger.info(f"=== Weekly Review Pulse run for week {iso_week} completed successfully! ===")
        
    except Exception as ex:
        logger.error(f"Error during delivery: {ex}. Marking run as FAILED.")
        state_manager.fail_run(run_id, str(ex))
        raise
    finally:
        mcp_client.close()

if __name__ == "__main__":
    main()
