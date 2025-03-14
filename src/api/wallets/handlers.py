from logging import getLogger

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.permissions import IsAuthenicatedPermission
from core.exceptions.families import UserNotFoundInFamily
from core.exceptions.wallets import NotEnoughCoins
from db.dals.users import AsyncUserDAL
from db.models.user import User
from db.session import get_db
from schemas.wallets import MoneyTransfer, NewWalletTransaction, ShowWalletBalance
from services.wallets.data import TransactionDataService, WalletDataService
from services.wallets.services import CoinsTransferService

logger = getLogger(__name__)

wallet_router = APIRouter()


# Get user's wallet
@wallet_router.get(path="", summary="Get user wallet information")
async def get_user_wallet(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> ShowWalletBalance:
    async with async_session.begin():
        wallet_data = await WalletDataService(async_session).get_user_wallet(
            user_id=current_user.id
        )
        return wallet_data


# Money transfer
@wallet_router.post(path="/transfer", summary="Make a transfer of coins to the user")
async def money_transfer_wallet(
    body: MoneyTransfer,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with async_session.begin():
        try:
            user_dal = AsyncUserDAL(async_session)
            to_user = await user_dal.get_or_raise(body.to_user_id)

            transfer_service = CoinsTransferService(
                from_user=current_user,
                to_user=to_user,
                count=body.count,
                message="Transferred you some coins",
                db_session=async_session,
            )
            await transfer_service.run_process()
        except UserNotFoundInFamily:
            raise HTTPException(
                status_code=404, detail="No Such User Found In The family"
            )
        except NotEnoughCoins:
            raise HTTPException(status_code=400, detail="You don't have enough coins")

    return JSONResponse(
        status_code=200,
        content={"detail": "The transaction was successful."},
    )


# Get transactions user's wallet
@wallet_router.get(path="/transactions", summary="Get transactions user's wallet")
async def get_user_wallet_transaction(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=20),
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[NewWalletTransaction]:
    async with async_session.begin():
        transactions_data = TransactionDataService(async_session)
        offset = (page - 1) * limit

        user_transactions = await transactions_data.get_union_user_transactions(
            user_id=current_user.id,
            offset=offset,
            limit=limit,
        )
        return user_transactions
