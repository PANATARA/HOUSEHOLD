import pytest

from users.repository import AsyncUserDAL, AsyncUserSettingsDAL


@pytest.mark.asyncio
async def test_user_created_with_settings(user_factory, async_session_test):
    user = await user_factory(username="unique_user")

    user_dal = AsyncUserDAL(async_session_test)
    user_from_db = await user_dal.get_user_by_username(user.username)

    assert user_from_db is not None
    assert user_from_db.username == user.username

    user_settings_dal = AsyncUserSettingsDAL(async_session_test)
    user_settings = await user_settings_dal.get_by_user_id(user.id)

    assert user_settings is not None
