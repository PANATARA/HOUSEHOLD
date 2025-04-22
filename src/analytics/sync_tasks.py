import logging

from sqlalchemy import text

from analytics.click_house_connection import get_click_house_client
from analytics.repository import ChoreAnalyticRepository
from core.enums import StatusConfirmENUM
from database_connection import get_db

logger = logging.getLogger(__name__)

async def sync_statistics():
    db_gen = get_db()  # get_db() возвращает async generator
    async_session = await db_gen.__anext__()
    async with async_session.begin():
        query_result = await async_session.execute(
            text(
                """
                    SELECT 
                        chore_completion.id,
                        chores.family_id,
                        chore_completion.chore_id,
                        chore_completion.completed_by_id as user_id,
                        chore_completion.created_at as completion_date
                    FROM chore_completion
                    JOIN chores ON chore_completion.chore_id = chores.id
                    WHERE  chore_completion.synced_to_ch = false AND status = :enum_value
                """
            ),
            {"enum_value": StatusConfirmENUM.approved.value},
        )
        raw_data = query_result.fetchall()

        if raw_data:
            click_house_client = await get_click_house_client()
            car = ChoreAnalyticRepository(click_house_client)
            prepared_data = []
            for row in raw_data:
                prepared_data.append([row[1], row[2], row[3], row[4].date()])
            await car.bulk_add_new_entry(prepared_data)
            await async_session.execute(
                text(
                    """
                        UPDATE chore_completion
                        SET synced_to_ch = true
                        WHERE id = ANY(:ids)
                    """
                ),
                {"ids": tuple(row[0] for row in raw_data)},
            )
        else:
            pass
