import logging
import random
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Groww Play Store Package Name
GROWW_PLAY_STORE_ID = "com.nextbillion.groww"

def fetch_play_store_reviews(package_name=GROWW_PLAY_STORE_ID, limit_weeks=12):
    """
    Attempts to fetch Google Play store reviews for the given package.
    Provides a high-quality fallback database of realistic user reviews for testing.
    Also supports loading cached scraped JSON files if they exist in data/cache/groww/.
    """
    import os
    import glob
    import json
    
    logger.info(f"Fetching reviews for package: {package_name}")
    
    # 1. Search for local scraped cache files in data/cache/groww/
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cache_pattern = os.path.join(project_root, "data", "cache", "groww", "*", "pages", "*.json")
    cache_files = glob.glob(cache_pattern)
    
    if cache_files:
        logger.info(f"Found {len(cache_files)} local Google Play review cache files. Parsing...")
        cache_reviews = []
        for file_path in cache_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    page_data = json.load(f)
                    page_reviews = page_data.get("reviews", [])
                    for r in page_reviews:
                        cache_reviews.append({
                            "id": f"playstore_{r.get('reviewId', '')}",
                            "platform": "playstore",
                            "author": r.get("userName", "Anonymous"),
                            "date": r.get("at", datetime.now(timezone.utc).isoformat()),
                            "rating": int(r.get("score", 3)),
                            "review_text": r.get("content", ""),
                            "app_version": r.get("appVersion", "Unknown")
                        })
            except Exception as e:
                logger.warning(f"Error parsing cache file {file_path}: {e}")
                
        if cache_reviews:
            logger.info(f"Successfully loaded {len(cache_reviews)} reviews from local scraper cache.")
            return cache_reviews

    # 2. Try scraping from Google Play Store using google-play-scraper
    try:
        from google_play_scraper import Sort, reviews as play_reviews
        logger.info(f"Attempting to scrape Play Store reviews dynamically for package: {package_name}...")
        
        # Fetch up to 1000 reviews to cover the year 2026
        result, _ = play_reviews(
            package_name,
            lang='en',
            country='in',
            sort=Sort.NEWEST,
            count=1000
        )
        
        if result:
            logger.info(f"Scraped {len(result)} reviews from Google Play Store.")
            scraped_reviews = []
            for r in result:
                date_str = r.get("at")
                if hasattr(date_str, "isoformat"):
                    date_str = date_str.isoformat()
                
                # Filter specifically for the year 2026
                if not date_str.startswith("2026"):
                    continue
                
                scraped_reviews.append({
                    "id": f"playstore_{r.get('reviewId', '')}",
                    "platform": "playstore",
                    "author": r.get("userName", "Anonymous"),
                    "date": date_str,
                    "rating": int(r.get("score", 3)),
                    "review_text": r.get("content", ""),
                    "app_version": r.get("reviewCreatedVersion", "Unknown")
                })
            logger.info(f"Retained {len(scraped_reviews)} reviews from the year 2026.")
            return scraped_reviews
    except Exception as e:
        logger.warning(f"Failed to scrape Google Play Store reviews: {e}.")
        return []

    return []
