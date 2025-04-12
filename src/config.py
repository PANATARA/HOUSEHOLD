import re
import os
from envparse import Env
from decimal import Decimal

env = Env()

""" JWT TOKEN SETTINGS """
SECRET_KEY: str = env.str("SECRET_KEY", default="secret_key")
ALGORITHM: str = env.str("ALGORITHM", default="HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = env.int("ACCESS_TOKEN_EXPIRE_MINUTES", default=30)
REFRESH_TOKEN_EXPIRE_MINUTES: int = env.int(
    "REFRESH_TOKEN_EXPIRE_MINUTES", default=20_160
)


""" DATABASE SETTINGS """
env.read_envfile(os.path.join(os.path.dirname(__file__), "...", ".env"))
REAL_DATABASE_URL = env.str(
    "DATABASE_URL",
    default="postgresql+asyncpg://postgres:postgres@postgres_db:5432/postgres",
)


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
