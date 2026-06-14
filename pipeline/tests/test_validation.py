from pipeline.reasoning.synthesizer import validate_and_correct_quote

def test_exact_match_quote():
    reviews = [
        {"review_text": "The app freezes exactly when the market opens, very frustrating."},
        {"review_text": "Support takes days to reply."}
    ]
    candidate = "Support takes days to reply."
    result = validate_and_correct_quote(candidate, reviews)
    assert result == "Support takes days to reply."

def test_case_insensitive_substring():
    reviews = [
        {"review_text": "The app freezes exactly when the market opens, very frustrating."},
        {"review_text": "Support takes days to reply."}
    ]
    candidate = "the app freezes exactly"
    result = validate_and_correct_quote(candidate, reviews)
    # Should correct the casing to match the original review
    assert result == "The app freezes exactly"

def test_paraphrased_matching_words():
    reviews = [
        {"review_text": "Groww direct mutual funds are completely free. Highly recommend."},
        {"review_text": "Please fix this lag issues."}
    ]
    # LLM might paraphrase to "direct funds are free" which is not a substring
    candidate = "direct funds are free"
    result = validate_and_correct_quote(candidate, reviews)
    assert result == "Groww direct mutual funds are completely free"

def test_validation_fallback():
    reviews = [
        {"review_text": "A very short review text for testing."}
    ]
    candidate = "Completely hallucinated quote by the LLM that does not match."
    result = validate_and_correct_quote(candidate, reviews)
    # Should fall back to the available raw review text
    assert result == "A very short review text for testing."
