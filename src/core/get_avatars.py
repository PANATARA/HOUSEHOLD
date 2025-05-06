import asyncio
from dataclasses import dataclass
from uuid import UUID

from fastapi import UploadFile
from pydantic import BaseModel

from config import (
    ALLOWED_CONTENT_TYPES,
    FAMILY_URL_AVATAR_EXPIRE,
    USER_URL_AVATAR_EXPIRE,
)
from core.enums import StorageFolderEnum
from core.exceptions.image_exceptions import (
    ImageSizeTooLargeError,
    NotAllowdedContentTypes,
)
from core.redis_connection import redis_client
from core.services import BaseService
from core.storage import PresignedUrl, get_s3_client
from families.models import Family
from users.models import User


async def update_user_avatars(data):
    from users.schemas import UserResponseSchema

    if isinstance(data, UserResponseSchema):
        await data.set_avatar_url()
    if isinstance(data, list):
        await asyncio.gather(*(update_user_avatars(item) for item in data))
    elif isinstance(data, BaseModel):
        await asyncio.gather(
            *(update_user_avatars(getattr(data, field)) for field in data.model_fields)
        )


async def update_family_avatars(data):
    from families.schemas import FamilyResponseSchema

    if isinstance(data, FamilyResponseSchema):
        await data.set_avatar_url()
    if isinstance(data, list):
        await asyncio.gather(*(update_family_avatars(item) for item in data))
    elif isinstance(data, BaseModel):
        await asyncio.gather(
            *(
                update_family_avatars(getattr(data, field))
                for field in data.model_fields
            )
        )


@dataclass
class AvatarService(BaseService[str | None]):
    object_id: UUID
    folder: StorageFolderEnum

    async def process(self) -> str | None:
        self.redis = redis_client.get_client()
        url = await self.get_url_from_redis()

        if url == "no_avatar":
            return None
        if url is None:

            url = await self.get_url_from_s3_storage()

            if url is None:
                await self.set_url_redis("no_avatar")
                return None
            else:
                await self.set_url_redis(url)
        return url

    async def get_url_from_redis(self) -> str | None:
        return await self.redis.get(str(self.object_id))

    async def set_url_redis(self, url: str) -> None:
        await self.redis.set(str(self.object_id), url, ex=USER_URL_AVATAR_EXPIRE)

    async def get_url_from_s3_storage(self) -> str | None:
        s3_storage = get_s3_client()
        avatar_url = await s3_storage.generate_presigned_url(
            object_key=str(self.object_id), folder=self.folder
        )
        return avatar_url


async def upload_object_image(object: User | Family, file: UploadFile) -> PresignedUrl:
    key = str(object.id)

    if isinstance(object, User):
        folder = StorageFolderEnum.users_avatars
        expire = USER_URL_AVATAR_EXPIRE
    elif isinstance(object, Family):
        folder = StorageFolderEnum.family_avatars
        expire = FAMILY_URL_AVATAR_EXPIRE
    else:
        raise ValueError()  # TODO make a suitable exception

    content_type = file.content_type

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise NotAllowdedContentTypes(
            message=f"Format Error: {file.content_type}. Allowed content types: JPEG, PNG, WebP."
        )

    object_image = await file.read()
    if len(object_image) > 1_048_576:  # TODO: increase file size
        raise ImageSizeTooLargeError(
            message=f"Image size too large: {len(object_image)} bytes"
        )

    s3_client = get_s3_client()

    await s3_client.upload_file(object_image, content_type, key, folder)
    presigned_url = await s3_client.generate_presigned_url(key, folder)

    redis = redis_client.get_client()
    await redis.set(key, presigned_url, ex=expire)

    return presigned_url
