import pytest
from sqlalchemy import select

from chores.models import Chore
from chores_completions.models import ChoreCompletion
from chores_completions.services import (
    ApproveChoreCompletion,
    CancellChoreCompletion,
    CreateChoreCompletion,
)
from core.enums import StatusConfirmENUM
from core.exceptions.chores import ChoreNotFoundError
from core.exceptions.chores_completion import ChoreCompletionCanNotBeChanged
from families.models import Family
from unittest.mock import AsyncMock, patch

from users.models import User


async def get_random_chore(family: Family, db_session) -> Chore:
    query = select(Chore).where(family.id == family.id)
    query_result = await db_session.execute(query)
    chore = query_result.fetchone()
    if chore is not None:
        return chore[0]
    raise ChoreNotFoundError


async def get_chore_completion(
    user: User, family: Family, db_session
) -> ChoreCompletion:
    chore = await get_random_chore(family, db_session)

    chore_completion = await CreateChoreCompletion(
        user=user, chore=chore, message="message", db_session=db_session
    ).run_process()
    return chore_completion


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "chore_is_active, should_raise_exception",
    [
        (True, False),
        (False, True),
    ],
)
async def test_create_approved_chore_completion(
    chore_is_active, should_raise_exception, admin_family, async_session_test
):
    user, family = admin_family
    chore = await get_random_chore(family, async_session_test)
    chore.is_active = chore_is_active
    if should_raise_exception:
        with pytest.raises(ChoreNotFoundError):
            await CreateChoreCompletion(
                user=user, chore=chore, message="message", db_session=async_session_test
            ).run_process()
    else:
        with patch(
            "chores_completions.services.ApproveChoreCompletion.run_process",
            new_callable=AsyncMock,
        ) as mock_approve:
            chore_completion = await CreateChoreCompletion(
                user=user, chore=chore, message="message", db_session=async_session_test
            ).run_process()

            assert chore_completion
            assert chore_completion.chore_id == chore.id
            mock_approve.assert_called_once()


@pytest.mark.asyncio
async def test_create_awaited_chore_completion(member_family, async_session_test):
    with patch(
        "chores_completions.services.CreateChoreCompletion._create_chores_confirmations",
        new_callable=AsyncMock,
    ) as mock_approve:
        user, family = member_family
        chore = await get_random_chore(family, async_session_test)

        chore_completion = await CreateChoreCompletion(
            user=user, chore=chore, message="message", db_session=async_session_test
        ).run_process()

        assert chore_completion
        mock_approve.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "initial_status, expected_status, should_raise_exception",
    [
        (StatusConfirmENUM.awaits, StatusConfirmENUM.approved, False),
        (StatusConfirmENUM.approved, None, True),
        (StatusConfirmENUM.canceled, None, True),
    ],
)
async def test_approve_chore_completion(
    initial_status,
    expected_status,
    should_raise_exception,
    member_family,
    async_session_test,
):
    user, family = member_family
    chore_completion = await get_chore_completion(user, family, async_session_test)
    chore_completion.status = initial_status

    if should_raise_exception:
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            await ApproveChoreCompletion(
                chore_completion, db_session=async_session_test
            ).run_process()
    else:
        with patch(
            "chores_completions.services.CoinsRewardService.run_process",
            new_callable=AsyncMock,
        ) as mock_approve:
            await ApproveChoreCompletion(
                chore_completion, db_session=async_session_test
            ).run_process()
            await async_session_test.refresh(chore_completion)
            assert chore_completion.status == expected_status
            mock_approve.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "initial_status, expected_status, should_raise_exception",
    [
        (StatusConfirmENUM.awaits, StatusConfirmENUM.canceled, False),
        (StatusConfirmENUM.approved, None, True),
        (StatusConfirmENUM.canceled, None, True),
    ],
)
async def test_cencell_chore_completion(
    initial_status,
    expected_status,
    should_raise_exception,
    member_family,
    async_session_test,
):
    user, family = member_family
    chore_completion = await get_chore_completion(user, family, async_session_test)
    chore_completion.status = initial_status

    if should_raise_exception:
        with pytest.raises(ChoreCompletionCanNotBeChanged):
            await CancellChoreCompletion(
                chore_completion, db_session=async_session_test
            ).run_process()
    else:
        await CancellChoreCompletion(
            chore_completion, db_session=async_session_test
        ).run_process()
        await async_session_test.refresh(chore_completion)
        assert chore_completion.status == expected_status
