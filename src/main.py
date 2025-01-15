import re
import uvicorn
import uuid
from fastapi import FastAPI
from fastapi.routing import APIRouter
from sqlalchemy import Boolean, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import field_validator
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from config import database
from config.swagger import swagger_ui_settings

##############################################
# BLOCK FOR COMMON INTERACTION WITH DATABASE #
##############################################


# create async engine for interaction with database
engine = create_async_engine(database.REAL_DATABASE_URL, future=True, echo=True)

# create session for the interaction with database
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


##############################
# BLOCK WITH DATABASE MODELS #
##############################


class Base(DeclarativeBase):
	pass


class User(Base):
    __tablename__ = "User"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(30))
    surname: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


###########################################################
# BLOCK FOR INTERACTION WITH DATABASE IN BUSINESS CONTEXT #
###########################################################


class UserDAL:

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_user(self, name: str, surname: str, email: str) -> User:
        new_user = User(
            name=name,
            surname=surname,
            email=email,
        )
        self.db_session.add(new_user)
        await self.db_session.flush()
        return new_user


#########################
# BLOCK WITH API MODELS #
#########################


LETTER_MATCH_PATTERN = re.compile(r"^[а-яА-Яa-zA-Z\-]+$")

class TunedModel(BaseModel):
    class Config:
        """tells pydantic to convert even non dict obj to json"""

        orm_mode = True


class ShowUser(TunedModel):
    user_id: uuid.UUID
    name: str
    surname: str
    email: EmailStr
    is_active: bool


class UserCreate(BaseModel):
    name: str
    surname: str
    email: EmailStr

    @field_validator("name")
    def validate_name(cls, value):
        if not LETTER_MATCH_PATTERN.match(value):
            raise HTTPException(
                status_code=422, detail="Name should contains only letters"
            )
        return value

    @field_validator("surname")
    def validate_surname(cls, value):
        if not LETTER_MATCH_PATTERN.match(value):
            raise HTTPException(
                status_code=422, detail="Surname should contains only letters"
            )
        return value


#########################
# BLOCK WITH API ROUTES #
#########################

# create instance of the app
app = FastAPI(
    title="My Awesome API",
    description="This API allows you to interact with the system.",
    version="1.0.0",
    swagger_ui_parameters=swagger_ui_settings,
)

user_router = APIRouter()


async def _create_new_user(body: UserCreate) -> ShowUser:
    async with async_session() as session:
        async with session.begin():
            user_dal = UserDAL(session)
            user = await user_dal.create_user(
                name=body.name,
                surname=body.surname,
                email=body.email,
            )
            return ShowUser(
                user_id=user.user_id,
                name=user.name,
                surname=user.surname,
                email=user.email,
                is_active=user.is_active,
            )


@user_router.post("/", response_model=ShowUser)
async def create_user(body: UserCreate) -> ShowUser:
    return await _create_new_user(body)

# create the instance for the routes
main_api_router = APIRouter()

# set routes to the app instance
main_api_router.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(main_api_router)

if __name__ == "__main__":
    # run app on the host and port
    uvicorn.run(app, host="0.0.0.0", port=8000)