from dataclasses import dataclass
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from db.models.declarative_base import Base



@dataclass
class BaseDals:
    """Implementation of basic CRUD operation"""
    db_session: AsyncSession

    class Meta:
        model = None

    async def get_by_id(self, object_id: UUID) -> Base | None:
        query = select(self.Meta.model).where(self.Meta.model.id == object_id)
        result = await self.db_session.execute(query)
        object = result.scalar_one_or_none()
        return object

    async def create(self, fields: dict) -> Base | None:
        object = self.Meta.model(**fields)
        self.db_session.add(object)
        await self.db_session.flush()
        await self.db_session.refresh(object)
        return object

    async def update(self, object_id: UUID | Base, fields: dict)-> Base | None:
        object = None

        if isinstance(object_id, UUID):
            object = await self.get_by_id(object_id)
        else:
            object = object_id

        if not object:
            return None

        for field, value in fields.items():
            if value is not None:
                setattr(object, field, value)

        self.db_session.add(object)
        await self.db_session.flush()
        return object

class DeleteDALMixin:

    async def soft_delete(self, object_id: UUID) -> bool:
        """Soft delete an object by setting `is_active` to `False`.

        Args:
            object_id (UUID): The ID of the object to soft delete.

        Returns:
            bool: True if the object was found and updated, False if not found.
        """
        
        if not hasattr(self, 'Meta') or not hasattr(self.Meta, 'model'):
            raise AttributeError("Class must define 'Meta' class with a 'model' attribute.")
        
        if not hasattr(self, 'db_session'):
            raise AttributeError("Class must define 'db_session' attribute.")
        
        query = (
            update(self.Meta.model)
            .where(self.Meta.model.id == object_id)
            .values(is_active=False)
            .execution_options(synchronize_session="fetch")
        )
        result = await self.db_session.execute(query)

        return result.rowcount > 0 
        
        



@dataclass
class BaseUserPkDals:
    """Implementation of basic CRUD operation"""
    db_session: AsyncSession

    class Meta:
        model = None

    async def get_by_user_id(self, user_id: UUID) -> Base | None:
        query = select(self.Meta.model).where(self.Meta.model.user_id == user_id)
        result = await self.db_session.execute(query)
        object = result.scalar_one_or_none()
        return object

    async def create(self, fields: dict) -> Base | None:
        object = self.Meta.model(**fields)
        self.db_session.add(object)
        await self.db_session.flush()
        return object

    async def update_by_user_id(self, user_id: UUID, fields: dict) -> None:

        query = (
            update(self.Meta.model)
            .where(self.Meta.model.user_id==user_id)
            .values(**fields)
        )
        await self.db_session.execute(query)
        await self.db_session.flush()
        return None