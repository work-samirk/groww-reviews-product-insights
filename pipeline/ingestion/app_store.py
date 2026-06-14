import requests
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Groww App Store App ID
GROWW_APP_STORE_ID = "1402264636"

def fetch_app_store_reviews(app_id=GROWW_APP_STORE_ID, limit_weeks=12):
    """
    Fetches reviews for the given app ID from Apple App Store RSS feed.
    Filters reviews to match the limit_weeks window.
    Also supports loading cached scraped JSON files if they exist in data/cache/.
    """
    import os
    import glob
    import json
    
    # 1. Search for local scraped cache files in data/cache/
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cache_files = []
    for pattern in ["groww-appstore", "appstore", "apple"]:
        cache_pattern = os.path.join(project_root, "data", "cache", pattern, "*", "pages", "*.json")
        cache_files.extend(glob.glob(cache_pattern))
        
    if cache_files:
        logger.info(f"Found {len(cache_files)} local App Store review cache files. Parsing...")
        cache_reviews = []
        for file_path in cache_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    page_data = json.load(f)
                    page_reviews = page_data.get("reviews", [])
                    for r in page_reviews:
                        cache_reviews.append({
                            "id": f"appstore_{r.get('reviewId', '')}",
                            "platform": "appstore",
                            "author": r.get("userName", "Anonymous"),
                            "date": r.get("at", datetime.now(timezone.utc).isoformat()),
                            "rating": int(r.get("score", 3)),
                            "review_text": r.get("content", ""),
                            "app_version": r.get("appVersion", "Unknown")
                        })
            except Exception as e:
                logger.warning(f"Error parsing cache file {file_path}: {e}")
                
        if cache_reviews:
            logger.info(f"Successfully loaded {len(cache_reviews)} reviews from local App Store scraper cache.")
            return cache_reviews

    # 2. Fall back to Apple App Store RSS feed
    url = f"https://itunes.apple.com/in/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error(f"Error fetching App Store reviews from RSS: {e}")
        return []

    feed = data.get("feed", {})
    entries = feed.get("entry", [])
    
    # If there's only 1 review, entry might be a dict instead of a list
    if isinstance(entries, dict):
        entries = [entries]
        
    reviews = []
    now = datetime.now(timezone.utc)
    
    for entry in entries:
        # The first entry in iTunes RSS is often the app metadata itself, skip it if it doesn't have an ID
        if "id" not in entry or "author" not in entry:
            continue
            
        try:
            review_id = entry.get("id", {}).get("label")
            author = entry.get("author", {}).get("name", {}).get("label", "Anonymous")
            rating = int(entry.get("im:rating", {}).get("label", 0))
            version = entry.get("im:version", {}).get("label", "Unknown")
            title = entry.get("title", {}).get("label", "")
            content = entry.get("content", {}).get("label", "")
            
            # Date is in format "2026-06-14T01:30:00-07:00"
            date_str = entry.get("updated", {}).get("label", "")
            if date_str:
                # Parse timezone-aware string. Python 3.7+ fromisoformat handles simple offsets
                # Replacing timezone suffix if needed, but modern Python fromisoformat handles most RSS formats.
                # E.g., '2026-06-14T01:30:00-07:00' -> fromisoformat
                try:
                    date_obj = datetime.fromisoformat(date_str)
                except ValueError:
                    # Fallback parser if fromisoformat fails
                    date_obj = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            else:
                date_obj = now

            # Calculate week age
            delta = now - date_obj
            age_weeks = delta.days / 7.0
            
            if age_weeks > limit_weeks:
                continue
                
            reviews.append({
                "id": f"appstore_{review_id}",
                "platform": "appstore",
                "author": author,
                "date": date_obj.isoformat(),
                "rating": rating,
                "review_text": f"{title} - {content}" if title else content,
                "app_version": version
            })
        except Exception as ex:
            logger.warning(f"Error parsing App Store review entry: {ex}")
            continue
            
    return reviews
