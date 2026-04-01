"""
Get Tastytrade access token using OAuth2 refresh token flow.
"""
from utils.auth import get_access_token

if __name__ == "__main__":
    try:
        access_token = get_access_token(force_refresh=True)
        print(f"\n[OK] Access token obtained and saved!")
        print(f"Token file: tasty_token.json")
    except Exception as e:
        print(f"[FAIL] Error: {e}")
