from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NoSuchUserFoundInThefamily, NotEnoughCoins
from core.security import get_current_user_from_token
from db.dals.users import AsyncUserDAL
from db.models.user import User
from db.session import get_db
from schemas.wallets import MoneyTransfer, ShowWalletBalance, WalletTransactionLog
from services.wallets.data import TransactionDataService, WalletDataService
from services.wallets.services import CoinsTransferService


from logging import getLogger
logger = getLogger(__name__)

wallet_router = APIRouter()


# Get user wallet
@wallet_router.get(
    path="", response_model=ShowWalletBalance, summary="Get user wallet information"
)
async def get_user_wallet(
    current_user: User = Depends(get_current_user_from_token),
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
    current_user: User = Depends(get_current_user_from_token),
    async_session: AsyncSession = Depends(get_db),
) -> JSONResponse:

    async with async_session.begin():
        try:
            user_dal = AsyncUserDAL(async_session)
            to_user = await user_dal.get_by_id(body.to_user_id)

            transfer_service = CoinsTransferService(
                from_user=current_user,
                to_user=to_user,
                count=body.count,
                message="Transferred you some coins",
                db_session=async_session,
            )
            transaction_log = await transfer_service()
        except NoSuchUserFoundInThefamily:
            return JSONResponse(
                status_code=400,
                content={"detail": "No Such User Found In The family"},
            )
        except NotEnoughCoins:
            return JSONResponse(
                status_code=400,
                content={"detail": "You don't have enough coins"},
            )
        
        return JSONResponse(
                status_code=200,
                content={"detail": "The transaction was successful."},
            )


# Get transactions on user wallet
@wallet_router.get(path="/transactions", summary="Get transactions on user wallet")
async def get_user_wallet(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=20),
    current_user: User = Depends(get_current_user_from_token),
    async_session: AsyncSession = Depends(get_db)
) -> list[WalletTransactionLog]:

    async with async_session.begin():
        transactions_data = TransactionDataService(async_session)
        offset = (page - 1) * limit
        
        user_transactions = await transactions_data.get_user_transactions(
            user_id=current_user.id,
            offset=offset,
            limit=limit,
        )
        return user_transactions
