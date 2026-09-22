import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from auth.router import router as auth_router
from chores.router import router as chores_router
from planned_chores.router import (
    router as planned_chores_router,
    schedules_router,
    update_planned_chore_message,
)
import config
from config import swagger_ui_settings
from core.enums import PostgreSQLEnum
from core.exceptions.base_exceptions import BaseAPIException
from database_connection import engine
from families.router import router as families_router
from products.router import router as product_router
from users.router import router as user_router
from wallets.router import router as wallet_router
from statistics.router import router as stats_router
from meals.router import router as meals_router
from notifications.router import router as notifications_router
from notifications.service import init_firebase

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
        logger.info("Startup: Checking ENUMs in DB...")
        await create_enum_if_not_exists(engine)
        init_firebase()

        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        logger.info("🛑 Shutdown: Closing resources...")


# create instance of the app
app = FastAPI(
    title="HOUSEHOLD",
    swagger_ui_parameters=swagger_ui_settings,
    lifespan=lifespan,
)


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
main_api_router.include_router(planned_chores_router, prefix="/chores")
main_api_router.include_router(schedules_router, prefix="/schedules")
main_api_router.include_router(chores_router, prefix="/chores")
main_api_router.include_router(wallet_router, prefix="/wallets")
main_api_router.include_router(product_router, prefix="/products")
main_api_router.include_router(stats_router, prefix="/stats")
main_api_router.include_router(meals_router, prefix="/meals")
main_api_router.include_router(notifications_router, prefix="/notifications")
main_api_router.add_api_route(
    "/planned-chores/{planned_chore_id}",
    update_planned_chore_message,
    methods=["PATCH"],
    include_in_schema=False,
)

app.include_router(main_api_router)
app.add_api_route(
    "/planned-chores/{planned_chore_id}",
    update_planned_chore_message,
    methods=["PATCH"],
    include_in_schema=False,
)

# Optional PWA frontend serving (enabled via SERVE_FRONTEND=True)
if config.SERVE_FRONTEND:
    import os
    from fastapi import HTTPException
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    static_dir = config.STATIC_DIR
    if os.path.exists(static_dir):
        logger.info("Serving PWA frontend from: %s", static_dir)

        assets_dir = os.path.join(static_dir, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        icons_dir = os.path.join(static_dir, "icons")
        if os.path.exists(icons_dir):
            app.mount("/icons", StaticFiles(directory=icons_dir), name="icons")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa_frontend(full_path: str):
            if full_path in ("docs", "redoc", "openapi.json") or full_path.startswith("api"):
                raise HTTPException(status_code=404, detail="Not Found")
            file_path = os.path.join(static_dir, full_path)
            if full_path and os.path.isfile(file_path):
                return FileResponse(file_path)
            index_path = os.path.join(static_dir, "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path)
            return JSONResponse(status_code=404, content={"detail": "Frontend index.html not found"})
    else:
        logger.warning("SERVE_FRONTEND is True, but static directory '%s' does not exist.", static_dir)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
