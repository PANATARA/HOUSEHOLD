import json
from typing import AsyncGenerator

import aio_pika
import redis.asyncio as aioredis
import clickhouse_connect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import config


# create async engine for interaction with database
engine = create_async_engine(
    url=config.REAL_DATABASE_URL,
    future=True,
    echo=True,
    execution_options={"isolation_level": "REPEATABLE READ"},
)

# create session for the interaction with database
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


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


class ClickHouseClient(metaclass=Singleton):
    def __init__(self):
        self.host = config.CLICKHOUSE_HOST
        self.port = config.CLICKHOUSE_PORT
        self.user = config.CLICKHOUSE_USER
        self.password = config.CLICKHOUSE_PASSWORD
        self._client: clickhouse_connect.driver.asyncclient.AsyncClient | None = None

    async def connect(self):
        if self._client is None:
            self._client = await clickhouse_connect.get_async_client(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
            )
            await self._client.query("SELECT 1")
            print("ClickHouse connected")

    async def get_client(self):
        if self._client is None:
            await self.connect()
        return self._client

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None
            print("ClickHouse connection closed")


class RabbitMQClient(metaclass=Singleton):
    def __init__(self, url: str):
        self.url = url
        self.connection = None
        self.channel = None

    async def connect(self):
        if not self.connection:
            self.connection = await aio_pika.connect_robust(self.url)
            self.channel = await self.connection.channel()

    async def publish(self, message: dict):
        if not self.connection:
            await self.connect()

        exchange = await self.channel.get_exchange("clickhouse_exchange")

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="completions",
        )

    async def close(self):
        if self.connection:
            await self.connection.close()
            print("ClickHouse connection closed")


redis_client = RedisClient(redis_url=config.REDIS_URL)
clickhouse_client = ClickHouseClient()
rabbit_client = RabbitMQClient(config.RABBITMQ_URL)
