import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from users.repository import AsyncUserDAL, AsyncUserSettingsDAL
from users.services import UserCreatorService


@pytest.mark.asyncio
class TestUserServiceCreate:
    async def test_get_family_chores(
        self, async_session_test: AsyncSession, user_create_data
    ):
        async with async_session_test.begin():
            service = UserCreatorService(
                username=user_create_data.username,
                name=user_create_data.name,
                surname=user_create_data.surname,
                password=user_create_data.password,
                db_session=async_session_test,
            )
            user = await service.run_process()

            user_dal = AsyncUserDAL(async_session_test)
            result_user = await user_dal.get_user_by_username(
                username=user_create_data.username
            )

            assert user.id == result_user.id
            assert user.username == result_user.username
            assert user.name == result_user.name
            assert user.surname == result_user.surname

            user_settings_dal = AsyncUserSettingsDAL(async_session_test)

            user_settings = await user_settings_dal.get_by_user_id(result_user.id)

            assert user_settings is not None