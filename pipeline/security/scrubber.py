import re
import hashlib

# Regex Patterns for PII
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_REGEX = re.compile(r'\b(?:\+91[\-\s]?)?[6-9]\d{9}\b|\b\d{5}[\-\s]?\d{5}\b')
AADHAAR_REGEX = re.compile(r'\b\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b')
PAN_REGEX = re.compile(r'\b[A-Za-z]{5}\d{4}[A-Za-z]\b')
CARD_REGEX = re.compile(r'\b\d{4}[\-\s]?\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b')
OTP_REGEX = re.compile(r'\b\d{4,6}\b') # Matches 4-6 digit numeric OTPs if mentioned in reviews

def anonymize_author(author_name):
    """
    Consistently maps an author name to an anonymous user ID.
    E.g. "Aarav Sharma" -> "User_8f3a"
    """
    if not author_name or author_name.strip() == "":
        return "Anonymous_User"
    
    # Generate MD5 hash of the author's name
    hash_object = hashlib.md5(author_name.strip().lower().encode('utf-8'))
    hash_hex = hash_object.hexdigest()
    # Use first 4 characters for a short consistent ID
    return f"User_{hash_hex[:4]}"

def scrub_text(text):
    """
    Scrubs PII (Emails, Phones, Aadhaar, PAN, Credit Cards, OTPs) from text.
    """
    if not text:
        return ""
        
    scrubbed = text
    
    # 1. Scrub Email Addresses
    scrubbed = EMAIL_REGEX.sub("[EMAIL_MASKED]", scrubbed)
    
    # 2. Scrub Phone Numbers
    scrubbed = PHONE_REGEX.sub("[PHONE_MASKED]", scrubbed)
    
    # 3. Scrub Aadhaar Cards
    scrubbed = AADHAAR_REGEX.sub("[AADHAAR_MASKED]", scrubbed)
    
    # 4. Scrub PAN Cards
    scrubbed = PAN_REGEX.sub("[PAN_MASKED]", scrubbed)
    
    # 5. Scrub Credit/Debit Cards
    scrubbed = CARD_REGEX.sub("[CARD_MASKED]", scrubbed)
    
    # 6. Scrub OTPs - typically mentioned like "OTP is 1234" or "received 456789"
    # To avoid scrubbing general numbers, we check common prefix indicators:
    # E.g. "otp", "code", "pin"
    scrubbed = re.sub(
        r'\b(otp|code|pin|verification)\s*(?:is|of)?\s*:?\s*\d{4,6}\b', 
        r'\1 is [OTP_MASKED]', 
        scrubbed, 
        flags=re.IGNORECASE
    )
    
    return scrubbed

def scrub_review(review_dict):
    """
    Accepts a review dict and returns a copy with scrubbed author and review_text.
    """
    scrubbed = review_dict.copy()
    scrubbed["author"] = anonymize_author(review_dict.get("author", ""))
    scrubbed["review_text"] = scrub_text(review_dict.get("review_text", ""))
    return scrubbed
