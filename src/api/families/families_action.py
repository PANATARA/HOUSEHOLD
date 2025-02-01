from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter, parse_obj_as
from sqlalchemy.ext.asyncio import AsyncSession

from db.dals.families import AsyncFamilyDAL
from schemas.families import FamilyFullShow, FamilyShow
from schemas.users import ShowUser, UserCreate
from logging import getLogger

from db.models.user import User
from services.families.data import FamilyDataService
from services.families.services import FamilyCreatorService

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


async def _get_family(user: User, async_session: AsyncSession) -> FamilyShow | HTTPException:
    async with async_session.begin():
        data = await FamilyDataService(async_session).get_family_with_users(
            user.family_id
        )
        if data is None:
            raise HTTPException(status_code=404, detail=f"Family not found")

        return data
