import os
import sys

import requests

api_key = os.getenv("TIINGO_API_KEY")
if not api_key:
    print("ERROR: TIINGO_API_KEY is not configured.")
    sys.exit(1)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Token {api_key}",
}

try:
    response = requests.get(
        "https://api.tiingo.com/api/test/",
        headers=headers,
        timeout=20,
    )
except requests.RequestException as exc:
    print(f"Connection error: {type(exc).__name__}")
    sys.exit(1)

print(f"HTTP status: {response.status_code}")

if response.status_code == 200:
    print("Authentication OK.")
    print(response.json())
elif response.status_code in (401, 403):
    print("Authentication failed: check the token.")
    sys.exit(1)
else:
    print("Unexpected response. Check Tiingo's status page and your plan limits.")
    sys.exit(1)