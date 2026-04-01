"""
Get dxFeed streamer token from Tastytrade API.
"""
from utils.auth import get_access_token, get_streamer_token

if __name__ == "__main__":
    try:
        print("Getting access token...")
        access_token = get_access_token()

        streamer_token = get_streamer_token(access_token)

        print(f"\n[OK] Complete! Both tokens obtained and saved.")
    except Exception as e:
        print(f"[FAIL] Error: {e}")
