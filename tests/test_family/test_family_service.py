import pytest

from chores.repository import ChoreDataService
from chores.services import get_default_chore_data
from core.exceptions.families import UserIsAlreadyFamilyMember
from families.services import FamilyCreatorService
from wallets.repository import AsyncWalletDAL


@pytest.mark.asyncio
async def test_created_family_has_admin_user(created_family):
    user, family = created_family

    assert family.name == "family_test"
    assert family.family_admin_id == user.id


@pytest.mark.asyncio
async def test_added_user_is_linked_to_family(created_family, async_session_test):
    user, family = created_family

    await async_session_test.refresh(user)

    assert user.family_id == family.id


@pytest.mark.asyncio
async def test_cannot_add_user_already_in_family(created_family, async_session_test):
    user, _ = created_family

    with pytest.raises(UserIsAlreadyFamilyMember):
        service = FamilyCreatorService(
            name="second_family", user=user, db_session=async_session_test
        )
        await service.run_process()


@pytest.mark.asyncio
async def test_family_has_default_chores_on_creation(
    created_family, async_session_test
):
    _, family = created_family

    ChoreRepository = ChoreDataService(async_session_test)
    family_chores = await ChoreRepository.get_family_chores(family.id)

    assert len(family_chores) == len(get_default_chore_data())


@pytest.mark.asyncio
async def test_family_add_user(second_family_member):
    user, family = second_family_member
    assert user.family_id == family.id


@pytest.mark.asyncio
async def test_permissions_are_created_for_added_user(
    second_family_member, async_session_test
):
    user, _ = second_family_member
    await async_session_test.refresh(user, attribute_names=["permissions"])
    assert user.permissions is not None


@pytest.mark.asyncio
async def test_wallet_is_created_for_added_user(
    second_family_member, async_session_test
):
    user, _ = second_family_member

    user_wallet = await AsyncWalletDAL(async_session_test).get_by_user_id(user.id)

    assert user_wallet is not None
