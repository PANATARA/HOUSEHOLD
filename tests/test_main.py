import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from users.services import UserCreatorService

@pytest.mark.asyncio
async def test_get_family_chores(async_session_test: AsyncSession):
# Данные для создания пользователя
    username = "test_username_2"
    name = "test_name"
    surname = "test_surname"
    password = "test_password"  # Убедитесь, что пароль хэшируется, если нужно

    async with async_session_test.begin():
        # Создание сервиса
        service = UserCreatorService(
            username=username,
            name=name,
            surname=surname,
            password=password,
            db_session=async_session_test,  # Передаем сессию для работы с БД
        )

        # Запуск процесса создания пользователя
        user = await service.run_process()

        # Проверка, что пользователь был создан и вернул данные
        assert user.username == username
        assert user.name == name
        assert user.surname == surname
        

        
        