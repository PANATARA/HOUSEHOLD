from logging import getLogger

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.permissions import IsAuthenicatedPermission
from database_connection import get_db
from notifications.repository import DeviceRepository
from notifications.schemas import (
    DeviceRegisterSchema,
    DeviceResponseSchema,
    NotificationSendTestSchema,
)
from notifications.service import NotificationService, is_fcm_available
from users.models import User

logger = getLogger(__name__)

router = APIRouter(tags=["Notifications"])


@router.post(
    path="/devices",
    summary="Register or update FCM device token",
    response_model=DeviceResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    body: DeviceRegisterSchema,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        repo = DeviceRepository(async_session)
        device = await repo.register_device(
            user_id=current_user.id,
            token=body.token,
            device_type=body.device_type,
            device_name=body.device_name,
        )
        return device


@router.delete(
    path="/devices/{token}",
    summary="Unregister FCM device token",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unregister_device(
    token: str,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> Response:
    async with async_session.begin():
        repo = DeviceRepository(async_session)
        await repo.unregister_device(user_id=current_user.id, token=token)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    path="/devices",
    summary="List current user's registered devices",
    response_model=list[DeviceResponseSchema],
)
async def list_user_devices(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        repo = DeviceRepository(async_session)
        devices = await repo.get_user_devices(user_id=current_user.id)
        return devices


@router.post(
    path="/test",
    summary="Send test push notification to current user's registered devices",
)
async def send_test_notification(
    body: NotificationSendTestSchema,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        service = NotificationService(async_session)
        result = await service.send_to_user(
            user_id=current_user.id,
            title=body.title,
            body=body.body,
            data=body.data,
        )
        return {
            "fcm_available": is_fcm_available(),
            "delivery": result,
        }
