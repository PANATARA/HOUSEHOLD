from typing import Generic, Type, TypeVar
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from core.exceptions.base_exceptions import ObjectNotFoundError
from core.models import BaseIdTimeStampModel, BaseUserModel

T = TypeVar("T", bound=BaseIdTimeStampModel)
T_EXE = TypeVar("T_EXE", bound=ObjectNotFoundError)
T_U = TypeVar("T_U", bound=BaseUserModel)


class BaseDal(Generic[T]):
    model: Type[T]
    not_found_exception: Type[T_EXE]

    def __init__(self, db_session: AsyncSession):
        if not hasattr(self, "model"):
            raise AttributeError("Class must define a model attribute.")
        self.db_session = db_session


class BaseDals(BaseDal[T]):
    """Implementation of basic CRU operations"""

    async def get_by_id(self, object_id: UUID) -> T:
        query = select(self.model).where(self.model.id == object_id)
        result = await self.db_session.execute(query)
        try:
            return result.scalar_one()
        except NoResultFound:
            raise self.not_found_exception

    async def create(self, object: T) -> T:
        self.db_session.add(object)
        await self.db_session.flush()
        await self.db_session.refresh(object)
        return object

    async def update(self, object: T) -> T:
        self.db_session.add(object)
        await self.db_session.flush()
        await self.db_session.refresh(object)
        return object


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
