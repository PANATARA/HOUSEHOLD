from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# import routers
from analytics.click_house_connection import get_click_house_client
from analytics.repository import ChoreAnalyticRepository
from users.router import user_router
from families.router import families_router
from chores.router import chores_router
from chores_completions.router import chores_completions_router
from chores_confirmations.router import chores_confirmations_router
from wallets.router import wallet_router
from products.router import product_router
from auth.router import login_router

from config import swagger_ui_settings
from core.constants import PostgreSQLEnum
from core.redis_connection import redis_client
from core.session import engine

logger = logging.getLogger(__name__)

async def create_enum_if_not_exists(engine: AsyncEngine):
    async with engine.begin() as conn:
        for subclass in PostgreSQLEnum.get_subclasses():
            enum_name = subclass.get_enum_name()

            result = await conn.execute(
                text("SELECT 1 FROM pg_type WHERE typname = :enum_name"),
                {"enum_name": enum_name},
            )

            if result.scalar() is None:
                values_str = ", ".join(f"'{item.value}'" for item in subclass)
                await conn.execute(
                    text(f"CREATE TYPE {enum_name} AS ENUM ({values_str})")
                )
                print(f"✅ Created ENUM: {enum_name} ({values_str})")
            else:
                print(f"⚠️ ENUM '{enum_name}' already exist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Checking ENUMs in DB
        logger.info("🚀 Startup: Checking ENUMs in DB...")
        await create_enum_if_not_exists(engine)
        
        # Redis connections
        logger.info("🚀 Startup: Redis connections...")
        await redis_client.connect()
        
        # ClickHouse connections and creating the table
        logger.info("🚀 Startup: ClickHouse connections...")
        click_house_repo = ChoreAnalyticRepository(await get_click_house_client())
        await click_house_repo.create_chore_stats_table()
        
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        logger.info("🛑 Shutdown: Closing resources...")
        await redis_client.close()


# create instance of the app
app = FastAPI(
    title="HOUSEHOLD",
    swagger_ui_parameters=swagger_ui_settings,
    lifespan=lifespan,
)

# create the instance for the routes
main_api_router = APIRouter(prefix="/api")

# # set routes to the app instance
main_api_router.include_router(user_router, prefix="/users", tags=["Users"])
main_api_router.include_router(login_router, prefix="/login", tags=["Auth"])
main_api_router.include_router(families_router, prefix="/families", tags=["Family"])
main_api_router.include_router(chores_completions_router, prefix="/chores-completions", tags=["Chores completions"])
main_api_router.include_router(chores_confirmations_router, prefix="/chores-confirmations", tags=["Chores confiramtions"],)
main_api_router.include_router(chores_router, prefix="/chores", tags=["Chore"])
main_api_router.include_router(wallet_router, prefix="/wallets", tags=["Wallet"])


main_api_router.include_router(product_router, prefix="/products", tags=["Products"])

app.include_router(main_api_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
