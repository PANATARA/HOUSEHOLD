from typing import Generic, Type, TypeVar
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import BaseIdTimeStampModel, BaseUserModel

T = TypeVar("T", bound=BaseIdTimeStampModel)
T_U = TypeVar("T_U", bound=BaseUserModel)


class BaseDal(Generic[T]):
    model: Type[T]

    def __init__(self, db_session: AsyncSession):
        if not hasattr(self, "model"):
            raise AttributeError("Class must define a model attribute.")
        self.db_session = db_session


class BaseDals(BaseDal[T]):
    """Implementation of basic CRU operations"""

    async def get_by_id(self, object_id: UUID) -> T | None:
        query = select(self.model).where(self.model.id == object_id)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, object: T) -> T:
        self.db_session.add(object)
        await self.db_session.flush()
        await self.db_session.refresh(object)
        return object

    async def update(self, object_id: UUID, fields: dict) -> T | None:
        obj = await self.get_by_id(object_id)

        if obj is None:
            return None

        for field, value in fields.items():
            setattr(obj, field, value)

        self.db_session.add(obj)
        await self.db_session.flush()
        return obj


class DeleteDALMixin:
    """Soft delete an object by setting `is_active` to `False`.

    Args:
        object_id (UUID): The ID of the object to soft delete.

    Returns:
        bool: True if the object was found and updated, False if not found.

    Requirements for the subclass:
        - Must define a `Meta` class with the following attributes:
            - `model` (the SQLAlchemy model where the search is performed)
        - Must have a `db_session` attribute to execute queries.
    """

    async def soft_delete(self, object_id: UUID) -> bool:
        if not hasattr(self.model, "is_active"):
            raise AttributeError("Model must define 'is_active' field.")

        query = (
            update(self.model)
            .where(self.model.id == object_id)
            .values(is_active=False)
            .execution_options(synchronize_session="fetch")
        )
        result = await self.db_session.execute(query)

        return result.rowcount > 0

    async def hard_delete(self, object_id: UUID) -> None:
        query = delete(self.model).where(self.model.id == object_id)
        await self.db_session.execute(query)


class GetOrRaiseMixin(BaseDal[T]):
    """
    Mixin for retrieving a database object or raising an exception if the object is not found.

    This mixin provides the `get_or_raise` method, which performs an SQL query
    to retrieve an object by a specified field (default: 'id'). If the object
    is not found, it raises the exception defined in `Meta.not_found_exception`.

    Requirements for the subclass:
    - Must define a `Meta` class with the following attributes:
      - `model` (the SQLAlchemy model where the search is performed)
      - `not_found_exception` (the exception to raise when the object is not found)
    - Must have a `db_session` attribute to execute queries.

    Example usage:

    ```python
    class AsyncUserDAL(BaseDals, GetOrRaiseMixin):

        model = User
        not_found_exception = UserNotFound

    user_dal = AsyncUserDAL(db_session)

    # Retrieve a user by ID or raise an exception
    user = await user_dal.get_or_raise(user_id)

    # Retrieve a user by email
    user = await user_dal.get_or_raise("admin@example.com", field_name="email")
    ```
    """

    not_found_exception: Type[Exception]

    async def get_or_raise(self, object_id: UUID) -> T:
        if not hasattr(self, "not_found_exception"):
            raise AttributeError("Class must define 'not_found_exception' attribute.")

        query = select(self.model).where(self.model.id == object_id)
        result = await self.db_session.execute(query)
        object = result.scalar_one_or_none()

        if object is None:
            raise self.not_found_exception()

        return object


class BaseUserPkDals(Generic[T_U]):
    """Implementation of basic CRUD operation"""

    model: Type[T_U]

    def __init__(self, db_session: AsyncSession, *args, **kwargs):
        self.db_session = db_session
        super().__init__(*args, **kwargs)

    async def get_by_user_id(self, user_id: UUID) -> T_U | None:
        query = select(self.model).where(self.model.user_id == user_id)
        result = await self.db_session.execute(query)
        obj = result.scalar_one_or_none()
        return obj

    async def create(self, fields: dict) -> T_U:
        obj = self.model(**fields)
        self.db_session.add(obj)
        await self.db_session.flush()
        await self.db_session.refresh(obj)
        return obj

    async def update_by_user_id(self, user_id: UUID, fields: dict) -> None:
        query = update(self.model).where(self.model.user_id == user_id).values(**fields)
        await self.db_session.execute(query)
        await self.db_session.flush()
        return None
