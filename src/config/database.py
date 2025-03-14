import os

from envparse import Env

env = Env()
env.read_envfile(os.path.join(os.path.dirname(__file__), "...", ".env"))
REAL_DATABASE_URL = env.str(
    "DATABASE_URL",
    default="postgresql+asyncpg://postgres:postgres@postgres_db:5432/postgres",
)
