import os
import re

""" JWT TOKEN SETTINGS """
SECRET_KEY: str = os.getenv("SECRET_KEY", default="secret_key")
ALGORITHM: str = os.getenv("ALGORITHM", default="HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", default=30)
)
REFRESH_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", default=20160)
)


""" LOCAL STORAGE SETTINGS """
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(os.path.dirname(BASE_DIR), "uploads")
STATIC_DIR = os.getenv(
    "STATIC_DIR", default=os.path.join(os.path.dirname(BASE_DIR), "static")
)
SERVE_FRONTEND: bool = os.getenv("SERVE_FRONTEND", default="False").lower() in (
    "true",
    "1",
    "yes",
)
BASE_URL = os.getenv("BASE_URL", default="localhost:8000")


""" DATABASE SETTINGS """
REAL_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    default="postgresql+asyncpg://postgres:postgres@postgres_db:5432/postgres",
)
REDIS_URL = os.getenv("redis_url", default="redis://redis:6379")


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


""" FCM / NOTIFICATIONS SETTINGS """
FCM_CREDENTIALS_PATH: str | None = os.getenv("FCM_CREDENTIALS_PATH")
FCM_CREDENTIALS_JSON: str | None = os.getenv("FCM_CREDENTIALS_JSON")


""" GOOGLE AUTH SETTINGS """
GOOGLE_CLIENT_ID: str | None = os.getenv("GOOGLE_CLIENT_ID")
