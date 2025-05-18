import logging
from contextlib import asynccontextmanager

from fastapi.responses import JSONResponse
import uvicorn
from fastapi import FastAPI, Request
from fastapi.routing import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from auth.router import router as auth_router
from chores.router import router as chores_router
from chores_completions.router import router as chores_completions_router
from chores_confirmations.router import router as chores_confirmations_router
from config import swagger_ui_settings
from core.enums import PostgreSQLEnum
from core.exceptions.base_exceptions import BaseAPIException
from core.redis_connection import redis_client
from database_connection import engine
from families.router import router as families_router
from products.router import router as product_router
from users.router import router as user_router
from wallets.router import router as wallet_router

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


@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    return JSONResponse(status_code=400, content={"serviceError": str(exc)})


# create the instance for the routes
main_api_router = APIRouter(prefix="/api")

# # set routes to the app instance
main_api_router.include_router(user_router, prefix="/users")
main_api_router.include_router(auth_router, prefix="/login")
main_api_router.include_router(families_router, prefix="/families")
main_api_router.include_router(chores_completions_router, prefix="/chores-completions")
main_api_router.include_router(
    chores_confirmations_router, prefix="/chores-confirmations"
)
main_api_router.include_router(chores_router, prefix="/chores")
main_api_router.include_router(wallet_router, prefix="/wallets")


main_api_router.include_router(product_router, prefix="/products")

app.include_router(main_api_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
