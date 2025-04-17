from dataclasses import dataclass
from clickhouse_connect.driver import AsyncClient


@dataclass
class ClickHouseRepository:
    async_client: AsyncClient

    async def create_chore_stats_table(self):
        await self.async_client.command(
            """
                CREATE TABLE IF NOT EXISTS chores_completions_stats (
                    family_id UUID,
                    chore_id UUID,
                    user_id UUID,
                    completion_date Date
                ) ENGINE AggregatingMergeTree()
                PARTITION BY toStartOfWeek(completion_date)
                ORDER BY (family_id, chore_id, completion_date)
            """
        )
