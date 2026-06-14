from pipeline.security.scrubber import scrub_text, anonymize_author

def test_scrub_email():
    text = "Hello, please contact me at user@example.com for details."
    scrubbed = scrub_text(text)
    assert "user@example.com" not in scrubbed
    assert "[EMAIL_MASKED]" in scrubbed

def test_scrub_phone():
    text = "Call me at +91 9876543210 or 9988776655."
    scrubbed = scrub_text(text)
    assert "9876543210" not in scrubbed
    assert "9988776655" not in scrubbed
    assert "[PHONE_MASKED]" in scrubbed

def test_scrub_aadhaar():
    text = "My Aadhaar card number is 1234-5678-9012."
    scrubbed = scrub_text(text)
    assert "1234-5678-9012" not in scrubbed
    assert "[AADHAAR_MASKED]" in scrubbed

def test_scrub_pan():
    text = "Here is my PAN details: ABCDE1234F."
    scrubbed = scrub_text(text)
    assert "ABCDE1234F" not in scrubbed
    assert "[PAN_MASKED]" in scrubbed

def test_scrub_otp():
    text = "Do not share this. Your verification code is 123456."
    scrubbed = scrub_text(text)
    assert "123456" not in scrubbed
    assert "[OTP_MASKED]" in scrubbed

def test_anonymize_author():
    author = "Amit Kumar"
    anon1 = anonymize_author(author)
    anon2 = anonymize_author(author)
    
    # Assert same author hashes consistently
    assert anon1 == anon2
    assert "Amit" not in anon1
    assert anon1.startswith("User_")
