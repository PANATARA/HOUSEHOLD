import logging
import sys
from pathlib import Path
from typing import Any

# Ensure both src/ and project root are in sys.path
_current_dir = Path(__file__).resolve().parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))
_parent_dir = _current_dir.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

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
    try:
        async with async_session_maker() as session:
            async with session.begin():
                service = GeneratePlannedChores(db_session=session)
                count = await service.process()
        logger.info("ARQ: Successfully generated %d planned chores.", count)
        return count
    except Exception as e:
        logger.error("ARQ: Error during planned chores generation: %s", e, exc_info=True)
        raise


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("ARQ Worker started.")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("ARQ Worker stopped.")


class WorkerSettings:
    """
    ARQ Worker configuration.
    Run with: arq worker.WorkerSettings (or arq src.worker.WorkerSettings)
    """

    functions = [generate_planned_chores_task]
    cron_jobs = [
        cron(
            generate_planned_chores_task,
            hour={3},
            minute={0},
            run_at_startup=True,
            name="daily_generate_planned_chores",
        )
    ]
    redis_settings = RedisSettings.from_dsn(config.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
