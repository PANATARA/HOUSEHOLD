import pytest_asyncio
from families.services import AddUserToFamilyService, FamilyCreatorService
from users.schemas import UserCreateSchema, UserFamilyPermissionModelSchema
from users.services import UserCreatorService


@pytest_asyncio.fixture
async def created_family(async_session_test, user_factory):
    user = await user_factory.create_user()
    service = FamilyCreatorService(
        name="family_test", user=user, db_session=async_session_test
    )
    family = await service.run_process()
    return user, family


@pytest_asyncio.fixture
async def second_family_member(created_family, async_session_test):
    _, family = created_family

    user_data = UserCreateSchema(
        username="username_added",
        name="secondName",
        surname="secondSurname",
        password="StrongPassword123",
    )
    service = UserCreatorService(user_data=user_data, db_session=async_session_test)
    user = await service.run_process()

    user_permissions = UserFamilyPermissionModelSchema(
        should_confirm_chore_completion=True
    )
    await AddUserToFamilyService(
        family, user, user_permissions, async_session_test
    ).run_process()

    await async_session_test.refresh(user)
    return user, family
