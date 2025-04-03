import asyncio
from dataclasses import dataclass
from uuid import UUID
from pydantic import BaseModel

from core.constants import StorageFolderEnum
from core.services import BaseService
from core.storage import get_s3_client

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
        return "test/url.com"
        # url = await self.get_url_from_redis()
        # if url is None:
        #     url = await self.get_url_from_s3_storage()
        # await self.set_url_redis(url=url)
        # return url
        
    async def get_url_from_redis(self) -> str | None:
        pass

    async def set_url_redis(self, url: str) -> None:
        pass

    async def get_url_from_s3_storage(self) -> str | None:
        s3_storage = get_s3_client()
        avatar_url = await s3_storage.generate_presigned_url(
            object_key=str(self.id), folder=StorageFolderEnum.users_avatars
        )
        return avatar_url
