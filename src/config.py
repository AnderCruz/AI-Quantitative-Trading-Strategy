# Import the environment and path utilities.
import os
from pathlib import Path

# Import dotenv support for optional local configuration.
from dotenv import load_dotenv


# Define the project root directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load environment variables from the project-root .env file if present.
# Existing environment variables are not overwritten by default.
load_dotenv(PROJECT_ROOT / ".env")


def get_tiingo_api_key() -> str:
    """Return the Tiingo API key or raise an error if it is unavailable."""

    # Retrieve the API key from the environment.
    api_key = os.getenv("TIINGO_API_KEY")

    # Reject missing or whitespace-only credentials.
    if not api_key or not api_key.strip():
        raise RuntimeError(
            "TIINGO_API_KEY is not configured. "
            "Set it as an environment variable or in the project-root .env file."
        )

    # Return the credential without printing or logging it.
    return api_key.strip()
