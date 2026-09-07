import logging
from typing import Any

from arq import cron
from arq.connections import RedisSettings

import config
from database_connection import async_session_maker
from planned_chores.services import GeneratePlannedChores

logger = logging.getLogger(__name__)


async def generate_planned_chores_task(ctx: dict[str, Any]) -> int:
    """
    Periodic cron task to generate planned chores for all active schedules.
    """
    logger.info("ARQ: Starting periodic generation of planned chores...")
    async with async_session_maker() as session:
        async with session.begin():
            service = GeneratePlannedChores(db_session=session)
            count = await service.process()
    logger.info("ARQ: Successfully generated %d planned chores.", count)
    return count


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("ARQ Worker started.")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("ARQ Worker stopped.")


class WorkerSettings:
    """
    ARQ Worker configuration.
    Run with: arq src.worker.WorkerSettings (or arq worker.WorkerSettings)
    """

    functions = [generate_planned_chores_task]
    cron_jobs = [
        cron(
            generate_planned_chores_task,
            hour={3},
            minute={0},
            run_at_startup=False,
            name="daily_generate_planned_chores",
        )
    ]
    redis_settings = RedisSettings.from_dsn(config.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
