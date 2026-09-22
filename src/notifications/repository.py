from uuid import UUID
from sqlalchemy import delete, select

from core.base_dals import BaseDals
from core.exceptions.base_exceptions import ObjectNotFoundError
from notifications.models import UserDevice
from users.models import User


class DeviceNotFoundError(ObjectNotFoundError):
    pass


class DeviceRepository(BaseDals[UserDevice]):
    model = UserDevice
    not_found_exception = DeviceNotFoundError

    async def register_device(
        self,
        user_id: UUID,
        token: str,
        device_type: str = "android",
        device_name: str | None = None,
    ) -> UserDevice:
        stmt = select(UserDevice).where(UserDevice.token == token)
        result = await self.db_session.execute(stmt)
        existing_device = result.scalar_one_or_none()

        if existing_device:
            existing_device.user_id = user_id
            existing_device.device_type = device_type
            if device_name is not None:
                existing_device.device_name = device_name
            await self.db_session.flush()
            await self.db_session.refresh(existing_device)
            return existing_device

        device = UserDevice(
            user_id=user_id,
            token=token,
            device_type=device_type,
            device_name=device_name,
        )
        self.db_session.add(device)
        await self.db_session.flush()
        await self.db_session.refresh(device)
        return device

    async def unregister_device(self, user_id: UUID, token: str) -> bool:
        stmt = (
            delete(UserDevice)
            .where(UserDevice.user_id == user_id, UserDevice.token == token)
            .returning(UserDevice.id)
        )
        result = await self.db_session.execute(stmt)
        await self.db_session.flush()
        return result.scalar_one_or_none() is not None

    async def get_user_devices(self, user_id: UUID) -> list[UserDevice]:
        stmt = (
            select(UserDevice)
            .where(UserDevice.user_id == user_id)
            .order_by(UserDevice.created_at.desc())
        )
        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_tokens(self, user_id: UUID) -> list[str]:
        stmt = select(UserDevice.token).where(
            UserDevice.user_id == user_id,
            UserDevice.device_type == "android",
        )
        result = await self.db_session.execute(stmt)
        return list(set(result.scalars().all()))

    async def get_family_tokens(
        self,
        family_id: UUID,
        exclude_user_id: UUID | None = None,
    ) -> list[str]:
        stmt = (
            select(UserDevice.token)
            .join(User, User.id == UserDevice.user_id)
            .where(
                User.family_id == family_id,
                User.is_active.is_(True),
                UserDevice.device_type == "android",
            )
        )
        if exclude_user_id is not None:
            stmt = stmt.where(UserDevice.user_id != exclude_user_id)

        result = await self.db_session.execute(stmt)
        return list(set(result.scalars().all()))

    async def delete_tokens(self, tokens: list[str]) -> None:
        if not tokens:
            return
        await self.db_session.execute(
            delete(UserDevice).where(UserDevice.token.in_(tokens))
        )
        await self.db_session.flush()
