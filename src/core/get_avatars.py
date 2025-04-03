import asyncio
from dataclasses import dataclass
from uuid import UUID
from pydantic import BaseModel

from core.constants import USER_URL_AVATAR_EXPIRE, StorageFolderEnum
from core.services import BaseService
from core.storage import get_s3_client
from core.redis_connection import redis_client

async def update_user_avatars(data):
    from schemas.users import UserSummarySchema
    
    if isinstance(data, UserSummarySchema):
            await data.set_avatar_url()
    if isinstance(data, list):
        await asyncio.gather(*(update_user_avatars(item) for item in data))
    elif isinstance(data, BaseModel):
        await asyncio.gather(*(update_user_avatars(getattr(data, field)) for field in data.model_fields))

@dataclass
class AvatarService(BaseService):
    user_id: UUID

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
        return await self.redis.get(str(self.user_id))

    async def set_url_redis(self, url: str) -> None:
        await self.redis.set(str(self.user_id), url, ex=USER_URL_AVATAR_EXPIRE)

    async def get_url_from_s3_storage(self) -> str | None:
        s3_storage = get_s3_client()
        avatar_url = await s3_storage.generate_presigned_url(
            object_key=str(self.user_id), folder=StorageFolderEnum.users_avatars
        )
        return avatar_url
