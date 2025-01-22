import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRouter

from api.users.handlers import user_router
from api.login_handler import login_router
from config.swagger import swagger_ui_settings


# create instance of the app
app = FastAPI(
    title="Chores-Tracking",
    swagger_ui_parameters=swagger_ui_settings,
)

# create the instance for the routes
main_api_router = APIRouter()

# set routes to the app instance
main_api_router.include_router(user_router, prefix="/users", tags=["user"])
main_api_router.include_router(login_router, prefix="/login", tags=["user"])
app.include_router(main_api_router)

if __name__ == "__main__":
    # run app on the host and port
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)