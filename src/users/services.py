from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core import constants
from core.exceptions.image_exceptions import NotAllowdedContentTypes
from core.exceptions.users import UserAvatarSizeTooLargre
from core.hashing import Hasher
from core.services import BaseService
from core.redis_connection import redis_client
from core.storage import PresignedUrl, get_s3_client
from users.models import User, UserSettings
from users.repository import AsyncUserDAL, AsyncUserSettingsDAL


@dataclass
class UserCreatorService(BaseService[User]):
    """Create and return a new Family"""

    username: str
    name: str
    surname: str
    password: str
    db_session: AsyncSession

    async def process(self) -> User:
        user = await self._create_user(
            {
                "username": self.username,
                "name": self.name,
                "surname": self.surname,
                "hashed_password": self._get_hash_password(),
            }
        )
        settings_fields = constants.default_user_settings
        settings_fields["user_id"] = user.id
        await self._create_settings(settings_fields)
        return user

    def _get_hash_password(self) -> str:
        return Hasher.get_password_hash(self.password)

    async def _create_user(self, fields: dict) -> User:
        user_dal = AsyncUserDAL(self.db_session)
        return await user_dal.create(fields)

    async def _create_settings(self, fields: dict) -> UserSettings:
        settings_dal = AsyncUserSettingsDAL(self.db_session)
        return await settings_dal.create(fields)


async def update_user_avatar(user: User, file: UploadFile) -> PresignedUrl:
    key = str(user.id)
    folder = constants.StorageFolderEnum.users_avatars
    content_type = file.content_type

    if content_type not in constants.ALLOWED_CONTENT_TYPES:
        raise NotAllowdedContentTypes(
            message=f"Format Error: {file.content_type}. Allowed content types: JPEG, PNG, WebP."
        )

    user_avatar = await file.read()
    if len(user_avatar) > 1_048_576:
        raise UserAvatarSizeTooLargre(
            message=f"Image size too large: {len(user_avatar)} bytes"
        )

    s3_client = get_s3_client()

    await s3_client.upload_file(user_avatar, content_type, key, folder)
    presigned_url = await s3_client.generate_presigned_url(key, folder)

    redis = redis_client.get_client()
    await redis.set(key, presigned_url, ex=constants.USER_URL_AVATAR_EXPIRE)

    return presigned_url
