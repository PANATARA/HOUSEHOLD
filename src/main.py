from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# import routers
from api import (
    chores_completions_router,
    chores_confirmations_router,
    chores_router,
    families_invitations_router,
    families_router,
    login_router,
    product_router,
    user_router,
    wallet_router,
)
from config.swagger import swagger_ui_settings
from core.constants import PostgreSQLEnum
from db.session import engine


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
    print("🚀 Startup: Checking ENUMs in DB...")
    await create_enum_if_not_exists(engine)
    yield
    print("🛑 Shutdown: Closing resources...")


# create instance of the app
app = FastAPI(
    title="HOUSEHOLD", swagger_ui_parameters=swagger_ui_settings, lifespan=lifespan
)

# create the instance for the routes
main_api_router = APIRouter(prefix="/api")

# # set routes to the app instance
main_api_router.include_router(user_router, prefix="/users", tags=["Users"])
main_api_router.include_router(login_router, prefix="/login", tags=["Auth"])

main_api_router.include_router(families_router, prefix="/families", tags=["Family"])
main_api_router.include_router(
    families_invitations_router,
    prefix="/families/invitations",
    tags=["Family invitations"],
)

main_api_router.include_router(
    chores_completions_router,
    prefix="/families/chores/completions",
    tags=["Chores completions"],
)
main_api_router.include_router(
    chores_confirmations_router,
    prefix="/families/chores/confirmations",
    tags=["Chores confiramtions"],
)
main_api_router.include_router(chores_router, prefix="/families/chores", tags=["Chore"])

main_api_router.include_router(wallet_router, prefix="/users/wallets", tags=["Wallet"])

main_api_router.include_router(
    product_router, prefix="/families/products", tags=["Products"]
)

app.include_router(main_api_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
