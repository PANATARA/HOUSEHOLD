from envparse import Env
import os

env = Env()

# env.read_env(os.path.join(os.path.dirname(__file__), '..', '.env'))

# REAL_DATABASE_URL = env.str(
#     "DATABASE_URL",
#     default="postgresql+asyncpg://postgres:postgres@0.0.0.0:5432/postgres",
# )
REAL_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@postgres_db:5432/postgres"