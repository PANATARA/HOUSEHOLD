from decimal import Decimal
from unittest.mock import AsyncMock, patch
import pytest
from sqlalchemy import update

from config import TRANSFER_RATE
from core.enums import PeerTransactionENUM
from core.exceptions.families import UserNotFoundInFamily
from core.exceptions.wallets import NotEnoughCoins
from users.repository import AsyncUserDAL
from wallets.models import Wallet
from wallets.repository import AsyncWalletDAL
from wallets.schemas import CreatePeerTransactionSchema
from wallets.services import (
    CoinsTransferService,
    PeerTransactionService,
    WalletCreatorService,
)


async def set_user_balance(user, balance, db_session):
    query = update(Wallet).where(Wallet.user_id == user.id).values(balance=balance)
    await db_session.execute(query)
    await db_session.flush()


@pytest.mark.asyncio
async def test_wallet_creator_service(user_factory, async_session_test):
    user = await user_factory()
    wallet = await WalletCreatorService(user, async_session_test).run_process()
    assert wallet
    assert wallet.balance == 0
    assert wallet.user_id == user.id


@pytest.mark.asyncio
async def test_coin_transfer_service(member_family, async_session_test):
    member, family = member_family
    admin = await AsyncUserDAL(async_session_test).get_by_id(family.family_admin_id)
    with patch(
        "wallets.services.PeerTransactionService.run_process", new_callable=AsyncMock
    ) as mock_approve:
        await CoinsTransferService(
            from_user=member,
            to_user=admin,
            count=Decimal(10),
            message="message",
            db_session=async_session_test,
        ).run_process()
        mock_approve.assert_called_once()


@pytest.mark.asyncio
async def test_coin_transfer_service_exception(member_family, async_session_test):
    member, family = member_family
    admin = await AsyncUserDAL(async_session_test).get_by_id(family.family_admin_id)
    member.family_id = None
    with pytest.raises(UserNotFoundInFamily):
        await CoinsTransferService(
            from_user=member,
            to_user=admin,
            count=Decimal(10),
            message="message",
            db_session=async_session_test,
        ).run_process()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_from_balance, should_raise_exception",
    [
        (Decimal(20), False),
        (Decimal(2), True),
    ],
)
async def test_peer_transaction_service(
    user_from_balance, should_raise_exception, member_family, async_session_test
):
    user_from, family = member_family
    user_to = await AsyncUserDAL(async_session_test).get_by_id(family.family_admin_id)

    await set_user_balance(user_from, user_from_balance, async_session_test)

    data = CreatePeerTransactionSchema(
        coins=10, transaction_type=PeerTransactionENUM.transfer, detail="Transfer coins"
    )

    service = PeerTransactionService(
        from_user=user_from, to_user=user_to, data=data, db_session=async_session_test
    )
    if should_raise_exception:
        with pytest.raises(NotEnoughCoins):
            await service.run_process()
    else:
        transaction_log = await service.run_process()

        assert transaction_log.coins == data.coins
        assert transaction_log.detail == data.detail
        assert transaction_log.from_user_id == user_from.id
        assert transaction_log.to_user_id == user_to.id

        expected_user_from_balance = user_from_balance - data.coins
        expected_user_to_balance = data.coins * TRANSFER_RATE

        actual_user_from_balance = await AsyncWalletDAL(
            async_session_test
        ).get_user_balance(user_from.id)
        assert actual_user_from_balance == expected_user_from_balance

        actual_user_to_balance = await AsyncWalletDAL(
            async_session_test
        ).get_user_balance(user_to.id)
        assert actual_user_to_balance == expected_user_to_balance.quantize(
            Decimal("0.01")
        )
