from contextlib import asynccontextmanager
from sqlalchemy import text
import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncEngine

from config.swagger import swagger_ui_settings
from db.session import engine
from core.constants import PostgreSQLEnum

#import routers
from api.users.handlers import user_router
from api.auth.handler import login_router
from api.families.handlers import families_router
from api.chores.handlers import chores_router
from api.chores_logs.handlers import chores_logs_router
from api.wallets.handlers import wallet_router
from api.chores_confirmations.handlers import chores_confirmations

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
    title="Chores-Tracking",
    swagger_ui_parameters=swagger_ui_settings,
    lifespan=lifespan
)

# create the instance for the routes
main_api_router = APIRouter(prefix="/api")

# set routes to the app instance
main_api_router.include_router(user_router, prefix="/users", tags=["Users"])
main_api_router.include_router(login_router, prefix="/login", tags=["Auth"])
main_api_router.include_router(families_router, prefix="/family", tags=["Family"])

main_api_router.include_router(chores_router, prefix="/family/chores", tags=["Chore"])
main_api_router.include_router(chores_logs_router, prefix="/family/chores/logs", tags=["Chores Logs"])
main_api_router.include_router(chores_confirmations, prefix="/family/chores/confirmations", tags=["Chores confiramtions"])

main_api_router.include_router(wallet_router, prefix="/users/wallets", tags=["Wallet"])

app.include_router(main_api_router)

if __name__ == "__main__":
    # run app on the host and port
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)