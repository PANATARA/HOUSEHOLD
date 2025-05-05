import pytest

from core.exceptions.families import UserCannotLeaveFamily
from families.services import LogoutUserFromFamilyService

@pytest.mark.asyncio
async def test_admin_cannot_logout_from_family(created_family, async_session_test):
    user, family = created_family
    with pytest.raises(UserCannotLeaveFamily):
        service = LogoutUserFromFamilyService(user, async_session_test)
        await service.run_process()

@pytest.mark.asyncio
async def test_user_is_logout_from_family(second_family_member, async_session_test):
    user, family = second_family_member
    service = LogoutUserFromFamilyService(user, async_session_test)
    await service.run_process()
    await async_session_test.refresh(user)

    assert user.family_id is None
