from dataclasses import dataclass
from datetime import date
from uuid import UUID
from clickhouse_connect.driver import AsyncClient

from analytics.schemas import ChoreAnalyticSchema


@dataclass
class ChoreAnalyticRepository:
    async_client: AsyncClient

    async def create_chore_stats_table(self):
        await self.async_client.command(
            """
                CREATE TABLE IF NOT EXISTS chores_completions_stats (
                    family_id UUID,
                    chore_id UUID,
                    user_id UUID,
                    completion_date Date
                ) ENGINE MergeTree()
                PARTITION BY toStartOfWeek(completion_date)
                ORDER BY (family_id, chore_id, completion_date)
            """
        )

    async def add_new_entry(self, data: ChoreAnalyticSchema):
        data = [list(data.model_dump().values())]

        query_summary = await self.async_client.insert(
            table="chores_completions_stats",
            data=data,
            column_names=["family_id", "chore_id", "user_id", "completion_date"],
        )
        return query_summary

    async def get_family_members_by_chores_completions(
        self, family_id: UUID, interval_start: date, interval_end: date
    ) -> list[tuple[UUID, int]]:
        query_result = await self.async_client.query(
            query=
            """
                SELECT 
                    user_id, 
                    count(*) AS chore_completion_count
                FROM chores_completions_stats
                WHERE family_id = %(family_id)s
                    AND completion_date BETWEEN %(start_date)s AND %(end_date)s
                GROUP BY user_id
                ORDER BY chore_completion_count DESC
            """,
            parameters={
                "family_id": str(family_id),
                "start_date": interval_start,
                "end_date": interval_end,
            },
        )
        return query_result.result_rows
