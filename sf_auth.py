"""
Salesforce authentication via JWT Bearer Flow.

No password is ever used. Instead, this proves identity with a private key
(server.key) matched to a certificate uploaded to the Connected App
("Hero FinCorp Bot API") in Salesforce Setup.

server.key must never be committed to source control or shared.
"""
import os
import time
import jwt
import requests
from dotenv import load_dotenv

load_dotenv()

# Read with .get so a workspace running Slack-only (SF_WRITE_MODE=simulate)
# can import this module without blowing up. missing_config() reports what is
# absent, and get_salesforce_token() returns that as a normal error result
# instead of raising.
SF_LOGIN_DOMAIN = os.environ.get("SF_LOGIN_DOMAIN", "")
SF_JWT_AUDIENCE = "https://login.salesforce.com"
SF_CONSUMER_KEY = os.environ.get("SF_CONSUMER_KEY", "")
SF_USERNAME = os.environ.get("SF_USERNAME", "")
SF_PRIVATE_KEY_PATH = os.path.join(os.path.dirname(__file__), "server.key")


def missing_config():
    """What Salesforce needs but does not have. Empty list means ready to go."""
    missing = []
    if not SF_LOGIN_DOMAIN:
        missing.append("SF_LOGIN_DOMAIN")
    if not SF_CONSUMER_KEY:
        missing.append("SF_CONSUMER_KEY")
    if not SF_USERNAME:
        missing.append("SF_USERNAME")
    if not os.path.exists(SF_PRIVATE_KEY_PATH):
        missing.append("server.key")
    return missing


_TOKEN_CACHE = {"result": None, "fetched_at": 0}
_TOKEN_TTL_SECONDS = 25 * 60  # refresh well before any realistic org session timeout


def get_salesforce_token(force_refresh=False):
    missing = missing_config()
    if missing:
        return {"error": "configuration_missing",
                "error_description": f"Salesforce is not configured — missing {', '.join(missing)}. "
                                     f"This is fine for a Slack-only run (SF_WRITE_MODE=simulate)."}

    cached = _TOKEN_CACHE["result"]
    age = time.time() - _TOKEN_CACHE["fetched_at"]
    if cached and not force_refresh and age < _TOKEN_TTL_SECONDS:
        return cached

    with open(SF_PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()

    now = int(time.time())
    payload = {
        "iss": SF_CONSUMER_KEY,
        "sub": SF_USERNAME,
        "aud": SF_JWT_AUDIENCE,
        "exp": now + 180,
    }

    assertion = jwt.encode(payload, private_key, algorithm="RS256")

    url = f"https://{SF_LOGIN_DOMAIN}/services/oauth2/token"
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }
    response = requests.post(url, data=data)
    result = response.json()

    if "access_token" in result:
        _TOKEN_CACHE["result"] = result
        _TOKEN_CACHE["fetched_at"] = time.time()

    return result


if __name__ == "__main__":
    result = get_salesforce_token()
    if "access_token" in result:
        print("AUTH SUCCESS")
        print("instance_url:", result.get("instance_url"))
    else:
        print("AUTH FAILED")
        print("error:", result.get("error"))
        print("error_description:", result.get("error_description"))
