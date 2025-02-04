from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.dals.families import AsyncFamilyDAL
from db.dals.users import AsyncUserDAL
from db.dals.wallets import AsyncWalletDAL
from schemas.families import FamilyShow
from schemas.users import UserCreate
from db.models.user import User
from schemas.wallets import ShowWallet
from services.families.data import FamilyDataService
from services.families.services import AddUserToFamilyService, FamilyCreatorService


from logging import getLogger

from services.wallets.data import WalletDataService
logger = getLogger(__name__)

user_router = APIRouter()

# Get user wallet
async def _get_user_wallet(user: User, async_session: AsyncSession) -> ShowWallet:
    async with async_session.begin():
        wallet_data = await WalletDataService(async_session).get_user_wallet(user_id=user.id)
        return wallet_data