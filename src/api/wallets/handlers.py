from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.wallets.wallets_actions import _get_user_wallet, _money_transfer_wallet
from db.models.user import User
from db.session import get_db
from logging import getLogger

from schemas.wallets import MoneyTransfer, ShowWallet

logger = getLogger(__name__)

wallet_router = APIRouter()

# Get user family
@wallet_router.get(path="", response_model=ShowWallet)
async def get_user_wallet(
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> ShowWallet:
    
    return await _get_user_wallet(current_user, db)

# Money transfer
@wallet_router.post(path="", summary="NOT IMPLEMENTED")
async def money_transfer_wallet(
    body: MoneyTransfer,
    current_user: User = Depends(get_current_user_from_token), 
    db: AsyncSession = Depends(get_db)
) -> None:
    
    return await _money_transfer_wallet(body, current_user, db)