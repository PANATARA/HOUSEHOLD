import re
import os
from decimal import Decimal

""" JWT TOKEN SETTINGS """
SECRET_KEY: str = os.getenv("SECRET_KEY", default="secret_key")
ALGORITHM: str = os.getenv("ALGORITHM", default="HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", default=30)
)
REFRESH_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", default=20160)
)

""" S3 SETTINGS """
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", default="S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", default="S3_SECRET_KEY")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", default="S3_ENDPOINT_URL")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", default="S3_BUCKET_NAME")


""" DATABASE SETTINGS """
REAL_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    default="postgresql+asyncpg://postgres:postgres@postgres_db:5432/postgres",
)
REDIS_URL = os.getenv("redis_url", default="redis://redis:6379")

CLICK_HOUSE_HOST: str = os.getenv("CLICK_HOUSE_HOST", default="localhost")
CLICK_HOUSE_PORT: int = int(os.getenv("CLICK_HOUSE_PORT", default="8123"))
CLICK_HOUSE_USERNAME: str = os.getenv("CLICK_HOUSE_USERNAME", default="default")
CLICK_HOUSE_PASSWORD: str= os.getenv("CLICK_HOUSE_PASSWORD", default="clickhouse")

""" VALIDATION SETTTINGS """
PASSWORD_PATTERN = re.compile(r"^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$")
LETTER_MATCH_PATTERN = re.compile(r"^[а-яА-Яa-zA-Z\-]+$")


""" JSON SCHEMA SETTINGS """
swagger_ui_settings = {
    "deepLinking": True,
    "displayOperationId": True,
    "syntaxHighlight.active": True,
    "syntaxHighlight.theme": "arta",
    "defaultModelsExpandDepth": 1,
    "docExpansion": "list",
    "displayRequestDuration": True,
    "filter": True,
    "requestSnippetsEnabled": True,
}


""" APP SETTINGS """
TRANSFER_RATE = Decimal(0.7)
PURCHASE_RATE = Decimal(0.8)
