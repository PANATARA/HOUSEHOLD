from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_current_user_from_token
from api.wallets.wallets_actions import (
    _get_user_transactions,
    _get_user_wallet,
    _money_transfer_wallet,
)
from db.models.user import User
from db.session import get_db
from logging import getLogger

from schemas.wallets import MoneyTransfer, ShowWalletBalance, WalletTransactionLog

logger = getLogger(__name__)

wallet_router = APIRouter()


# Get user wallet
@wallet_router.get(
    path="", response_model=ShowWalletBalance, summary="Get user wallet information"
)
async def get_user_wallet(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> ShowWalletBalance:

    return await _get_user_wallet(current_user, db)


# Money transfer
@wallet_router.post(path="/transfer", summary="Make a transfer of coins to the user")
async def money_transfer_wallet(
    body: MoneyTransfer,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> None:

    return await _money_transfer_wallet(body, current_user, db)


# Get transactions on user wallet
@wallet_router.get(path="/transactions", summary="Get transactions on user wallet")
async def get_user_wallet(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=20),
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> list[WalletTransactionLog]:

    return await _get_user_transactions(
        user=current_user, async_session=db, page=page, limit=limit
    )
