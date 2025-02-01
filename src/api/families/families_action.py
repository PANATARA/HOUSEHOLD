from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.dals.families import AsyncFamilyDAL
from schemas.families import FamilyFullShow, FamilyShow
from schemas.users import ShowUser, UserCreate
from logging import getLogger

from db.models.user import User
from services.families import FamilyCreatorService

logger = getLogger(__name__)

user_router = APIRouter()


async def _create_family(
    user: User, body: UserCreate, async_session: AsyncSession
) -> FamilyShow:

    try:
        async with async_session.begin():
            family = await FamilyCreatorService(
                name=body.name, user=user, db_session=async_session
            )()
            return FamilyShow(name=family.name)
    except ValueError as e:
        return JSONResponse(
            status_code=400, content={"detail": "The user is already a family member"}
        )
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})


async def _get_family(user: User, async_session: AsyncSession) -> FamilyShow:
    async with async_session.begin():
        family_dal = AsyncFamilyDAL(async_session)
        family = await family_dal.get_family_with_related_objects(user.family_id)

        members = [ShowUser.model_validate(u) for u in family.users]

        return FamilyFullShow(name=family.name, members=members)
