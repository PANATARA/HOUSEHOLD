import asyncio
import logging
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

import config

logger = logging.getLogger(__name__)


class InvalidGoogleTokenError(Exception):
    pass


def _sync_verify_google_token(token: str, client_id: str | None = None) -> dict:
    try:
        request = google_requests.Request()
        id_info = google_id_token.verify_oauth2_token(
            token,
            request,
            audience=client_id if client_id else None,
        )
        if id_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            raise InvalidGoogleTokenError(f"Invalid token issuer: {id_info.get('iss')}")
        return id_info
    except (ValueError, GoogleAuthError) as e:
        logger.warning(f"Google token verification failed: {e}")
        raise InvalidGoogleTokenError(str(e))


async def verify_google_id_token(token: str) -> dict:
    return await asyncio.to_thread(_sync_verify_google_token, token, config.GOOGLE_CLIENT_ID)
