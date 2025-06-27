import os
import aiosmtplib
import aiofiles
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_HOSTNAME

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
