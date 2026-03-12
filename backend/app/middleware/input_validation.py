"""Enhanced input validation middleware with spam pattern detection."""

import re
import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)

# Enhanced spam patterns
SPAM_PATTERNS = {
    "repeated_chars": re.compile(r"(.)\1{199,}"),
    "base64_blobs": re.compile(r"(?:data:[^,\s]+;base64,)?[A-Za-z0-9+/]{512,}={0,2}"),
    "hex_blobs": re.compile(r"\b[a-fA-F0-9]{512,}\b"),
    "url_spam": re.compile(r"https?://\S+"),
    "email_spam": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone_spam": re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "ssn": re.compile(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b"),
    "crypto_addresses": re.compile(r"\b(?:0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
    "malicious_keywords": re.compile(
        r"(?i)(sql\s*injection|xss|script|eval|exec|system|shell|cmd|rm\s+-rf)",
        re.IGNORECASE
    ),
    "bot_patterns": re.compile(r"(?i)(bot|crawler|spider|scraper)", re.IGNORECASE),
    "unicode_obfuscation": re.compile(r"[\u200B-\u200D\uFEFF]"),
    "control_chars": re.compile(r"[\x00-\x1F\x7F-\x9F]"),
}

# Content quality checks
MAX_URLS = 100
MAX_EMAILS = 50
MAX_PHONES = 20
MAX_CREDIT_CARDS = 5
MAX_SSNS = 5
MAX_CRYPTO_ADDRESSES = 10

class EnhancedInputValidationMiddleware(BaseHTTPMiddleware):
    """Enhanced input validation with comprehensive spam and security pattern detection."""
    
    async def dispatch(self, request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            # Get request body
            body = await request.body()
            if not body:
                return await call_next(request)
            
            try:
                content = body.decode('utf-8', errors='ignore')
            except UnicodeDecodeError:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid UTF-8 encoding in request body"}
                )
            
            # Perform enhanced validation
            validation_result = self.validate_content(content)
            if not validation_result["is_valid"]:
                logger.warning(
                    "input_validation_failed",
                    reason=validation_result["reason"],
                    client_ip=request.client.host if request.client else "unknown"
                )
                return JSONResponse(
                    status_code=422,
                    content={
                        "error": "Input validation failed",
                        "detail": validation_result["reason"]
                    }
                )
        
        return await call_next(request)
    
    def validate_content(self, content: str) -> dict:
        """Validate content against spam and security patterns."""
        
        # Check for control characters
        if SPAM_PATTERNS["control_chars"].search(content):
            return {"is_valid": False, "reason": "Input contains unsupported control characters"}
        
        # Check for unicode obfuscation
        if SPAM_PATTERNS["unicode_obfuscation"].search(content):
            return {"is_valid": False, "reason": "Input contains unicode obfuscation characters"}
        
        # Check for repeated characters
        if SPAM_PATTERNS["repeated_chars"].search(content):
            return {"is_valid": False, "reason": "Input appears to contain repeated spam content"}
        
        # Check for large encoded blobs
        if (SPAM_PATTERNS["base64_blobs"].search(content) or 
            SPAM_PATTERNS["hex_blobs"].search(content)):
            return {"is_valid": False, "reason": "Input appears to contain a large encoded or binary blob"}
        
        # Check for excessive URLs
        urls = SPAM_PATTERNS["url_spam"].findall(content)
        if len(urls) > MAX_URLS:
            return {"is_valid": False, "reason": f"Input contains too many URLs ({len(urls)} > {MAX_URLS})"}
        
        # Check for excessive emails
        emails = SPAM_PATTERNS["email_spam"].findall(content)
        if len(emails) > MAX_EMAILS:
            return {"is_valid": False, "reason": f"Input contains too many email addresses ({len(emails)} > {MAX_EMAILS})"}
        
        # Check for excessive phone numbers
        phones = SPAM_PATTERNS["phone_spam"].findall(content)
        if len(phones) > MAX_PHONES:
            return {"is_valid": False, "reason": f"Input contains too many phone numbers ({len(phones)} > {MAX_PHONES})"}
        
        # Check for sensitive information
        credit_cards = SPAM_PATTERNS["credit_card"].findall(content)
        if len(credit_cards) > MAX_CREDIT_CARDS:
            return {"is_valid": False, "reason": f"Input contains too many potential credit card numbers ({len(credit_cards)} > {MAX_CREDIT_CARDS})"}
        
        ssn_matches = SPAM_PATTERNS["ssn"].findall(content)
        if len(ssn_matches) > MAX_SSNS:
            return {"is_valid": False, "reason": f"Input contains too many potential SSNs ({len(ssn_matches)} > {MAX_SSNS})"}
        
        crypto_addresses = SPAM_PATTERNS["crypto_addresses"].findall(content)
        if len(crypto_addresses) > MAX_CRYPTO_ADDRESSES:
            return {"is_valid": False, "reason": f"Input contains too many potential crypto addresses ({len(crypto_addresses)} > {MAX_CRYPTO_ADDRESSES})"}
        
        # Check for malicious keywords
        if SPAM_PATTERNS["malicious_keywords"].search(content):
            return {"is_valid": False, "reason": "Input contains potentially malicious content"}
        
        # Check for bot patterns
        if SPAM_PATTERNS["bot_patterns"].search(content):
            return {"is_valid": False, "reason": "Input appears to be from an automated bot"}
        
        # Check content quality
        technical_chars = sum(1 for char in content if char.isalnum())
        if technical_chars < 10:
            return {"is_valid": False, "reason": "Input must contain meaningful technical content"}
        
        # Check for minimum length after cleaning
        cleaned_content = re.sub(r'\s+', ' ', content.strip())
        if len(cleaned_content) < 10:
            return {"is_valid": False, "reason": "Input is too short after cleaning"}
        
        return {"is_valid": True, "reason": None}