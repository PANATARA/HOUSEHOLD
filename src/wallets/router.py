from logging import getLogger

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions.base_exceptions import ObjectNotFoundError
from core.exceptions.wallets import NotEnoughCoins
from core.get_avatars import update_user_avatars
from core.permissions import FamilyMemberPermission
from core.query_depends import get_pagination_params
from database_connection import get_db
from users.models import User
from users.repository import AsyncUserDAL
from wallets.repository import TransactionDataService, WalletDataService
from wallets.schemas import (
    MoneyTransferSchema,
    UnionTransactionsSchema,
    WalletBalanceSchema,
)
from wallets.services import CoinsTransferService

logger = getLogger(__name__)

router = APIRouter()


@router.get(path="", summary="Get user wallet balance", tags=["Wallet"])
async def get_user_wallet(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> WalletBalanceSchema:
    async with async_session.begin():
        wallet_data = await WalletDataService(async_session).get_user_wallet(
            user_id=current_user.id
        )
        return wallet_data


@router.post(
    path="/transfer",
    summary="Transfer coins to another user",
    tags=["Wallet transfer"],
)
async def money_transfer_wallet(
    body: MoneyTransferSchema,
    current_user: User = Depends(FamilyMemberPermission()),
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
        except ObjectNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except NotEnoughCoins:
            raise HTTPException(status_code=400, detail="You don't have enough coins")

    return JSONResponse(
        status_code=200,
        content={"detail": "The transaction was successful."},
    )


@router.get(
    path="/transactions",
    summary="Get user's wallet transactions",
    tags=["Wallet transactions"],
)
async def get_user_wallet_transaction(
    pagination: tuple[int, int] = Depends(get_pagination_params),
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> UnionTransactionsSchema:

    async with async_session.begin():
        transactions_data = TransactionDataService(async_session)
        offset, limit = pagination

        user_transactions = await transactions_data.get_union_user_transactions(
            user_id=current_user.id,
            offset=offset,
            limit=limit,
        )
        await update_user_avatars(user_transactions)
        return user_transactions
