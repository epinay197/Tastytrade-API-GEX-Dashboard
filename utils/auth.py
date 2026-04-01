"""
Authentication utilities for Tastytrade API
Handles OAuth2 token exchange and dxFeed streamer token retrieval
"""
import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

# Token file paths
TOKEN_FILE = "tasty_token.json"
STREAMER_TOKEN_FILE = "streamer_token.json"

# Load environment variables from .env file
load_dotenv()


def load_credentials_from_env():
    """
    Load Tastytrade API credentials from environment variables.
    """
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    refresh_token = os.getenv('REFRESH_TOKEN')

    if not client_id or not client_secret or not refresh_token:
        raise ValueError(
            "Missing required environment variables. "
            "Please ensure CLIENT_ID, CLIENT_SECRET, and REFRESH_TOKEN are set in .env file"
        )

    return {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token
    }


def get_access_token(force_refresh=False):
    """
    Get Tastytrade access token using OAuth2 refresh token flow.
    """
    # Try to load cached token first
    if not force_refresh and os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)

                if 'access_token' in token_data and 'expires_at' in token_data:
                    expires_at = token_data['expires_at']
                    current_time = time.time()

                    if expires_at > current_time + 60:
                        time_remaining = int(expires_at - current_time)
                        print(f"[OK] Using cached access token (expires in {time_remaining}s)")
                        return token_data['access_token']
                    else:
                        print("[!] Access token expired or expiring soon, refreshing...")
        except Exception as e:
            print(f"[!] Could not load cached token: {e}")

    # Fetch new token via OAuth2
    print("[*] Fetching new access token from Tastytrade...")
    credentials = load_credentials_from_env()

    data = {
        "grant_type": "refresh_token",
        "refresh_token": credentials['refresh_token'],
        "client_id": credentials['client_id'],
        "client_secret": credentials['client_secret']
    }

    response = requests.post("https://api.tastytrade.com/oauth/token", data=data)

    if response.status_code == 200:
        token_response = response.json()
        access_token = token_response["access_token"]
        expires_in = token_response.get("expires_in", 900)

        expires_at = time.time() + expires_in

        token_data = {
            "access_token": access_token,
            "expires_in": expires_in,
            "expires_at": expires_at,
            "fetched_at": time.time()
        }

        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f, indent=2)

        print(f"[OK] Access token obtained! (valid for {expires_in}s)")
        return access_token
    else:
        raise Exception(
            f"Failed to get access token. Status code: {response.status_code}\n"
            f"Response: {response.text}"
        )


def get_streamer_token(access_token=None, force_refresh=False):
    """
    Get dxFeed streamer token from Tastytrade API.
    """
    # Try to load cached token first
    if not force_refresh and os.path.exists(STREAMER_TOKEN_FILE):
        try:
            with open(STREAMER_TOKEN_FILE, 'r') as f:
                token_data = json.load(f)

                if 'token' in token_data and 'expires_at' in token_data:
                    expires_at = token_data['expires_at']
                    current_time = time.time()

                    if expires_at > current_time + 300:
                        time_remaining = int((expires_at - current_time) / 3600)
                        print(f"[OK] Using cached streamer token (expires in ~{time_remaining}h)")
                        return token_data['token']
                    else:
                        print("[!] Streamer token expired or expiring soon, refreshing...")
        except Exception as e:
            print(f"[!] Could not load cached streamer token: {e}")

    # Get fresh access token if not provided
    if access_token is None:
        access_token = get_access_token()

    print("[*] Fetching dxFeed streamer token...")

    # Try the main API endpoint first
    url = "https://api.tastytrade.com/api-quote-tokens"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)

    # Fallback to legacy endpoint if needed
    if response.status_code != 200:
        url = "https://api.tastyworks.com/api-quote-tokens"
        response = requests.get(url, headers=headers)

    if response.status_code == 200:
        result = response.json()
        data = result.get('data', {})
        streamer_token = data.get('token')

        if not streamer_token:
            raise Exception(f"No token in response: {result}")

        expires_in = 20 * 3600
        expires_at = time.time() + expires_in

        token_data = {
            "token": streamer_token,
            "expires_in": expires_in,
            "expires_at": expires_at,
            "fetched_at": time.time()
        }

        with open(STREAMER_TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)

        print(f"[OK] Streamer token obtained! (valid for ~{expires_in/3600:.0f}h)")
        return streamer_token
    else:
        raise Exception(
            f"Failed to get streamer token. Status code: {response.status_code}\n"
            f"Response: {response.text}"
        )


def ensure_streamer_token():
    """
    Ensure we have a valid streamer token with automatic expiration checking.
    This is the main function used by the dashboard.
    """
    return get_streamer_token()


if __name__ == "__main__":
    print("Testing authentication flow...\n")

    try:
        creds = load_credentials_from_env()
        print("[OK] Credentials loaded successfully\n")
    except Exception as e:
        print(f"[FAIL] Error loading credentials: {e}\n")
        exit(1)

    try:
        access_token = get_access_token()
        print("[OK] Access token obtained successfully\n")
    except Exception as e:
        print(f"[FAIL] Error getting access token: {e}\n")
        exit(1)

    try:
        streamer_token = get_streamer_token(access_token)
        print("[OK] Streamer token obtained successfully\n")
    except Exception as e:
        print(f"[FAIL] Error getting streamer token: {e}\n")
        exit(1)

    print("[OK] All authentication tests passed!")
