import redis.asyncio as aioredis

from config import REDIS_URL


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

    async def close(self):
        if self.client:
            await self.client.aclose()

    def get_client(self):
        return self.client


redis_client = RedisClient(redis_url=REDIS_URL)
