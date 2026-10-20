# Test Tiingo API authentication without displaying the API token.
import os
import sys
import requests

# Retrieve the API token from the environment.
api_key = os.getenv("TIINGO_API_KEY")

# Stop if the token has not been configured.
if not api_key:
    print("ERROR: TIINGO_API_KEY is not configured.")
    sys.exit(1)

# Configure authentication using an HTTP header.
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Token {api_key}",
}

# Call Tiingo's official API connectivity test endpoint.
try:
    response = requests.get(
        "https://api.tiingo.com/api/test/",
        headers=headers,
        timeout=20,
    )

    # Display the HTTP status and a sanitised response.
    print(f"HTTP status: {response.status_code}")

    if response.ok:
        print("API authentication test: SUCCESS")
        print(f"Response: {response.json()}")
    else:
        print("API authentication test: FAILED")
        print("Response:", response.text[:300])

except requests.RequestException as exc:
    # Display connection errors without exposing credentials.
    print(f"Connection error: {type(exc).__name__}")
    sys.exit(1)