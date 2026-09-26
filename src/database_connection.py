from typing import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import config

# create async engine for interaction with database
engine = create_async_engine(
    url=config.REAL_DATABASE_URL,
    future=True,
    echo=False,
    execution_options={"isolation_level": "READ COMMITTED"},
)

# create session for the interaction with database
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
async_session_maker = async_session


async def get_db() -> AsyncGenerator:
    """Dependency for getting async session"""
    try:
        session: AsyncSession = async_session()
        yield session
    finally:
        await session.close()


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class RedisClient(metaclass=Singleton):
    def __init__(
        self,
        redis_url: str,
        max_connections: int = 10,
        timeout: int = 1,
        health_check_interval: int = 10,
    ):
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.timeout = timeout
        self.health_check_interval = health_check_interval
        self.client: aioredis.Redis | None = None

    async def connect(self):
        try:
            pool = aioredis.ConnectionPool.from_url(
                self.redis_url, decode_responses=True
            )
            self.client = aioredis.Redis.from_pool(pool)
            print(f"Ping redis successful: {await self.client.ping()}")
        except Exception as e:
            print(f"Redis Error: {e}")

    async def get_client(self) -> aioredis.Redis:
        if self.client is None:
            await self.connect()
        return self.client

    async def close(self):
        if self.client:
            await self.client.aclose()


redis_client = RedisClient(redis_url=config.REDIS_URL)
