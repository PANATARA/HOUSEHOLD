import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiofiles
import aiosmtplib

from config import EMAIL_ADDRESS, EMAIL_HOSTNAME, EMAIL_PASSWORD

current_dir = os.path.dirname(__file__)
template_path = os.path.join(current_dir, "email_template.html")


async def send_email_secret_code(to_email: str, secret_code: int):
    email_address = EMAIL_ADDRESS
    email_password = EMAIL_PASSWORD

    async with aiofiles.open(template_path, "r", encoding="utf-8") as f:
        html_template = await f.read()

    html_content = html_template.replace("{{code}}", str(secret_code))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{secret_code} - Ваш код входа в HouseHold"
    msg["From"] = email_address
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html"))

    await aiosmtplib.send(
        msg,
        hostname=EMAIL_HOSTNAME,
        port=465,
        username=email_address,
        password=email_password,
        use_tls=True,
    )


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

