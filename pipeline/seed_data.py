import os
import json

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG_REVIEWS_FILE = os.path.join(WORKSPACE_DIR, "debug", "4_clustered_reviews.json")
DATA_DIR = os.path.join(WORKSPACE_DIR, "data")

os.makedirs(os.path.join(DATA_DIR, "reports"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "reviews"), exist_ok=True)

# 1. Define the report JSON matching docs/Groww_Weekly_Review_Pulse_2026-W25.md
report_data = {
  "product": "Groww",
  "iso_week": "2026-W25",
  "period_start": "2026-06-09",
  "period_end": "2026-06-16",
  "themes": [
    {
      "theme_name": "App Performance & Latency Issues",
      "severity": "MEDIUM",
      "review_count": 23,
      "summary": "Users report app freezing, slow loading charts, and lagging performance, particularly during the market opening hours.",
      "quotes": [
        "not happy with this application, brokrage charges are very High, too much lag, very much disappointed with the services,,going to unplug.... i don't recommend....",
        "What P&L does the chart show",
        "lag and update are very late 😔"
      ],
      "action_ideas": [
        "Optimize infrastructure capacity during peak trading hours (9:15 AM - 10:30 AM).",
        "Implement lightweight chart rendering and local caching for option chains.",
        "Add connection timeout safety states with user-friendly retry banners."
      ],
      "cluster_id": 1
    },
    {
      "theme_name": "Customer Support Response Latency",
      "severity": "HIGH",
      "review_count": 11,
      "summary": "Customers experience significant delays in ticket resolution for failed transactions, direct wallet transfers, and onboarding queries.",
      "quotes": [
        "No Customer Support - There is no customer support. No response to emails. Phone call get disconnected.",
        "I had a pathetic experience with Groww app. Recently I had changed the nominee details and got updated in DP. After a week, I invested in 4 mutual fund schemes through Groww app as lumpsum. After allocation of units, it was found that the nomination was marked to old nominee and not the latest one that got updated in DP. I contacted their chat support. It didn't give proper answer. Then I called their customer care. They assured that the details will.be corrected. However they didn't.",
        "awesome grow apps and very much for your support"
      ],
      "action_ideas": [
        "Introduce real-time SLA visibility on all opened support tickets in-app.",
        "Route failed wallet transfer tickets to a priority human queue automatically.",
        "Provide a direct phone callback request option for transactions stuck > 24 hours."
      ],
      "cluster_id": 2
    },
    {
      "theme_name": "UX Insights & Reporting Enhancements",
      "severity": "MEDIUM",
      "review_count": 6,
      "summary": "Users request direct access to tax statements and annualized return calculators (CAGR), and cite confusing portfolio navigation.",
      "quotes": [
        "I have been using Groww for quite some time, and my overall experience has been excellent. The app offers a clean, user-friendly interface with smooth navigation and fast order execution. It provides all the essential features for investing and trading, including stocks, mutual funds, and F&O trading, in one place. Portfolio tracking is simple, and the platform is easy to use for both beginners and experienced traders. 🥰🥰🥰",
        "outstanding broker ... easy to use and there is also simple interference. there is no extra taxes instead of order tax ... all is good experience... ☺️",
        "I can't download this app much money I in vest here"
      ],
      "action_ideas": [
        "Expose tax report downloads directly on the app profile / home section.",
        "Simplify portfolio returns hierarchy to display CAGR alongside total absolute returns.",
        "Redesign the investment dashboard navigation flow to reduce taps to option charts."
      ],
      "cluster_id": 3
    }
  ]
}

# 2. Load reviews from debug folder and map them to these three cluster_ids
theme1_keywords = ["freeze", "lag", "crash", "slow", "candlestick", "chart"]
theme2_keywords = ["support", "ticket", "deducted", "wallet", "reply", "unprofessional", "nominee", "customer care"]
theme3_keywords = ["cagr", "navigation", "insights", "analytics", "download", "tax", "interface", "navigation", "ui", "ux"]

with open(DEBUG_REVIEWS_FILE, "r", encoding="utf-8") as f:
    raw_reviews = json.load(f)

mapped_reviews = []
theme1_count = 0
theme2_count = 0
theme3_count = 0

for review in raw_reviews:
    text = review.get("review_text", "").lower()
    
    # Map based on keyword matching to simulate UMAP/HDBSCAN clustering output for the dashboard
    cid = -1
    if any(k in text for k in theme1_keywords):
        cid = 1
        theme1_count += 1
    elif any(k in text for k in theme2_keywords):
        cid = 2
        theme2_count += 1
    elif any(k in text for k in theme3_keywords):
        cid = 3
        theme3_count += 1
        
    mapped_reviews.append({
        "id": review.get("id"),
        "platform": review.get("platform"),
        "author": review.get("author"),
        "date": review.get("date"),
        "rating": review.get("rating"),
        "review_text": review.get("review_text"),
        "cluster_id": cid
    })

# Update report count metadata with actual mapped counts
report_data["themes"][0]["review_count"] = theme1_count
report_data["themes"][1]["review_count"] = theme2_count
report_data["themes"][2]["review_count"] = theme3_count

# Write the reports and reviews JSON
report_out = os.path.join(DATA_DIR, "reports", "2026-W25.json")
reviews_out = os.path.join(DATA_DIR, "reviews", "2026-W25.json")

with open(report_out, "w", encoding="utf-8") as f:
    json.dump(report_data, f, indent=2, ensure_ascii=False)

with open(reviews_out, "w", encoding="utf-8") as f:
    json.dump(mapped_reviews, f, indent=2, ensure_ascii=False)

print(f"Data seeded successfully for 2026-W25!")
print(f"Theme 1 count: {theme1_count}")
print(f"Theme 2 count: {theme2_count}")
print(f"Theme 3 count: {theme3_count}")
print(f"Total reviews processed: {len(mapped_reviews)}")
