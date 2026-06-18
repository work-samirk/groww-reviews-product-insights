import os
import re
import json
import logging
import google.generativeai as genai
from .clusterer import configure_gemini

logger = logging.getLogger(__name__)

def validate_and_correct_quote(candidate_quote, cluster_reviews):
    """
    Validates that candidate_quote appears in one of the raw reviews.
    If it is a partial/paraphrased match, it heals it by returning the actual sentence
    or text from the review. If no match is found, it falls back to a real short review.
    """
    candidate = candidate_quote.strip().lower()
    
    # Remove leading/trailing quotation marks added by LLM
    candidate = re.sub(r'^["\'“]+|["\'”]+$', '', candidate).strip()
    
    # 1. Search for exact substring match in the reviews
    for review in cluster_reviews:
        text = review["review_text"].strip()
        if candidate in text.lower():
            start_idx = text.lower().index(candidate)
            exact_match = text[start_idx : start_idx + len(candidate)]
            return exact_match

    # 2. Word-based check (if LLM modified the punctuation or slightly paraphrased)
    # Check if a review contains a high density of the words in the candidate quote
    words = [w for w in re.findall(r'\b\w+\b', candidate) if len(w) > 3]
    if len(words) >= 3:
        for review in cluster_reviews:
            text = review["review_text"]
            # If at least 80% of the long words are in this review, we'll use a sentence from this review
            matches = sum(1 for w in words if w in text.lower())
            if matches / len(words) >= 0.8:
                # Split review into sentences to find the best matching sentence
                sentences = re.split(r'[.!?]\s*', text)
                for sentence in sentences:
                    if any(w in sentence.lower() for w in words):
                        return sentence.strip()
                return text.strip()

    # 3. Fallback: Return the text of the most relevant review in the cluster
    # We select the review closest in length to the candidate, or just a short review
    if cluster_reviews:
        # Sort reviews by length and pick a concise one (between 20 and 80 chars if possible)
        sorted_reviews = sorted(cluster_reviews, key=lambda r: len(r["review_text"]))
        for r in sorted_reviews:
            if len(r["review_text"]) >= 15:
                return r["review_text"].strip()
        return cluster_reviews[0]["review_text"].strip()
        
    return "No verbatim review text available."

def generate_report_json(clustered_reviews, iso_week):
    """
    Synthesizes clustered reviews using the Gemini LLM.
    If Gemini API keys are missing, uses a rule-based mock builder to construct a realistic report.
    """
    # Group reviews by cluster
    clusters = {}
    for r in clustered_reviews:
        c_id = r["cluster_id"]
        if c_id not in clusters:
            clusters[c_id] = []
        clusters[c_id].append(r)
        
    # Calculate score for each cluster (score = size * (6 - avg_rating))
    cluster_scores = {}
    for cid, reviews_in_cluster in clusters.items():
        if cid == -1:
            continue
        size = len(reviews_in_cluster)
        avg_rating = sum(r["rating"] for r in reviews_in_cluster) / size
        cluster_scores[cid] = size * (6.0 - avg_rating)
        
    # Sort clusters by score (excluding noise cluster -1)
    sorted_cluster_ids = sorted(
        [cid for cid in clusters.keys() if cid != -1],
        key=lambda cid: cluster_scores.get(cid, 0.0),
        reverse=True
    )
    
    # If no clusters found, default to all reviews as cluster 0
    if not sorted_cluster_ids and -1 in clusters:
        sorted_cluster_ids = [-1]

    has_api = configure_gemini()
    themes = []
    
    if has_api:
        try:
            logger.info("Connecting to Gemini LLM to synthesize review themes...")
            # We will use gemini-3.5-flash
            model = genai.GenerativeModel("gemini-3.5-flash")
            
            for cid in sorted_cluster_ids[:3]: # Limit to top 3 themes for conciseness
                reviews_in_cluster = clusters[cid]
                # Combine reviews for LLM context
                reviews_text_block = "\n".join([
                    f"- Rating: {r['rating']}* | Text: {r['review_text']}" 
                    for r in reviews_in_cluster
                ])
                
                prompt = f"""
                You are a product review analyst for the Groww app.
                Analyze the following user reviews that have been clustered together as having a similar theme:
                
                {reviews_text_block}
                
                Provide a JSON response containing:
                1. "theme_name": A short active title (e.g. "App Crashes & Performance Lag")
                2. "summary": A 1-2 sentence description summarizing the core customer issue.
                3. "quotes": Exactly 3 verbatim customer quotes that represent this issue. Keep them short.
                4. "action_ideas": Exactly 3 concrete, actionable features or fixes that the product team can implement.
                
                Respond ONLY with a valid JSON block of this schema:
                {{
                  "theme_name": "string",
                  "summary": "string",
                  "quotes": ["string", "string", "string"],
                  "action_ideas": ["string", "string", "string"]
                }}
                """
                
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                theme_data = json.loads(response.text)
                
                # Validate and correct quotes
                validated_quotes = []
                seen_quotes = set()
                for q in theme_data.get("quotes", []):
                    corrected = validate_and_correct_quote(q, reviews_in_cluster)
                    if corrected not in seen_quotes:
                        seen_quotes.add(corrected)
                        validated_quotes.append(corrected)
                
                # If we have less than 3, try to fill with other unique reviews from the cluster
                if len(validated_quotes) < 3:
                    sorted_reviews = sorted(reviews_in_cluster, key=lambda r: len(r["review_text"]))
                    for r in sorted_reviews:
                        if len(validated_quotes) >= 3:
                            break
                        text_clean = r["review_text"].strip()
                        if text_clean not in seen_quotes and len(text_clean) >= 15:
                            validated_quotes.append(text_clean)
                            seen_quotes.add(text_clean)
                            
                while len(validated_quotes) < 3 and reviews_in_cluster:
                    validated_quotes.append(reviews_in_cluster[0]["review_text"].strip())
                
                theme_data["quotes"] = validated_quotes
                
                # Append severity based on average rating
                avg_rating = sum(r["rating"] for r in reviews_in_cluster) / len(reviews_in_cluster)
                theme_data["severity"] = "HIGH" if avg_rating < 2.5 else "MEDIUM" if avg_rating < 4.0 else "LOW"
                theme_data["review_count"] = len(reviews_in_cluster)
                
                themes.append(theme_data)
                
        except Exception as e:
            logger.error(f"Failed to synthesize report via Gemini API: {e}. Falling back to Rule-based Mock Synthesizer.")
            themes = [] # Reset to trigger fallback
            
    # Mock fallback synthesizer for local testing/dry-runs
    if not themes:
        logger.info("Using local rule-based synthesizer to generate report...")
        
        # We look at the reviews and guess themes based on keywords
        theme_candidates = [
            {
                "keywords": ["freeze", "lag", "crash", "slow", "candlestick", "chart"],
                "theme_name": "App Performance & Latency Issues",
                "summary": "Users report app freezing, slow loading charts, and lagging performance, particularly during the market opening hours.",
                "action_ideas": [
                    "Optimize infrastructure capacity during peak trading hours (9:15 AM - 10:30 AM).",
                    "Implement lightweight chart rendering and local caching for option chains.",
                    "Add connection timeout safety states with user-friendly retry banners."
                ]
            },
            {
                "keywords": ["support", "ticket", "deducted", "wallet", "reply", "unprofessional"],
                "theme_name": "Customer Support Response Latency",
                "summary": "Customers experience significant delays in ticket resolution for failed transactions, direct wallet transfers, and onboarding queries.",
                "action_ideas": [
                    "Introduce real-time SLA visibility on all opened support tickets in-app.",
                    "Route failed wallet transfer tickets to a priority human queue automatically.",
                    "Provide a direct phone callback request option for transactions stuck > 24 hours."
                ]
            },
            {
                "keywords": ["cagr", "navigation", "insights", "analytics", "download", "tax"],
                "theme_name": "UX Insights & Reporting Enhancements",
                "summary": "Users request direct access to tax statements and annualized return calculators (CAGR), and cite confusing portfolio navigation.",
                "action_ideas": [
                    "Expose tax report downloads directly on the app profile / home section.",
                    "Simplify portfolio returns hierarchy to display CAGR alongside total absolute returns.",
                    "Redesign the investment dashboard navigation flow to reduce taps to option charts."
                ]
            }
        ]
        
        # Distribute reviews to matching themes
        for candidate in theme_candidates:
            theme_reviews = []
            for r in clustered_reviews:
                text_lower = r["review_text"].lower()
                if any(k in text_lower for k in candidate["keywords"]):
                    theme_reviews.append(r)
            
            if not theme_reviews:
                # If no matches, take a random sample of low rating reviews for buggy themes
                theme_reviews = [r for r in clustered_reviews if r["rating"] <= 3][:5]
                
            if theme_reviews:
                # Extract unique reviews to avoid duplicate quotes
                unique_reviews = []
                seen_texts = set()
                for r in theme_reviews:
                    text_clean = r["review_text"].strip()
                    if text_clean not in seen_texts:
                        seen_texts.add(text_clean)
                        unique_reviews.append(r)
                
                # Validate and select verbatim quotes
                raw_quotes = [r["review_text"] for r in unique_reviews[:3]]
                validated_quotes = [validate_and_correct_quote(q, unique_reviews) for q in raw_quotes]
                
                # Fill missing quotes if needed from other unique reviews
                if len(validated_quotes) < 3:
                    for r in unique_reviews:
                        if len(validated_quotes) >= 3:
                            break
                        text_clean = r["review_text"].strip()
                        if text_clean not in validated_quotes:
                            validated_quotes.append(text_clean)
                
                while len(validated_quotes) < 3 and unique_reviews:
                    validated_quotes.append(unique_reviews[0]["review_text"].strip())
                
                avg_rating = sum(r["rating"] for r in theme_reviews) / len(theme_reviews)
                severity = "HIGH" if avg_rating < 2.5 else "MEDIUM" if avg_rating < 4.0 else "LOW"
                
                themes.append({
                    "theme_name": candidate["theme_name"],
                    "severity": severity,
                    "review_count": len(theme_reviews),
                    "summary": candidate["summary"],
                    "quotes": validated_quotes[:3],
                    "action_ideas": candidate["action_ideas"]
                })
                
    # Format and return final report structure
    report = {
        "product": "Groww",
        "iso_week": iso_week,
        "period_start": (clustered_reviews[-1]["date"][:10] if clustered_reviews else ""),
        "period_end": (clustered_reviews[0]["date"][:10] if clustered_reviews else ""),
        "themes": themes
    }
    return report
