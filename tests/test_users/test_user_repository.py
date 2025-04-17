import uuid
import pytest

from core.exceptions.users import UserAlreadyExistsError, UserNotFoundError
from users.repository import AsyncUserDAL


@pytest.mark.asyncio
async def test_user_already_exists_error(user_factory):
    await user_factory.create_user(username="taken_username")

    with pytest.raises(UserAlreadyExistsError):
        await user_factory.create_user(username="taken_username")


@pytest.mark.asyncio
async def test_user_update_success(async_session_test, user_factory):
    user = await user_factory.create_user(username="username")

    fields = {
        "username": "new_username",
        "name": "new_name",
        "surname": "new_surname",
    }

    user_repository = AsyncUserDAL(async_session_test)

    await user_repository.update(user.id, fields)

    updated_user = await user_repository.get_by_id(user.id)

    assert updated_user.username == fields["username"]
    assert updated_user.name == fields["name"]
    assert updated_user.surname == fields["surname"]


@pytest.mark.asyncio
async def test_user_get_or_rise(async_session_test, user_factory):
    user = await user_factory.create_user(username="username")

    user_repository = AsyncUserDAL(async_session_test)

    user_received = await user_repository.get_or_raise(user.id)
    assert user_received.id == user.id

    with pytest.raises(UserNotFoundError):
        non_existent_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        await user_repository.get_or_raise(non_existent_uuid)
