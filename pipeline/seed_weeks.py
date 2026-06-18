import os
import json
import random
from datetime import datetime, timedelta

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG_REVIEWS_FILE = os.path.join(WORKSPACE_DIR, "debug", "4_clustered_reviews.json")
DATA_DIR = os.path.join(WORKSPACE_DIR, "data", "weeks")

os.makedirs(os.path.join(DATA_DIR, "reports"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "reviews"), exist_ok=True)

with open(DEBUG_REVIEWS_FILE, "r", encoding="utf-8") as f:
    raw_reviews = json.load(f)

# Define monthly profiles with themes and keywords
months_config = {
    "2026-01": {
        "label": "January 2026",
        "weeks": [
            ("2026-01-01", "2026-01-07"),
            ("2026-01-08", "2026-01-14"),
            ("2026-01-15", "2026-01-21"),
            ("2026-01-22", "2026-01-28"),
            ("2026-01-29", "2026-01-31")
        ],
        "themes": [
            {
                "theme_name": "KYC Onboarding Document Rejections",
                "severity": "HIGH",
                "summary": "Onboarding drop-offs due to automated image-processing errors when uploading PAN cards and failed digital signatures.",
                "quotes": [
                    "PAN card auto capture keeps failing and telling me to retry in daylight.",
                    "KYC verification failed 3 times, very bad customer onboarding.",
                    "E-sign signature not working on my phone."
                ],
                "action_ideas": [
                    "Expose detailed camera capture guide overlay with auto-brightness guidelines.",
                    "Provide fallback manual KYC upload button after two failed automated capture attempts.",
                    "Sync e-sign status check directly with NSDL gateway API."
                ],
                "cluster_id": 1,
                "keywords": ["kyc", "pan", "photo", "upload", "onboard", "reject", "document", "signature", "e-sign"]
            },
            {
                "theme_name": "F&O Expiry Option Price Latency",
                "severity": "HIGH",
                "summary": "Real-time F&O price feed lag during peak option expiry hours, leading to delayed position closeouts.",
                "quotes": [
                    "Options chart froze on contract expiry day, lost 5k.",
                    "Websocket disconnects frequently when market opens.",
                    "Price updates are very late in option chains."
                ],
                "action_ideas": [
                    "Reduce option chain WebSocket payload size by sending delta ticks only.",
                    "Implement auto reconnect state machines on options websocket client.",
                    "Show explicit lag status overlay when latency exceeds 2 seconds."
                ],
                "cluster_id": 2,
                "keywords": ["expiry", "options", "price", "delay", "latency", "websocket", "option chain", "freeze", "stuck"]
            },
            {
                "theme_name": "SIP Auto-Pay Activation Failures",
                "severity": "MEDIUM",
                "summary": "Errors in setting up bank mandates and recurring e-mandates for weekly/monthly stock and mutual fund SIPs.",
                "quotes": [
                    "My SIP mandate setup failed but amount was deducted from my bank.",
                    "Auto-pay failed today for my recurring mutual fund.",
                    "Confusing mandate verification process."
                ],
                "action_ideas": [
                    "Implement real-time mandate confirmation checks with NPCI e-mandate portal.",
                    "Expose detailed step-by-step auto-pay setup tutorials on the payment screen.",
                    "Send alert notifications 24 hours prior to auto-pay execution."
                ],
                "cluster_id": 3,
                "keywords": ["sip", "auto-pay", "autopay", "mandate", "recurring", "setup", "bank", "failed", "deducted"]
            }
        ]
    },
    "2026-02": {
        "label": "February 2026",
        "weeks": [
            ("2026-02-01", "2026-02-07"),
            ("2026-02-08", "2026-02-14"),
            ("2026-02-15", "2026-02-21"),
            ("2026-02-22", "2026-02-28")
        ],
        "themes": [
            {
                "theme_name": "Mutual Fund Redemption Delay",
                "severity": "HIGH",
                "summary": "Delays in transferring redemption payouts to users' bank accounts following mutual fund orders.",
                "quotes": [
                    "MF redemption order says completed but money not received in bank account.",
                    "Very slow payout times compared to other platforms.",
                    "Where is my redemption money? It has been 4 days."
                ],
                "action_ideas": [
                    "Expose detailed settlement lifecycle tracking bar on the order detail page.",
                    "Verify direct bank transfer payout pipeline health dynamically.",
                    "Proactively notify users of regional banking holidays affecting transfers."
                ],
                "cluster_id": 1,
                "keywords": ["redemption", "withdraw", "mutual fund", "delay", "payout", "redempt", "money", "bank", "settle"]
            },
            {
                "theme_name": "Stock Chart Rendering Glitches",
                "severity": "MEDIUM",
                "summary": "Stock candlestick charts failing to render properly on specific Android 12 and 13 devices, causing app crashes.",
                "quotes": [
                    "Charts are showing black screen on my OnePlus OnePlus.",
                    "App keeps crashing when I switch to landscape chart view.",
                    "Buggy candle charts make it impossible to trade."
                ],
                "action_ideas": [
                    "Resolve texture memory leaks in WebGL chart container.",
                    "Provide toggle to fallback to simple line chart rendering for low-memory devices.",
                    "Upgrade Google Play Services chart library dependencies."
                ],
                "cluster_id": 2,
                "keywords": ["chart", "render", "candle", "oneplus", "buggy", "rendering", "loading", "black screen", "landscape"]
            },
            {
                "theme_name": "Tax Statement Generation Lag",
                "severity": "LOW",
                "summary": "Portfolio tax statement generation timeouts due to database read locks during tax-filing season preparations.",
                "quotes": [
                    "Cannot download my capital gains report, it shows loading wheel forever.",
                    "Please fix tax statement downloads, I need to submit to CA.",
                    "Confusing capital gains statement formatting."
                ],
                "action_ideas": [
                    "Move capital gains document compiling to a background worker queue.",
                    "Provide CSV tax statement downloads directly on the account profile page.",
                    "Redesign tax report summaries to align with Income Tax Department rules."
                ],
                "cluster_id": 3,
                "keywords": ["tax", "statement", "capital gains", "download", "itr", "financial year", "statement lag", "report"]
            }
        ]
    },
    "2026-03": {
        "label": "March 2026",
        "weeks": [
            ("2026-03-01", "2026-03-07"),
            ("2026-03-08", "2026-03-14"),
            ("2026-03-15", "2026-03-21"),
            ("2026-03-22", "2026-03-28"),
            ("2026-03-29", "2026-03-31")
        ],
        "themes": [
            {
                "theme_name": "Brokerage Charges Transparency",
                "severity": "HIGH",
                "summary": "Discontent surrounding unexpected option brokerage fees and hidden regulatory charges.",
                "quotes": [
                    "Brokrage charges are very High, too much hidden fees.",
                    "brokerage is eating up my small trading profits.",
                    "charges are higher than Zerodha, please reduce brokerage."
                ],
                "action_ideas": [
                    "Expose itemized brokerage breakdowns on the order confirmation sheet.",
                    "Provide a free brokerage calculator utility tool directly inside the user profile.",
                    "Introduce flat brokerage subscription plans for active intraday traders."
                ],
                "cluster_id": 1,
                "keywords": ["brokerage", "broker", "charges", "fees", "hidden", "charging", "commission", "charge"]
            },
            {
                "theme_name": "Nominee Addition Hurdles",
                "severity": "MEDIUM",
                "summary": "Errors in digital signatures and mapping nominee details to folios, causing verification hold-ups.",
                "quotes": [
                    "changed nominee details but it allocated to my old nominee.",
                    "E-sign verification for nominee details fails every time.",
                    "Nominee document rejected without stating proper reasons."
                ],
                "action_ideas": [
                    "Add double-confirmation check screen during digital e-sign nominee mapping.",
                    "Streamline PAN verification of nominee in real-time.",
                    "Improve rejection reason clarity with step-by-step correction instructions."
                ],
                "cluster_id": 2,
                "keywords": ["nominee", "nomination", "e-sign", "signature", "will", "family", "details"]
            },
            {
                "theme_name": "Android 12 Chart Crashing",
                "severity": "HIGH",
                "summary": "App crashes immediately on opening candle charts on specific Android devices with OS version 12.",
                "quotes": [
                    "App keeps crashing on OnePlus 9 when opening charts.",
                    "whenever I look at F&O charts the screen goes black and crashes.",
                    "Very buggy app, closing automatically on my Samsung phone."
                ],
                "action_ideas": [
                    "Resolve memory leaks in options chart rendering library on Android 12.",
                    "Implement a safe fallback chart view for low-memory devices.",
                    "Upgrade Google Play Core SDK library dependencies."
                ],
                "cluster_id": 3,
                "keywords": ["crash", "crashing", "close", "buggy", "samsung", "oneplus", "black", "android", "hang"]
            }
        ]
    },
    "2026-04": {
        "label": "April 2026",
        "weeks": [
            ("2026-04-01", "2026-04-07"),
            ("2026-04-08", "2026-04-14"),
            ("2026-04-15", "2026-04-21"),
            ("2026-04-22", "2026-04-28"),
            ("2026-04-29", "2026-04-30")
        ],
        "themes": [
            {
                "theme_name": "Mutual Fund NAV Date Sync",
                "severity": "HIGH",
                "summary": "Orders placed before cutoff are allocated NAVs of the subsequent day, sparking user complaints regarding price discrepancies.",
                "quotes": [
                    "They choose the NAV date when it is not profitable to us, sometimes they take five days.",
                    "Mutual fund units allocated late, lost on market gains.",
                    "Why is my order still pending? Applied before 2 PM."
                ],
                "action_ideas": [
                    "Sync mutual fund order submission timestamps directly with AMC servers.",
                    "Display explicit NAV cutoff countdown timer on the mutual fund detail view.",
                    "Build automated order routing fallback for late-evening bank processing."
                ],
                "cluster_id": 1,
                "keywords": ["nav", "mutual", "fund", "date", "cutoff", "pending", "units", "allocation"]
            },
            {
                "theme_name": "In-App Search Indexing Lag",
                "severity": "MEDIUM",
                "summary": "Users report that newly listed IPOs and option symbols do not appear in search immediately during opening hours.",
                "quotes": [
                    "Unable to find the new IPO stock in search box.",
                    "Search takes 10 seconds to load stock charts.",
                    "Please make search faster and add search history."
                ],
                "action_ideas": [
                    "Add Redis caching layer for stock search query auto-completion.",
                    "Pre-fetch daily active stock indices into local device storage.",
                    "Redesign search result hierarchy to separate Stocks, Funds, and Indices."
                ],
                "cluster_id": 2,
                "keywords": ["search", "find", "ipo", "symbol", "index", "type", "search bar", "results"]
            },
            {
                "theme_name": "Dark Mode Contrast Legibility",
                "severity": "LOW",
                "summary": "Text in portfolio details is illegible under bright outdoor environments when using the dark theme.",
                "quotes": [
                    "Loving the dark mode updates, but portfolio text is too dark.",
                    "Cannot read order history under sunlight.",
                    "Contrast is very poor in the chart labels in dark mode."
                ],
                "action_ideas": [
                    "Increase font-weight and brightness of secondary text tokens in dark mode.",
                    "Verify order history text adheres to WCAG AA contrast ratio standards.",
                    "Implement a quick toggle for auto-brightness adjustment inside the app."
                ],
                "cluster_id": 3,
                "keywords": ["dark", "light", "contrast", "color", "sunlight", "brightness", "read", "illegible", "text"]
            }
        ]
    },
    "2026-05": {
        "label": "May 2026",
        "weeks": [
            ("2026-05-01", "2026-05-07"),
            ("2026-05-08", "2026-05-14"),
            ("2026-05-15", "2026-05-21"),
            ("2026-05-22", "2026-05-28"),
            ("2026-05-29", "2026-05-31")
        ],
        "themes": [
            {
                "theme_name": "UPI Gateway Latency Spikes",
                "severity": "HIGH",
                "summary": "Transaction timeouts and failed direct bank transfers spike during high volume option-chain expiry days.",
                "quotes": [
                    "Money debited but order not placed. Support says wait 48 hours...",
                    "UPI payment is getting timed out every single time today.",
                    "failed transaction refund is very slow in this app"
                ],
                "action_ideas": [
                    "Integrate a failover secondary UPI gateway handler.",
                    "Enable dynamic warnings for major banks displaying high network latency.",
                    "Optimize instant redemption webhooks to confirm units immediately."
                ],
                "cluster_id": 1,
                "keywords": ["upi", "bank", "pay", "payment", "timeout", "failed", "debited", "transfer", "transaction"]
            },
            {
                "theme_name": "KYC Photo Auto-Crop Failures",
                "severity": "MEDIUM",
                "summary": "Onboarding drop-offs due to automated camera image-processing errors when uploading PAN card details.",
                "quotes": [
                    "Video KYC is not working on my OnePlus device.",
                    "PAN card auto capture keeps failing and telling me to retry in daylight.",
                    "Very difficult kyc verification process, rejected 3 times."
                ],
                "action_ideas": [
                    "Optimize camera cropping overlay resolution and contrast guidelines.",
                    "Provide a fallback manual upload mode after two failed auto-capture attempts.",
                    "Add live in-app onboarding assistance chatbot prompts."
                ],
                "cluster_id": 2,
                "keywords": ["kyc", "crop", "pan", "photo", "document", "upload", "selfie", "verification", "onboarding"]
            },
            {
                "theme_name": "Option Chain Websocket Disconnects",
                "severity": "HIGH",
                "summary": "Real-time F&O prices freeze periodically, forcing users to reload the app to close active option positions.",
                "quotes": [
                    "App glitch during trading cost me 15k! Options chart froze.",
                    "WebSocket connection drops and live option chain prices don't change.",
                    "crashing whenever I open option trading charts."
                ],
                "action_ideas": [
                    "Reduce option chain WebSocket frame payload size by sending delta updates.",
                    "Add an automatic background WebSocket reconnect handler.",
                    "Implement a client-side warning banner when price feeds lag by >2 seconds."
                ],
                "cluster_id": 3,
                "keywords": ["websocket", "f&o", "options", "option", "freeze", "glitch", "chain", "stuck", "position"]
            }
        ]
    },
    "2026-06": {
        "label": "June 2026",
        "weeks": [
            ("2026-06-01", "2026-06-07"),
            ("2026-06-08", "2026-06-14"),
            ("2026-06-15", "2026-06-21"),
            ("2026-06-22", "2026-06-28"),
            ("2026-06-29", "2026-06-30")
        ],
        "themes": [
            {
                "theme_name": "App Performance & Latency Issues",
                "severity": "HIGH",
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
                "cluster_id": 1,
                "keywords": ["freeze", "lag", "crash", "slow", "candlestick", "chart"]
            },
            {
                "theme_name": "Customer Support Response Latency",
                "severity": "HIGH",
                "summary": "Customers experience significant delays in ticket resolution for failed transactions, direct wallet transfers, and onboarding queries.",
                "quotes": [
                    "No Customer Support - There is no customer support. No response to emails. Phone call get disconnected.",
                    "I contacted their chat support. It didn't give proper answer. Then I called their customer care. They assured that the details will be corrected.",
                    "awesome grow apps and very much for your support"
                ],
                "action_ideas": [
                    "Introduce real-time SLA visibility on all opened support tickets in-app.",
                    "Route failed wallet transfer tickets to a priority human queue automatically.",
                    "Provide a direct phone callback request option for transactions stuck > 24 hours."
                ],
                "cluster_id": 2,
                "keywords": ["support", "ticket", "deducted", "wallet", "reply", "unprofessional", "nominee", "customer care"]
            },
            {
                "theme_name": "UX Insights & Reporting Enhancements",
                "severity": "MEDIUM",
                "summary": "Users request direct access to tax statements and annualized return calculators (CAGR), and cite confusing portfolio navigation.",
                "quotes": [
                    "I have been using Groww for quite some time, and my overall experience has been excellent. The app offers a clean, user-friendly interface with smooth navigation...",
                    "outstanding broker ... easy to use and there is also simple interference...",
                    "I can't download this app much money I in vest here"
                ],
                "action_ideas": [
                    "Expose tax report downloads directly on the app profile / home section.",
                    "Simplify portfolio returns hierarchy to display CAGR alongside total absolute returns.",
                    "Redesign the investment dashboard navigation flow to reduce taps to option charts."
                ],
                "cluster_id": 3,
                "keywords": ["cagr", "navigation", "insights", "analytics", "download", "tax", "interface", "ui", "ux"]
            }
        ]
    }
}

periods_metadata = []

# Generate reviews and report files for each week of each month
for month_id, month_data in months_config.items():
    month_period = {
        "month_code": month_id,
        "month_label": month_data["label"],
        "weeks": []
    }
    
    # Extract themes and keywords
    themes = month_data["themes"]
    theme1_keywords = themes[0]["keywords"]
    theme2_keywords = themes[1]["keywords"]
    theme3_keywords = themes[2]["keywords"]
    
    for idx, (start_str, end_str) in enumerate(month_data["weeks"]):
        week_num = idx + 1
        week_label = f"Week {week_num} ({datetime.strptime(start_str, '%Y-%m-%d').strftime('%b %d')} - {datetime.strptime(end_str, '%Y-%m-%d').strftime('%b %d')})"
        
        # Add to metadata
        month_period["weeks"].append({
            "week_label": week_label,
            "start_date": start_str,
            "end_date": end_str
        })
        
        # Partition data specific to this week
        start_dt = datetime.strptime(start_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_str, "%Y-%m-%d")
        days_range = (end_dt - start_dt).days
        
        # Select a random subset of reviews for this week to maintain unique data counts
        sampled_raw = random.sample(raw_reviews, k=random.randint(45, 75))
        
        theme1_count = 0
        theme2_count = 0
        theme3_count = 0
        
        mapped_reviews = []
        for i, review in enumerate(sampled_raw):
            text = review.get("review_text", "").lower()
            
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
                
            # Shift date/time to fall within the week
            random_days = random.randint(0, days_range)
            random_time = timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59), seconds=random.randint(0, 59))
            shifted_dt = start_dt + timedelta(days=random_days) + random_time
            
            rating = review.get("rating", 5)
            if cid == 1:
                rating = random.choice([1, 2, 3])
            elif cid == 2:
                rating = random.choice([1, 2, 3, 4])
            elif cid == 3:
                rating = random.choice([3, 4, 5])
                
            mapped_reviews.append({
                "id": f"{review.get('platform')}_{start_str.replace('-', '')}_{i}",
                "platform": review.get("platform"),
                "author": review.get("author", f"User_{week_num}_{i:03x}"),
                "date": shifted_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "rating": rating,
                "review_text": review.get("review_text"),
                "cluster_id": cid
            })
            
        # Compile report details
        themes_list = []
        for theme in themes:
            count = theme1_count if theme["cluster_id"] == 1 else theme2_count if theme["cluster_id"] == 2 else theme3_count
            themes_list.append({
                "theme_name": theme["theme_name"],
                "severity": theme["severity"],
                "review_count": count,
                "summary": theme["summary"],
                "quotes": theme["quotes"],
                "action_ideas": theme["action_ideas"],
                "cluster_id": theme["cluster_id"]
            })
            
        report = {
            "product": "Groww",
            "iso_week": f"{month_id}-W{week_num}",
            "period_start": start_str,
            "period_end": end_str,
            "themes": themes_list
        }
        
        # Save week files
        file_key = f"{start_str}_{end_str}"
        report_out = os.path.join(DATA_DIR, "reports", f"{file_key}.json")
        reviews_out = os.path.join(DATA_DIR, "reviews", f"{file_key}.json")
        
        with open(report_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        with open(reviews_out, "w", encoding="utf-8") as f:
            json.dump(mapped_reviews, f, indent=2, ensure_ascii=False)
            
    periods_metadata.append(month_period)

# Save periods index JSON
with open(os.path.join(DATA_DIR, "periods.json"), "w", encoding="utf-8") as f:
    json.dump(periods_metadata, f, indent=2, ensure_ascii=False)

print(f"Successfully generated week-by-week datasets in {DATA_DIR}!")
print(f"Generated {len(periods_metadata)} months containing weekly ranges.")
