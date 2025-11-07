from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import ENABLE_CLICKHOUSE
from statistics.schemas import (
    ChoresFamilyCountSchema,
    DateRangeSchema,
    UserChoresCountSchema,
)
from database_connection import clickhouse_client, get_db


class StatsRepository(ABC):
    @abstractmethod
    async def get_family_members_by_chores_completions(
        self, family_id: UUID, interval: DateRangeSchema | None = None
    ) -> list[UserChoresCountSchema]: ...

    @abstractmethod
    async def get_family_chores_by_completions(
        self, family_id: UUID, interval: DateRangeSchema | None = None
    ) -> list[ChoresFamilyCountSchema]: ...

    @abstractmethod
    async def get_family_heatmap(
        self, family_id: UUID, interval: DateRangeSchema | None = None
    ) -> dict[date, int]: ...

    @abstractmethod
    async def get_user_heatmap(
        self, completed_by_id: UUID, interval: DateRangeSchema | None = None
    ) -> dict[date, int]: ...

    @abstractmethod
    async def get_user_chore_completion_count(
        self, completed_by_id: UUID, interval: DateRangeSchema | None = None
    ) -> tuple[UUID, int]: ...


class StatsClickhouseRepository(StatsRepository):
    async def get_family_members_by_chores_completions(
        self,
        family_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> list[UserChoresCountSchema]:
        async_client = await clickhouse_client.get_client()

        condition, parameters = self.__family_date_condition_parameters(
            family_id, interval
        )

        query_result = await async_client.query(
            query=f"""
                SELECT 
                    completed_by_id, 
                    count(*) AS chore_completion_count
                FROM chore_completion_stats
                WHERE {condition}
                GROUP BY completed_by_id
                ORDER BY chore_completion_count DESC
            """,
            parameters=parameters,
        )

        return [
            UserChoresCountSchema(user_id=row[0], chores_completions_counts=row[1])
            for row in query_result.result_rows
        ]

    async def get_family_chores_by_completions(
        self,
        family_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> list[ChoresFamilyCountSchema]:
        async_client = await clickhouse_client.get_client()

        condition, parameters = self.__family_date_condition_parameters(
            family_id, interval
        )

        query_result = await async_client.query(
            query=f"""
                SELECT 
                    chore_id, 
                    count(*) AS chore_completion_count
                FROM chore_completion_stats
                WHERE {condition}
                GROUP BY chore_id
                ORDER BY chore_completion_count DESC
            """,
            parameters=parameters,
        )

        return [
            ChoresFamilyCountSchema(chore_id=row[0], chores_completions_counts=row[1])
            for row in query_result.result_rows
        ]

    async def get_family_heatmap(
        self,
        family_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> dict[date, int]:
        async_client = await clickhouse_client.get_client()

        condition, parameters = self.__family_date_condition_parameters(
            family_id, interval
        )

        query_result = await async_client.query(
            query=f"""
                SELECT 
                    toDate(created_at) AS day,
                    count(*) AS chore_completion_count
                FROM chore_completion_stats
                WHERE {condition}
                GROUP BY day
                ORDER BY day ASC
            """,
            parameters=parameters,
        )
        return {row[0]: row[1] for row in query_result.result_rows}

    async def get_user_heatmap(
        self,
        completed_by_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> dict[date, int]:
        async_client = await clickhouse_client.get_client()

        condition, parameters = self.__user_date_condition_parameters(
            completed_by_id, interval
        )

        query_result = await async_client.query(
            query=f"""
                SELECT 
                    toDate(created_at) AS day,
                    count(*) AS chore_completion_count
                FROM chore_completion_stats
                WHERE {condition}
                GROUP BY day
                ORDER BY day ASC
            """,
            parameters=parameters,
        )
        return {row[0]: row[1] for row in query_result.result_rows}

    async def get_user_chore_completion_count(
        self,
        completed_by_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> tuple[UUID, int]:
        async_client = await clickhouse_client.get_client()

        condition, parameters = self.__user_date_condition_parameters(
            completed_by_id, interval
        )

        query_result = await async_client.query(
            query=f"""
                SELECT 
                    completed_by_id,
                    count(*) AS completion_count
                FROM chore_completion_stats
                WHERE {condition}
                GROUP BY completed_by_id
            """,
            parameters=parameters,
        )
        rows = query_result.result_rows
        if rows:
            return (rows[0][0], rows[0][1])
        return (completed_by_id, 0)

    def __family_date_condition_parameters(
        self, family_id: UUID, interval: DateRangeSchema | None = None
    ) -> tuple[str, dict]:
        condition = "family_id = %(family_id)s"
        parameters = {"family_id": str(family_id)}

        return self.__date_condition_parameters(condition, parameters, interval)

    def __user_date_condition_parameters(
        self, completed_by_id: UUID, interval: DateRangeSchema | None = None
    ) -> tuple[str, dict]:
        condition = "completed_by_id = %(completed_by_id)s"
        parameters = {"completed_by_id": str(completed_by_id)}

        return self.__date_condition_parameters(condition, parameters, interval)

    def __date_condition_parameters(
        self, condition: str, parameters: dict, interval: DateRangeSchema | None = None
    ) -> tuple[str, dict]:
        if interval:
            if interval.start and interval.end:
                condition += (
                    " AND toDate(created_at) BETWEEN %(start_date)s AND %(end_date)s"
                )
                parameters["start_date"] = interval.start.date()
                parameters["end_date"] = interval.end.date()
            elif interval.start:
                condition += " AND toDate(created_at) >= %(start_date)s"
                parameters["start_date"] = interval.start.date()
            elif interval.end:
                condition += " AND toDate(created_at) <= %(end_date)s"
                parameters["end_date"] = interval.end.date()
        return condition, parameters


@dataclass
class StatsPostgresRepository(StatsRepository):
    db_session: AsyncSession

    async def get_family_members_by_chores_completions(
        self,
        family_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> list[UserChoresCountSchema]:
        condition = "family_id = :family_id"
        params = {"family_id": str(family_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT completed_by_id, COUNT(*) AS count
            FROM chore_completion
            WHERE {condition}
            GROUP BY completed_by_id
            ORDER BY count DESC
        """)

        result = (await self.db_session.execute(query, params)).all()

        return [
            UserChoresCountSchema(user_id=row[0], chores_completions_counts=row[1])
            for row in result
        ]

    async def get_family_chores_by_completions(
        self,
        family_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> list[ChoresFamilyCountSchema]:
        condition = "family_id = :family_id"
        params = {"family_id": str(family_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT chore_id, COUNT(*) AS count
            FROM chore_completion
            WHERE {condition}
            GROUP BY chore_id
            ORDER BY count DESC
        """)

        result = (await self.db_session.execute(query, params)).all()

        return [
            ChoresFamilyCountSchema(chore_id=row[0], chores_completions_counts=row[1])
            for row in result
        ]

    async def get_family_heatmap(
        self,
        family_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> dict[date, int]:
        condition = "family_id = :family_id"
        params = {"family_id": str(family_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT DATE(created_at) AS day, COUNT(*) AS count
            FROM chore_completion
            WHERE {condition}
            GROUP BY day
            ORDER BY day
        """)

        rows = (await self.db_session.execute(query, params)).all()
        return {row[0]: row[1] for row in rows}

    async def get_user_heatmap(
        self,
        completed_by_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> dict[date, int]:
        condition = "completed_by_id = :completed_by_id"
        params = {"completed_by_id": str(completed_by_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT DATE(created_at) AS day, COUNT(*) AS count
            FROM chore_completion
            WHERE {condition}
            GROUP BY day
            ORDER BY day
        """)

        rows = (await self.db_session.execute(query, params)).all()
        return {row[0]: row[1] for row in rows}

    async def get_user_chore_completion_count(
        self,
        completed_by_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> tuple[UUID, int]:
        condition = "completed_by_id = :completed_by_id"
        params = {"completed_by_id": str(completed_by_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT completed_by_id, COUNT(*)
            FROM chore_completion
            WHERE {condition}
            GROUP BY completed_by_id
        """)

        rows = (await self.db_session.execute(query, params)).all()

        if rows:
            return (rows[0][0], rows[0][1])
        return (completed_by_id, 0)

    def _add_date_interval(self, condition, params, interval):
        if interval:
            if interval.start and interval.end:
                condition += " AND DATE(created_at) BETWEEN :start AND :end"
                params["start"] = interval.start.date()
                params["end"] = interval.end.date()
            elif interval.start:
                condition += " AND DATE(created_at) >= :start"
                params["start"] = interval.start.date()
            elif interval.end:
                condition += " AND DATE(created_at) <= :end"
                params["end"] = interval.end.date()

        return condition, params


def get_statistic_repo(
    async_session: AsyncSession = Depends(get_db),
) -> StatsRepository:
    if ENABLE_CLICKHOUSE:
        return StatsClickhouseRepository()
    return StatsPostgresRepository(async_session)
