import pytest

from chores.repository import ChoreDataService
from chores.services import get_default_chore_data
from core.exceptions.families import UserCannotLeaveFamily, UserIsAlreadyFamilyMember
from families.services import FamilyCreatorService, LogoutUserFromFamilyService
from wallets.repository import AsyncWalletDAL


@pytest.mark.asyncio
async def test_family_has_admin(admin_family):
    user, family = admin_family
    assert family.name == "family_test"
    assert family.family_admin_id == user.id


@pytest.mark.asyncio
async def test_added_user_is_linked_to_family(admin_family, async_session_test):
    user, family = admin_family
    await async_session_test.refresh(user)
    assert user.family_id == family.id


@pytest.mark.asyncio
async def test_cannot_add_user_already_in_family(admin_family, async_session_test):
    user, _ = admin_family

    with pytest.raises(UserIsAlreadyFamilyMember):
        service = FamilyCreatorService(
            name="Family", user=user, db_session=async_session_test
        )
        await service.run_process()


@pytest.mark.asyncio
async def test_family_has_default_chores_on_creation(admin_family, async_session_test):
    _, family = admin_family

    ChoreRepository = ChoreDataService(async_session_test)
    family_chores = await ChoreRepository.get_family_chores(family.id)
    assert len(family_chores) == len(get_default_chore_data())


@pytest.mark.asyncio
async def test_family_add_user(member_family):
    user, family = member_family
    assert user.family_id == family.id


@pytest.mark.asyncio
async def test_permissions_are_created_for_added_user(
    member_family, async_session_test
):
    user, _ = member_family
    await async_session_test.refresh(user, attribute_names=["permissions"])
    assert user.permissions is not None


@pytest.mark.asyncio
async def test_wallet_is_created_for_added_user(member_family, async_session_test):
    user, _ = member_family
    user_wallet = await AsyncWalletDAL(async_session_test).get_by_user_id(user.id)
    assert user_wallet is not None


@pytest.mark.asyncio
async def test_admin_cannot_logout_from_family(admin_family, async_session_test):
    user, _ = admin_family
    with pytest.raises(UserCannotLeaveFamily):
        service = LogoutUserFromFamilyService(user, async_session_test)
        await service.run_process()


@pytest.mark.asyncio
async def test_user_is_logout_from_family(member_family, async_session_test):
    user, _ = member_family
    service = LogoutUserFromFamilyService(user, async_session_test)
    await service.run_process()
    await async_session_test.refresh(user)
    assert user.family_id is None
