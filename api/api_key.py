import base64, hmac, hashlib, time
import os
from typing import Dict

from fastapi import Header, HTTPException
from dotenv import load_dotenv

# from core.logger import get_logger

# logger = get_logger(__name__)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY").encode()

def generate_api_key(user_id: str, valid_days: int = 7, unlimited: bool = False):
    if not SECRET_KEY:
        raise HTTPException(status_code=400, detail="Service does not provide secret key!")
    
    expiry = 0 if unlimited else int(time.time()) + valid_days * 86400
    message = f"{user_id}:{expiry}".encode()
    signature = hmac.new(SECRET_KEY, message, hashlib.sha256).hexdigest()
    token = f"{user_id}:{expiry}:{signature}"
    return base64.urlsafe_b64encode(token.encode()).decode()

def verify_api_key(api_key: str = Header(...)) -> Dict:
    if not SECRET_KEY:
        raise HTTPException(status_code=400, detail="Service does not provide secret key!")
    
    try:
        decoded = base64.urlsafe_b64decode(api_key).decode()
        # logger.info(decoded)
        user_id, expiry_str, signature = decoded.split(":")
        expiry = int(expiry_str)

        # Check expiry unless it's unlimited (expiry = 0)
        if expiry != 0 and expiry < time.time():
            raise HTTPException(status_code=401, detail="API key expired")

        message = f"{user_id}:{expiry}".encode()
        expected_sig = hmac.new(SECRET_KEY, message, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            raise HTTPException(status_code=401, detail="Invalid API key")

        return {
            "user_id": user_id,
            "expiry": expiry
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
# print(generate_api_key("jemmy", 1, False))