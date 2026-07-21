from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from statistics.schemas import (
    ChoresFamilyCountSchema,
    DateRangeSchema,
    UserChoresCountSchema,
)
from uuid import UUID

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import ENABLE_CLICKHOUSE
from database_connection import clickhouse_client, get_db


class StatsRepository(ABC):
    @abstractmethod
    async def get_family_members_by_chores_completions(
        self, family_id: UUID, interval: DateRangeSchema | None = None
    ) -> list[UserChoresCountSchema]: ...

    @abstractmethod
    async def get_chores_by_completions(
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
    async def get_users_chore_completion_count(
        self, users_ids: list[UUID], interval: DateRangeSchema | None = None
    ) -> list[UserChoresCountSchema]: ...

    @abstractmethod
    async def get_family_chore_completion_count(
        self, family_id: UUID, interval: DateRangeSchema | None = None
    ) -> int: ...

    @abstractmethod
    async def get_family_current_streak(self, family_id: UUID) -> int: ...


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
                    SUM(sign) AS chore_completion_count
                FROM planned_chore_stats
                WHERE {condition}
                GROUP BY completed_by_id
                HAVING chore_completion_count > 0
                ORDER BY chore_completion_count DESC
            """,
            parameters=parameters,
        )

        return [
            UserChoresCountSchema(user_id=row[0], chores_completions_counts=row[1])
            for row in query_result.result_rows
        ]

    async def get_chores_by_completions(
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
                    SUM(sign) AS chore_completion_count
                FROM planned_chore_stats
                WHERE {condition}
                GROUP BY chore_id
                HAVING chore_completion_count > 0
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
                    due_date AS day,
                    SUM(sign) AS chore_completion_count
                FROM planned_chore_stats
                WHERE {condition}
                GROUP BY day
                HAVING chore_completion_count > 0
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
                    due_date AS day,
                    SUM(sign) AS chore_completion_count
                FROM planned_chore_stats
                WHERE {condition}
                GROUP BY day
                HAVING chore_completion_count > 0
                ORDER BY day ASC
            """,
            parameters=parameters,
        )
        return {row[0]: row[1] for row in query_result.result_rows}

    async def get_users_chore_completion_count(
        self,
        users_ids: list[UUID],
        interval: DateRangeSchema | None = None,
    ) -> list[UserChoresCountSchema]:
        if not users_ids:
            return []

        async_client = await clickhouse_client.get_client()
        condition = "completed_by_id IN %(users_ids)s"
        parameters = {"users_ids": [str(uid) for uid in users_ids]}

        condition, parameters = self.__date_condition_parameters(
            condition, parameters, interval
        )

        query_result = await async_client.query(
            query=f"""
                SELECT
                    completed_by_id,
                    SUM(sign) AS completion_count
                FROM planned_chore_stats
                WHERE {condition}
                GROUP BY completed_by_id
                HAVING completion_count > 0
            """,
            parameters=parameters,
        )
        result = {row[0]: row[1] for row in query_result.result_rows}
        return [
            UserChoresCountSchema(
                user_id=uid, chores_completions_counts=result.get(uid, 0)
            )
            for uid in users_ids
        ]

    async def get_family_chore_completion_count(
        self, family_id: UUID, interval: DateRangeSchema | None = None
    ) -> int:
        async_client = await clickhouse_client.get_client()

        condition, parameters = self.__family_date_condition_parameters(
            family_id, interval
        )

        query_result = await async_client.query(
            query=f"""
                SELECT SUM(sign) AS completion_count
                FROM planned_chore_stats
                WHERE {condition}
            """,
            parameters=parameters,
        )
        rows = query_result.result_rows
        if rows and rows[0][0] is not None:
            return max(rows[0][0], 0)
        return 0

    async def get_family_current_streak(self, family_id: UUID) -> int:
        async_client = await clickhouse_client.get_client()
        query_result = await async_client.query(
            query="""
                WITH active_days AS (
                    SELECT
                        toDate(created_at) AS day
                    FROM planned_chore_stats
                    WHERE family_id = {family_id:UUID}
                    GROUP BY day
                    HAVING SUM(sign) > 0
                ),
                anchor AS (
                    SELECT
                        if(max(day) = today(), today(), today() - 1) AS anchor_date
                    FROM active_days
                ),
                ranked AS (
                    SELECT
                        day,
                        row_number() OVER (ORDER BY day DESC) - 1 AS rn
                    FROM active_days
                    WHERE day <= (SELECT anchor_date FROM anchor)
                )
                SELECT count() AS current_streak
                FROM ranked
                WHERE day = (SELECT anchor_date FROM anchor) - rn
            """,
            parameters={"family_id": family_id},
        )
        return query_result.result_rows[0][0] if query_result.result_rows else 0

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
                condition += " AND due_date BETWEEN %(start_date)s AND %(end_date)s"
                parameters["start_date"] = interval.start
                parameters["end_date"] = interval.end
            elif interval.start:
                condition += " AND due_date >= %(start_date)s"
                parameters["start_date"] = interval.start
            elif interval.end:
                condition += " AND due_date <= %(end_date)s"
                parameters["end_date"] = interval.end
        return condition, parameters


@dataclass
class StatsPostgresRepository(StatsRepository):
    db_session: AsyncSession

    async def get_family_members_by_chores_completions(
        self,
        family_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> list[UserChoresCountSchema]:
        condition = "family_id = :family_id AND completed_by_id IS NOT NULL"
        params = {"family_id": str(family_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT completed_by_id, COUNT(*) AS count
            FROM planned_chore
            WHERE {condition}
            GROUP BY completed_by_id
            ORDER BY count DESC
        """)

        result = (await self.db_session.execute(query, params)).all()

        return [
            UserChoresCountSchema(user_id=row[0], chores_completions_counts=row[1])
            for row in result
        ]

    async def get_chores_by_completions(
        self,
        family_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> list[ChoresFamilyCountSchema]:
        condition = "family_id = :family_id AND completed_by_id IS NOT NULL"
        params = {"family_id": str(family_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT chore_id, COUNT(*) AS count
            FROM planned_chore
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
        condition = "family_id = :family_id AND completed_by_id IS NOT NULL"
        params = {"family_id": str(family_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT due_date AS day, COUNT(*) AS count
            FROM planned_chore
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
            SELECT due_date AS day, COUNT(*) AS count
            FROM planned_chore
            WHERE {condition}
            GROUP BY day
            ORDER BY day
        """)

        rows = (await self.db_session.execute(query, params)).all()
        return {row[0]: row[1] for row in rows}

    async def get_users_chore_completion_count(
        self,
        users_ids: list[UUID],
        interval: DateRangeSchema | None = None,
    ) -> list[UserChoresCountSchema]:
        if not users_ids:
            return []

        condition = "completed_by_id = ANY(:user_ids)"
        params = {"user_ids": list(map(str, users_ids))}
        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT completed_by_id, COUNT(*) AS completion_count
            FROM planned_chore
            WHERE {condition}
            GROUP BY completed_by_id
        """)

        rows = (await self.db_session.execute(query, params)).all()
        result = {row[0]: row[1] for row in rows}
        return [
            UserChoresCountSchema(
                user_id=uid, chores_completions_counts=result.get(uid, 0)
            )
            for uid in users_ids
        ]

    async def get_family_chore_completion_count(
        self, family_id: UUID, interval: DateRangeSchema | None = None
    ) -> int:
        condition = "family_id = :family_id AND completed_by_id IS NOT NULL"
        params = {"family_id": str(family_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT COUNT(*)
            FROM planned_chore
            WHERE {condition}
        """)

        rows = (await self.db_session.execute(query, params)).all()

        if rows:
            return rows[0][0]
        return 0

    async def get_family_current_streak(
        self,
        family_id: UUID,
    ) -> int:
        query = text("""
            WITH active_days AS (
                SELECT
                    due_date AS day
                FROM planned_chore
                WHERE family_id = :family_id
                  AND completed_by_id IS NOT NULL
                GROUP BY due_date
            ),

            anchor AS (
                SELECT
                    CASE
                        WHEN MAX(day) IS NULL THEN NULL
                        WHEN MAX(day) >= CURRENT_DATE THEN CURRENT_DATE
                        ELSE CURRENT_DATE - INTERVAL '1 day'
                    END AS anchor_date
                FROM active_days
            ),

            ranked AS (
                SELECT
                    day,
                    ROW_NUMBER() OVER (
                        ORDER BY day DESC
                    ) - 1 AS rn
                FROM active_days
            )

            SELECT COUNT(*)
            FROM ranked
            CROSS JOIN anchor
            WHERE anchor.anchor_date IS NOT NULL
              AND day <= anchor.anchor_date
              AND day = anchor.anchor_date - rn * INTERVAL '1 day'
        """)

        result = await self.db_session.execute(
            query,
            {
                "family_id": family_id,
            },
        )

        return result.scalar_one()

    def _add_date_interval(self, condition, params, interval):
        if interval:
            if interval.start and interval.end:
                condition += " AND due_date BETWEEN :start AND :end"
                params["start"] = interval.start
                params["end"] = interval.end
            elif interval.start:
                condition += " AND due_date >= :start"
                params["start"] = interval.start
            elif interval.end:
                condition += " AND due_date <= :end"
                params["end"] = interval.end

        return condition, params


def get_statistic_repo(
    async_session: AsyncSession = Depends(get_db),
) -> StatsRepository:
    if ENABLE_CLICKHOUSE:
        return StatsClickhouseRepository()
    return StatsPostgresRepository(async_session)
