from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database_connection import get_db
from statistics.schemas import (
    ChoresFamilyCountSchema,
    DateRangeSchema,
    UserChoresCountSchema,
)


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

    @abstractmethod
    async def get_user_current_streak(self, user_id: UUID) -> int: ...


@dataclass
class StatsPostgresRepository(StatsRepository):
    db_session: AsyncSession

    async def get_family_members_by_chores_completions(
        self,
        family_id: UUID,
        interval: DateRangeSchema | None = None,
    ) -> list[UserChoresCountSchema]:
        condition = (
            "family_id = :family_id AND completed_by_id IS NOT NULL AND is_active"
        )
        params = {"family_id": str(family_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT completed_by_id, COUNT(*) AS count
            FROM (
                SELECT completed_by_id
                FROM planned_chore
                WHERE {condition}
                UNION ALL
                SELECT completed_by_id
                FROM quick_planned_chore
                WHERE {condition}
            ) AS combined
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
        condition = (
            "family_id = :family_id AND completed_by_id IS NOT NULL AND is_active"
        )
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
        condition = (
            "family_id = :family_id AND completed_by_id IS NOT NULL AND is_active"
        )
        params = {"family_id": str(family_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT day, COUNT(*) AS count
            FROM (
                SELECT due_date AS day
                FROM planned_chore
                WHERE {condition}
                UNION ALL
                SELECT due_date AS day
                FROM quick_planned_chore
                WHERE {condition}
            ) AS combined
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
        condition = "completed_by_id = :completed_by_id AND is_active"
        params = {"completed_by_id": str(completed_by_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT day, COUNT(*) AS count
            FROM (
                SELECT due_date AS day
                FROM planned_chore
                WHERE {condition}
                UNION ALL
                SELECT due_date AS day
                FROM quick_planned_chore
                WHERE {condition}
            ) AS combined
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

        condition = "completed_by_id = ANY(:user_ids) AND is_active"
        params = {"user_ids": list(map(str, users_ids))}
        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT completed_by_id, COUNT(*) AS completion_count
            FROM (
                SELECT completed_by_id
                FROM planned_chore
                WHERE {condition}
                UNION ALL
                SELECT completed_by_id
                FROM quick_planned_chore
                WHERE {condition}
            ) AS combined
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
        condition = (
            "family_id = :family_id AND completed_by_id IS NOT NULL AND is_active"
        )
        params = {"family_id": str(family_id)}

        condition, params = self._add_date_interval(condition, params, interval)

        query = text(f"""
            SELECT COUNT(*)
            FROM (
                SELECT 1
                FROM planned_chore
                WHERE {condition}
                UNION ALL
                SELECT 1
                FROM quick_planned_chore
                WHERE {condition}
            ) AS combined
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
                SELECT day
                FROM (
                    SELECT due_date AS day
                    FROM planned_chore
                    WHERE family_id = :family_id
                      AND completed_by_id IS NOT NULL
                      AND is_active
                    UNION ALL
                    SELECT due_date AS day
                    FROM quick_planned_chore
                    WHERE family_id = :family_id
                      AND completed_by_id IS NOT NULL
                      AND is_active
                ) AS combined
                GROUP BY day
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

    async def get_user_current_streak(
        self,
        user_id: UUID,
    ) -> int:
        query = text("""
            WITH active_days AS (
                SELECT day
                FROM (
                    SELECT due_date AS day
                    FROM planned_chore
                    WHERE completed_by_id = :user_id
                      AND is_active
                    UNION ALL
                    SELECT due_date AS day
                    FROM quick_planned_chore
                    WHERE completed_by_id = :user_id
                      AND is_active
                ) AS combined
                GROUP BY day
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
                "user_id": user_id,
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
    return StatsPostgresRepository(async_session)
