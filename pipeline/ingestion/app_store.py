import requests
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Groww App Store App ID
GROWW_APP_STORE_ID = "1404871703"

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

    # 2. Try scraping from Apple App Store using app-store-scraper
    try:
        from app_store_scraper import AppStore
        logger.info(f"Attempting to scrape App Store reviews dynamically using app-store-scraper for App ID: {app_id}...")
        
        # Specify app_name='groww' and match correct ID
        app = AppStore(country='in', app_name='groww', app_id=int(app_id))
        app.review(how_many=200)
        
        if app.reviews:
            logger.info(f"Scraped {len(app.reviews)} reviews from Apple App Store.")
            scraped_reviews = []
            for r in app.reviews:
                date_str = r.get("date")
                if hasattr(date_str, "isoformat"):
                    date_str = date_str.isoformat()
                    
                # Filter specifically for the year 2026
                if not date_str.startswith("2026"):
                    continue
                    
                scraped_reviews.append({
                    "id": f"appstore_{r.get('userName', '')}_{date_str}",
                    "platform": "appstore",
                    "author": r.get("userName", "Anonymous"),
                    "date": date_str,
                    "rating": int(r.get("rating", 3)),
                    "review_text": f"{r.get('title', '')} - {r.get('review', '')}" if r.get('title') else r.get('review', ''),
                    "app_version": "Unknown"
                })
            logger.info(f"Retained {len(scraped_reviews)} App Store reviews from the year 2026.")
            return scraped_reviews
    except Exception as e:
        logger.warning(f"app-store-scraper failed: {e}. Falling back to RSS feed.")

    reviews = []
    now = datetime.now(timezone.utc)
    
    # 3. Fall back to Apple App Store RSS feed with pagination (up to 10 pages)
    logger.info(f"Attempting to fetch App Store reviews dynamically from RSS feed for App ID: {app_id}...")
    for page in range(1, 11):
        url = f"https://itunes.apple.com/in/rss/customerreviews/page={page}/id={app_id}/sortBy=mostRecent/xml"
        try:
            import xml.etree.ElementTree as ET
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                break
            
            root = ET.fromstring(response.content)
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'im': 'http://itunes.apple.com/rss'
            }
            entries = root.findall('atom:entry', ns)
            if not entries:
                break
                
            for entry in entries:
                try:
                    review_id_el = entry.find('atom:id', ns)
                    review_id = review_id_el.text if review_id_el is not None else ""
                    if not review_id:
                        continue
                        
                    author_name_el = entry.find('atom:author/atom:name', ns)
                    author = author_name_el.text if author_name_el is not None else "Anonymous"
                    
                    rating_el = entry.find('im:rating', ns)
                    rating = int(rating_el.text) if rating_el is not None else 3
                    
                    version_el = entry.find('im:version', ns)
                    version = version_el.text if version_el is not None else "Unknown"
                    
                    title_el = entry.find('atom:title', ns)
                    title = title_el.text if title_el is not None else ""
                    
                    # Prefer text content over html content
                    content_el = entry.find('atom:content[@type="text"]', ns)
                    content = content_el.text if content_el is not None else ""
                    if not content:
                        content_el = entry.find('atom:content', ns)
                        content = content_el.text if content_el is not None else ""
                        
                    date_str_el = entry.find('atom:updated', ns)
                    date_str = date_str_el.text if date_str_el is not None else ""
                    
                    if date_str:
                        try:
                            date_obj = datetime.fromisoformat(date_str)
                        except ValueError:
                            date_obj = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    else:
                        date_obj = now

                    # Filter specifically for the year 2026
                    if not date_obj.isoformat().startswith("2026"):
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
                    continue
        except Exception as e:
            logger.warning(f"Failed to fetch page {page} of App Store reviews: {e}")
            break
            
    logger.info(f"Retained {len(reviews)} App Store reviews from the year 2026.")
    return reviews
