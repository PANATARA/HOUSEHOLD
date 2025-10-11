from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import mimetypes
import os
import secrets
from typing import Awaitable
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    ALLOWED_CONTENT_TYPES,
    BASE_URL,
    FAMILY_URL_AVATAR_EXPIRE,
    UPLOAD_DIR,
    USE_S3_STORAGE,
    USER_URL_AVATAR_EXPIRE,
)
from core.enums import StorageFolderEnum
from core.exceptions.image_exceptions import (
    ImageSizeTooLargeError,
    NotAllowdedContentTypes,
)
from core.redis_connection import redis_client
from core.services import BaseService
from core.storage import LocalStorageService, PresignedUrl, get_s3_client
from families.models import Family
from users.models import User


@dataclass
class OldGetAvatarService(BaseService[str | None]):
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


@dataclass
class GetAvatarService(BaseService[str | None]):
    target_object: User | Family
    db_session: AsyncSession

    async def process(self) -> str | None:
        avatar_key = self.target_object.avatar_key
        if avatar_key is None:
            return None
        folder = self.get_folder()
        if USE_S3_STORAGE:
            return await self.get_avatar_from_s3_storage(folder)
        else:
            return await self.get_avatar_from_local_storage(avatar_key, folder)

    async def get_avatar_from_local_storage(
        self, avatar_key: str, folder: StorageFolderEnum
    ) -> str | None:
        file_path = os.path.join(UPLOAD_DIR, folder.value, avatar_key)
        print(file_path)
        if not os.path.isfile(file_path):
            return None
        return f"{BASE_URL}/uploads/{folder.value}/{avatar_key}"

    def get_folder(self) -> StorageFolderEnum:
        if isinstance(self.target_object, User):
            return StorageFolderEnum.users_avatars
        elif isinstance(self.target_object, Family):
            return StorageFolderEnum.family_avatars
        else:
            raise ValueError()

    async def get_avatar_from_s3_storage(self, folder: StorageFolderEnum) -> str | None:
        service = OldGetAvatarService(self.target_object.id, folder)
        return await service.run_process()


@dataclass
class UploadAvatarService(BaseService[str]):
    object: User | Family
    file: UploadFile
    db_session: AsyncSession

    async def process(self) -> str:
        folder, expire = self.get_folder_expire()
        avatar_key = self.generate_avatar_key(self.object.id)

        if USE_S3_STORAGE:
            url = await self.upload_to_s3_storage(folder, expire)
        else:
            url = await self.upload_to_local_storage(avatar_key, folder)

        await self.save_avatar_key_db(avatar_key)
        return url

    async def upload_to_s3_storage(
        self, folder: StorageFolderEnum, expire: int
    ) -> PresignedUrl:
        s3_client = get_s3_client()
        object_key = str(self.object.id)
        await s3_client.upload_file(
            file_obj=self.object_image,
            content_type=self.content_type,  # type: ignore
            object_key=object_key,
            folder=folder,
        )
        presigned_url = await s3_client.generate_presigned_url(object_key, folder)
        redis = redis_client.get_client()
        await redis.set(object_key, presigned_url, ex=expire)
        return presigned_url

    async def upload_to_local_storage(
        self, filename: str, folder: StorageFolderEnum
    ) -> str:
        service = LocalStorageService(
            file_bytes=self.object_image,
            filename=filename,
            folder_enum=folder,
            content_type=self.content_type,  # type: ignore
        )
        return await service.save()

    def get_folder_expire(self) -> tuple[StorageFolderEnum, int]:
        if isinstance(self.object, User):
            folder = StorageFolderEnum.users_avatars
            expire = USER_URL_AVATAR_EXPIRE
        elif isinstance(self.object, Family):
            folder = StorageFolderEnum.family_avatars
            expire = FAMILY_URL_AVATAR_EXPIRE
        else:
            raise ValueError(
                "Unsupported object type"
            )  # TODO make a suitable exception
        return folder, expire

    def generate_avatar_key(self, id: UUID) -> str:
        salt = secrets.token_bytes(16)
        data = id.bytes + salt
        avatar_key = hashlib.sha256(data).hexdigest()
        return avatar_key

    async def save_avatar_key_db(self, avatar_key: str):
        extension = mimetypes.guess_extension(self.content_type) or ""  # type: ignore
        self.object.avatar_key = f"{avatar_key}{extension}"
        self.db_session.add(self.object)
        await self.db_session.commit()

    def validate_content_type(self):
        self.content_type = self.file.content_type

        if self.content_type not in ALLOWED_CONTENT_TYPES:
            raise NotAllowdedContentTypes(
                message=f"Format Error: {self.content_type}. Allowed content types: JPEG, PNG, WebP, GIF."
            )

    async def validate_size(self):
        self.object_image = await self.file.read()
        if len(self.object_image) > 15_728_640:
            raise ImageSizeTooLargeError(
                message=f"Image size too large: {len(self.object_image)} bytes"
            )

    def get_validators(
        self,
    ) -> list[Callable[[], None] | Callable[[], Awaitable[None]]]:
        return [self.validate_content_type, self.validate_size]


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
            message=f"Format Error: {file.content_type}. Allowed content types: JPEG, PNG, WebP, GIF."
        )

    object_image = await file.read()
    if len(object_image) > 15_728_640:
        raise ImageSizeTooLargeError(
            message=f"Image size too large: {len(object_image)} bytes"
        )

    s3_client = get_s3_client()

    await s3_client.upload_file(object_image, content_type, key, folder)
    presigned_url = await s3_client.generate_presigned_url(key, folder)

    redis = redis_client.get_client()
    await redis.set(key, presigned_url, ex=expire)

    return presigned_url
