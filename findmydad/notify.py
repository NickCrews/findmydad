import logging
import os

import requests

logger = logging.getLogger(__name__)


# curl -X POST https://textbelt.com/text \
#        --data-urlencode phone='19073821079' \
#        --data-urlencode message='FindMyDad Alert' \
#        -d key=<key>
def send_sms(*, phone_number: str, message: str = "", api_key: str | None = None):
    if api_key is None:
        # Retrieve the API key from environment variables if not provided
        api_key = os.environ["TEXTBELT_API_KEY"]
    payload = {
        "phone": phone_number,
        "message": "FindMyDad Alert: " + message,
        "key": api_key,
    }
    # Send a POST request to the Textbelt API
    response = requests.post("https://textbelt.com/text", data=payload)
    response.raise_for_status()
    json_response = response.json()
    logger.info(
        f"SMS sent to {phone_number} with message: {message}. Response: {json_response}"
    )
    return json_response
