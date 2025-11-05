from collections.abc import Callable
from dataclasses import dataclass
import mimetypes
import os
from typing import Awaitable
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    ALLOWED_CONTENT_TYPES,
    FAMILY_URL_AVATAR_EXPIRE,
    PRODUCT_AVATAR_EXPIRE,
    UPLOAD_DIR,
    USE_S3_STORAGE,
    USER_URL_AVATAR_EXPIRE,
)
from core.enums import StorageFolderEnum
from core.exceptions.image_exceptions import (
    ImageSizeTooLargeError,
    NotAllowdedContentTypes,
)
from database_connection import redis_client
from core.services import BaseService
from core.storage import LocalStorageService, PresignedUrl, get_s3_client
from families.models import Family
from families.repository import AsyncFamilyDAL
from products.models import Product
from products.repository import AsyncProductDAL
from users.models import User
from users.repository import AsyncUserDAL


def get_folder_expire(
    target_object: str | User | Family | Product,
) -> tuple[StorageFolderEnum, int]:
    if isinstance(target_object, User) or target_object == "User":
        folder = StorageFolderEnum.users_avatars
        expire = USER_URL_AVATAR_EXPIRE
    elif isinstance(target_object, Family) or target_object == "Family":
        folder = StorageFolderEnum.family_avatars
        expire = FAMILY_URL_AVATAR_EXPIRE
    elif isinstance(target_object, Product) or target_object == "Product":
        folder = StorageFolderEnum.product_avatars
        expire = PRODUCT_AVATAR_EXPIRE
    else:
        raise ValueError("Unsupported object type")  # TODO make a suitable exception
    return folder, expire


@dataclass
class OldGetAvatarService(BaseService[str | None]):
    object_id: UUID
    folder: StorageFolderEnum

    async def process(self) -> str | None:
        self.redis = await redis_client.get_client()
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
    target_kind: str
    target_object_id: UUID
    db_session: AsyncSession

    async def process(self) -> str | None:
        folder, _ = get_folder_expire(self.target_kind)

        if USE_S3_STORAGE:
            return await self.get_avatar_from_s3_storage(folder)
        else:
            target_object = await self.get_target_object()
            if target_object.avatar_version is None:
                return None
            return self.get_avatar_from_local_storage(target_object, folder)

    async def get_target_object(self) -> User | Family | Product:
        if self.target_kind == "User":
            target_object = await AsyncUserDAL(self.db_session).get_by_id(
                self.target_object_id
            )
        elif self.target_kind == "Family":
            target_object = await AsyncFamilyDAL(self.db_session).get_by_id(
                self.target_object_id
            )
        elif self.target_kind == "Product":
            target_object = await AsyncProductDAL(self.db_session).get_by_id(
                self.target_object_id
            )
        else:
            raise ValueError("Unknown target kind")
        return target_object

    def get_avatar_from_local_storage(
        self, target_object: User | Family | Product, folder: StorageFolderEnum
    ) -> str | None:
        file_path = os.path.join(
            UPLOAD_DIR,
            folder.value,
            f"{str(target_object.id)}{target_object.avatar_extension}",
        )
        if not os.path.isfile(file_path):
            return None
        return file_path

    async def get_avatar_from_s3_storage(self, folder: StorageFolderEnum) -> str | None:
        service = OldGetAvatarService(self.target_object_id, folder)
        return await service.run_process()


@dataclass
class UploadAvatarService(BaseService[str]):
    target_object: User | Family | Product
    file: UploadFile
    db_session: AsyncSession

    async def process(self) -> str:
        folder, expire = get_folder_expire(self.target_object)

        if USE_S3_STORAGE:
            url = await self.upload_to_s3_storage(folder, expire)
        else:
            url = await self.upload_to_local_storage(folder)

        await self.save_avatar_version_content_type()

        return url

    async def upload_to_s3_storage(
        self, folder: StorageFolderEnum, expire: int
    ) -> PresignedUrl:
        s3_client = get_s3_client()
        object_key = str(self.target_object.id)

        await s3_client.upload_file(
            file_obj=self.object_image,
            content_type=self.content_type,  # type: ignore
            object_key=object_key,
            folder=folder,
        )
        presigned_url = await s3_client.generate_presigned_url(object_key, folder)
        redis = await redis_client.get_client()
        await redis.set(object_key, presigned_url, ex=expire)
        return presigned_url

    async def upload_to_local_storage(self, folder: StorageFolderEnum) -> str:
        service = LocalStorageService(
            file_bytes=self.object_image,
            filename=str(self.target_object.id),
            folder_enum=folder,
            content_type=self.content_type,  # type: ignore
        )
        return await service.save()

    async def save_avatar_version_content_type(self):
        extension = mimetypes.guess_extension(self.content_type) or ""  # type: ignore
        self.target_object.avatar_extension = extension
        if self.target_object.avatar_version is None:
            self.target_object.avatar_version = 1
        else:
            self.target_object.avatar_version += 1
        self.db_session.add(self.target_object)
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
