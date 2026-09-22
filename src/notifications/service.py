import asyncio
import base64
import json
import logging
import os
from uuid import UUID

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.ext.asyncio import AsyncSession

import config
from notifications.repository import DeviceRepository

logger = logging.getLogger(__name__)

_firebase_initialized = False
_firebase_init_attempted = False


def init_firebase() -> bool:
    """Initialize Firebase Admin SDK with credentials from config/env."""
    global _firebase_initialized, _firebase_init_attempted

    if _firebase_initialized:
        return True

    if len(firebase_admin._apps) > 0:
        _firebase_initialized = True
        return True

    _firebase_init_attempted = True

    try:
        cred = None

        # 1. FCM_CREDENTIALS_JSON (raw JSON or base64 encoded JSON)
        if config.FCM_CREDENTIALS_JSON:
            raw_json = config.FCM_CREDENTIALS_JSON.strip()
            try:
                cert_dict = json.loads(raw_json)
            except Exception:
                try:
                    decoded = base64.b64decode(raw_json).decode("utf-8")
                    cert_dict = json.loads(decoded)
                except Exception as b64_err:
                    logger.error(f"Failed to parse FCM_CREDENTIALS_JSON: {b64_err}")
                    cert_dict = None

            if cert_dict:
                cred = credentials.Certificate(cert_dict)

        # 2. FCM_CREDENTIALS_PATH
        if cred is None and config.FCM_CREDENTIALS_PATH:
            path = config.FCM_CREDENTIALS_PATH
            if not os.path.isabs(path):
                # check relative to project root (one level up from src or current dir)
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                cand_path = os.path.join(base_dir, path)
                if os.path.exists(cand_path):
                    path = cand_path

            if os.path.exists(path):
                cred = credentials.Certificate(path)
            else:
                logger.warning(f"FCM_CREDENTIALS_PATH specified but file not found: {path}")

        # 3. Default fallback file locations
        if cred is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            for fname in ("serviceAccountKey.json", "firebase-credentials.json", "fcm-credentials.json"):
                cand_path = os.path.join(base_dir, fname)
                if os.path.exists(cand_path):
                    logger.info(f"Found FCM credentials file at {cand_path}")
                    cred = credentials.Certificate(cand_path)
                    break

        if cred is not None:
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK successfully initialized.")
            return True
        else:
            logger.warning(
                "FCM credentials not configured. Push notifications will be skipped. "
                "To enable, set FCM_CREDENTIALS_PATH or FCM_CREDENTIALS_JSON in .env"
            )
            return False

    except Exception as e:
        logger.error(f"Error initializing Firebase Admin SDK: {e}", exc_info=True)
        return False


def is_fcm_available() -> bool:
    """Check if FCM is available and initialized."""
    if not _firebase_initialized and not _firebase_init_attempted:
        init_firebase()
    return _firebase_initialized or len(firebase_admin._apps) > 0


class NotificationService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.device_repo = DeviceRepository(db_session)

    async def send_multicast(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> dict:
        """Send multicast notification to a list of tokens via FCM."""
        if not tokens:
            return {"total": 0, "success": 0, "failure": 0, "pruned": 0}

        if not is_fcm_available():
            logger.info("FCM is not initialized; skipping sending push notification.")
            return {
                "total": len(tokens),
                "success": 0,
                "failure": len(tokens),
                "pruned": 0,
                "reason": "fcm_not_configured",
            }

        # Format string dictionary for FCM data payload
        clean_data = {}
        if data:
            for k, v in data.items():
                clean_data[str(k)] = str(v)

        android_config = messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                sound="default",
                channel_id="household_chores_channel",
                default_sound=True,
                default_vibrate_timings=True,
            ),
        )

        notification = messaging.Notification(
            title=title,
            body=body,
        )

        total_success = 0
        total_failure = 0
        invalid_tokens = []

        # Send in chunks of 500 (FCM multicast limit)
        chunk_size = 500
        for i in range(0, len(tokens), chunk_size):
            chunk = tokens[i : i + chunk_size]
            multicast_message = messaging.MulticastMessage(
                tokens=chunk,
                notification=notification,
                data=clean_data,
                android=android_config,
            )

            try:
                response = await asyncio.to_thread(
                    messaging.send_each_for_multicast, multicast_message
                )
                total_success += response.success_count
                total_failure += response.failure_count

                if response.failure_count > 0:
                    for idx, resp in enumerate(response.responses):
                        if not resp.success:
                            err = resp.exception
                            err_str = str(err).lower()
                            # Check for unregistered or invalid tokens
                            if (
                                isinstance(err, messaging.UnregisteredError)
                                or "registration-token-not-registered" in err_str
                                or "invalid-argument" in err_str
                                or "not-registered" in err_str
                            ):
                                invalid_tokens.append(chunk[idx])
            except Exception as e:
                logger.error(f"Error during FCM multicast batch send: {e}", exc_info=True)
                total_failure += len(chunk)

        if invalid_tokens:
            logger.info(f"Pruning {len(invalid_tokens)} stale FCM token(s)...")
            await self.device_repo.delete_tokens(invalid_tokens)

        return {
            "total": len(tokens),
            "success": total_success,
            "failure": total_failure,
            "pruned": len(invalid_tokens),
        }

    async def send_to_user(
        self,
        user_id: UUID,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> dict:
        """Send notification to all Android devices of a single user."""
        tokens = await self.device_repo.get_user_tokens(user_id)
        return await self.send_multicast(tokens, title, body, data)

    async def send_to_family(
        self,
        family_id: UUID,
        title: str,
        body: str,
        exclude_user_id: UUID | None = None,
        data: dict[str, str] | None = None,
    ) -> dict:
        """Send notification to all Android devices in a family, optionally excluding the initiator."""
        tokens = await self.device_repo.get_family_tokens(
            family_id=family_id, exclude_user_id=exclude_user_id
        )
        return await self.send_multicast(tokens, title, body, data)

    async def notify_family_new_chore(
        self,
        family_id: UUID,
        creator_id: UUID,
        creator_name: str,
        chore_name: str,
        chore_id: UUID,
        chore_type: str = "planned",
    ) -> dict:
        """Notify other family members that a new chore was created."""
        title = f"Новая задача: {chore_name}"
        body = f"{creator_name} добавил(а) новую задачу в список"
        data = {
            "type": "new_chore",
            "chore_id": str(chore_id),
            "chore_name": chore_name,
            "chore_type": chore_type,
            "family_id": str(family_id),
            "creator_id": str(creator_id),
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
        }
        return await self.send_to_family(
            family_id=family_id,
            title=title,
            body=body,
            exclude_user_id=creator_id,
            data=data,
        )


async def notify_family_about_new_chore(
    family_id: UUID | None,
    creator_id: UUID,
    creator_name: str,
    chore_name: str,
    chore_id: UUID,
    chore_type: str = "planned",
) -> None:
    """Background task to send push notification to family members."""
    if not family_id:
        return
    try:
        from database_connection import async_session_maker

        async with async_session_maker() as session:
            async with session.begin():
                service = NotificationService(session)
                await service.notify_family_new_chore(
                    family_id=family_id,
                    creator_id=creator_id,
                    creator_name=creator_name,
                    chore_name=chore_name,
                    chore_id=chore_id,
                    chore_type=chore_type,
                )
    except Exception as e:
        logger.error(
            f"Failed to execute background push notification for chore {chore_id}: {e}",
            exc_info=True,
        )
