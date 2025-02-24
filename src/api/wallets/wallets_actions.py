from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse

from core.exceptions import NoSuchUserFoundInThefamily, NotEnoughCoins
from db.dals.users import AsyncUserDAL
from db.models.user import User
from schemas.wallets import MoneyTransfer, ShowWalletBalance, WalletTransactionLog
from services.wallets.data import TransactionDataService, WalletDataService
from services.wallets.services import CoinsTransferService

from logging import getLogger


logger = getLogger(__name__)


# Get user wallet
async def _get_user_wallet(user: User, async_session: AsyncSession) -> ShowWalletBalance:
    async with async_session.begin():
        wallet_data = await WalletDataService(async_session).get_user_wallet(
            user_id=user.id
        )
        return wallet_data

async def _get_user_transactions(user: User, async_session: AsyncSession, page=1, limit=10) -> list[WalletTransactionLog]:
    async with async_session.begin():
        transactions_data = TransactionDataService(async_session)
        offset = (page - 1) * limit
        
        return await transactions_data.get_user_transactions(user.id, offset, limit)


async def _money_transfer_wallet(
    body: MoneyTransfer, user: User, async_session: AsyncSession
):
    async with async_session.begin():
        try:
            user_dal = AsyncUserDAL(async_session)
            to_user = await user_dal.get_by_id(body.to_user_id)

            transactioin_log = await CoinsTransferService(
                from_user=user,
                to_user=to_user,
                count=body.count,
                message="Transferred you some coins",
                db_session=async_session,
            )()
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
