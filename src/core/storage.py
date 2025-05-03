from contextlib import asynccontextmanager
from typing import NewType

import aioboto3
from botocore.exceptions import ClientError

from config import (
    S3_ACCESS_KEY,
    S3_BUCKET_NAME,
    S3_ENDPOINT_URL,
    S3_SECRET_KEY,
    USER_URL_AVATAR_EXPIRE,
)
from core.enums import StorageFolderEnum

PresignedUrl = NewType("PresignedUrl", str)


class S3Client:
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        endpoint_url: str,
        bucket_name: str,
        region_name: str = "ru-1",
    ):
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name
        self.region_name = region_name

    @asynccontextmanager
    async def get_client(self):
        session = aioboto3.Session()
        async with session.client(
            service_name="s3",
            region_name=self.region_name,
            endpoint_url=self.endpoint_url,
            aws_secret_access_key=self.secret_key,
            aws_access_key_id=self.access_key,
        ) as client:
            yield client

    async def upload_file(
        self,
        file_obj: bytes,
        content_type: str,
        object_key: str,
        folder: StorageFolderEnum,
    ) -> None:

        key = f"{folder.value}/{object_key}"
        async with self.get_client() as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_obj,
                ContentType=content_type,
            )

    async def generate_presigned_url(
        self,
        object_key: str,
        folder: StorageFolderEnum,
        expires_in: int = USER_URL_AVATAR_EXPIRE,
    ) -> PresignedUrl | None:
        key = f"{folder.value}/{object_key}"
        async with self.get_client() as client:
            try:
                await client.head_object(Bucket=self.bucket_name, Key=key)
                url = await client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": self.bucket_name, "Key": key},
                    ExpiresIn=expires_in,
                )
                return url
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return None
                print(f"Error during generation presigned URL: {e}")
                return None


def get_s3_client() -> S3Client:
    return S3Client(
        access_key=S3_ACCESS_KEY,
        secret_key=S3_SECRET_KEY,
        endpoint_url=S3_ENDPOINT_URL,
        bucket_name=S3_BUCKET_NAME,
    )
