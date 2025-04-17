import clickhouse_connect as ch

import config
from core.redis_connection import Singleton


class ClickHouseClient(metaclass=Singleton):
    def __init__(
        self,
        click_house_url: str,
        click_house_port: int,
        click_house_username: str,
        click_house_password: str,
    ):
        self.click_house_url = click_house_url
        self.click_house_port = click_house_port
        self.click_house_username = click_house_username
        self.click_house_password = click_house_password
        self._client = None

    async def get_client(self):
        if self._client is None:
            self._client = await ch.get_async_client(
                host=self.click_house_url,
                username=self.click_house_username,
                port=self.click_house_port,
                password=self.click_house_password,
            )
        return self._client


chc = ClickHouseClient(
    click_house_url=config.CLICK_HOUSE_HOST,
    click_house_port=config.CLICK_HOUSE_PORT,
    click_house_username=config.CLICK_HOUSE_USERNAME,
    click_house_password=config.CLICK_HOUSE_PASSWORD,
)


async def get_click_house_client():
    return await chc.get_client()
