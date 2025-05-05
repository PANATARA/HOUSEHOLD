import pytest

from families.repository import AsyncFamilyDAL, FamilyDataService


@pytest.mark.asyncio
async def test_get_family_with_members(second_family_member, async_session_test):
    user, family = second_family_member
    
    data_service = FamilyDataService(async_session_test)
    data = await data_service.get_family_with_members(family.id)

    family_data = data.family
    members_data = data.members
    
    assert data is not None

    assert family_data.id == family.id
    assert family_data.name == family.name
    assert family_data.icon == family.icon
    
    assert len(members_data) == 2

@pytest.mark.asyncio
async def test_family_dal(created_family, async_session_test):
    user, family = created_family

    family_dal = AsyncFamilyDAL(async_session_test)

    user_is_family_admin = family_dal.user_is_family_admin(user.id, family.id)
    user_is_family_member = family_dal.user_is_family_member(user.id, family.id)

    assert user_is_family_admin
    assert user_is_family_member
