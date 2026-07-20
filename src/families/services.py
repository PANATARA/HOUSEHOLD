import random
import string

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions.families import InvalidInviteCodeError, UserCannotLeaveFamily
from core.services import BaseService
from core.validators import validate_user_not_in_family
from families.models import Family
from families.repository import FamilyRepository
from users.models import User, UserFamilyPermissions
from users.repository import UserPermissionsRepository, UserRepository
from users.schemas import UserFamilyPermissionModelSchema
from wallets.models import Wallet
from wallets.repository import WalletRepository
from wallets.services import WalletCreatorService
from database_connection import redis_client


@dataclass
class FamilyCreatorService(BaseService[Family]):
    """Create and return a new Family"""

    name: str
    icon: str
    icon_color: str
    icon_bg: str
    user: User  # User who creates a family
    db_session: AsyncSession

    async def process(self) -> Family:
        family = await self._create_family()
        await self._add_user_to_family(family)
        return family

    async def _create_family(self) -> Family:
        family_dal = FamilyRepository(self.db_session)
        new_family = await family_dal.create(
            Family(
                name=self.name,
                icon=self.icon,
                icon_color=self.icon_color,
                icon_bg=self.icon_bg,
                family_admin_id=self.user.id,
            )
        )
        return new_family

    async def _add_user_to_family(self, family: Family) -> None:
        new_member = AddUserToFamilyService(
            family=family,
            user=self.user,
            permissions=UserFamilyPermissionModelSchema(can_invite_users=True),
            db_session=self.db_session,
        )
        await new_member.run_process()


@dataclass
class AddUserToFamilyService(BaseService[Family]):
    family: Family
    user: User
    permissions: UserFamilyPermissionModelSchema
    db_session: AsyncSession

    async def process(self) -> Family:
        await self._add_user_to_family()
        await self._create_user_wallet()
        await self._create_permissions(self.permissions.model_dump())
        return self.family

    async def _add_user_to_family(self) -> None:
        user_dal = UserRepository(self.db_session)
        self.user.family_id = self.family.id
        await user_dal.update(self.user)

    async def _create_permissions(self, fields: dict) -> UserFamilyPermissions:
        perm_dal = UserPermissionsRepository(self.db_session)
        fields = self.permissions.model_dump()
        fields["user_id"] = self.user.id
        return await perm_dal.create(UserFamilyPermissions(**fields))

    async def _create_user_wallet(self) -> Wallet:
        user_wallet = WalletCreatorService(self.user, self.db_session)
        return await user_wallet.run_process()

    def get_validators(self):
        return [lambda: validate_user_not_in_family(self.user)]


@dataclass
class LogoutUserFromFamilyService(BaseService[None]):
    """Logout user from family"""

    user: User
    db_session: AsyncSession

    async def process(self) -> None:
        await self._update_user_field()
        await self._delete_user_permissions()
        await self._delete_user_wallet()

    async def _update_user_field(self) -> None:
        user_dal = UserRepository(self.db_session)
        self.user.family_id = None
        await user_dal.update(self.user)

    async def _delete_user_permissions(self) -> None:
        permissions_repo = UserPermissionsRepository(self.db_session)
        user_permission = await permissions_repo.get_by_user_id(self.user.id)
        await permissions_repo.hard_delete(user_permission.id)

    async def _delete_user_wallet(self) -> None:
        wallet_repo = WalletRepository(self.db_session)
        wallet = await wallet_repo.get_by_user_id(self.user.id)
        await wallet_repo.hard_delete(wallet.id)

    async def _delete_user_products(self) -> None:
        pass

    async def validate(self):
        family_dal = FamilyRepository(self.db_session)
        if await family_dal.user_is_family_admin(self.user.id, self.user.family_id):
            raise UserCannotLeaveFamily()


FAMILY_INVITE_CODE_LENGTH_LETTERS = 3
FAMILY_INVITE_CODE_LENGTH_DIGITS = 3
FAMILY_INVITE_CODE_EXPIRE = 60 * 5


@dataclass
class GenerateFamilyInviteTokenService(BaseService[tuple[str, int]]):
    user: User
    db_session: AsyncSession

    async def process(self) -> tuple[str, int]:
        self.redis = await redis_client.get_client()

        existing_code = await self._get_invite_code_from_redis()
        if existing_code:
            ttl = await self._get_invite_code_ttl()
            return existing_code, ttl

        code = await self._generate_unique_invite_code()
        await self._set_invite_code_to_redis(code)
        return code, FAMILY_INVITE_CODE_EXPIRE

    async def _generate_unique_invite_code(self) -> str:
        for _ in range(100):
            code = self._generate_invite_code()
            family_id = await self.redis.get(self._invite_code_key(code))
            if family_id is None:
                return code
        raise RuntimeError(
            "Failed to generate unique family invite code after 100 attempts"
        )

    def _generate_invite_code(self) -> str:
        letters = "".join(
            random.choices(
                string.ascii_uppercase,
                k=FAMILY_INVITE_CODE_LENGTH_LETTERS,
            )
        )
        digits = "".join(
            random.choices(
                string.digits,
                k=FAMILY_INVITE_CODE_LENGTH_DIGITS,
            )
        )
        return f"{letters}{digits}"

    async def _get_invite_code_from_redis(self) -> str | None:
        value = await self.redis.get(str(self.user.family_id))
        return value.decode() if isinstance(value, bytes) else value

    async def _get_invite_code_ttl(self) -> int:
        ttl = await self.redis.ttl(str(self.user.family_id))
        return ttl if ttl > 0 else FAMILY_INVITE_CODE_EXPIRE

    async def _set_invite_code_to_redis(self, code: str) -> None:
        family_key = str(self.user.family_id)
        code_key = self._invite_code_key(code)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.set(family_key, code, ex=FAMILY_INVITE_CODE_EXPIRE)
            pipe.set(code_key, str(self.user.family_id), ex=FAMILY_INVITE_CODE_EXPIRE)
            await pipe.execute()

    @staticmethod
    def _invite_code_key(code: str) -> str:
        return f"family_invite:{code}"


@dataclass
class JoinFamilyByInviteCodeService(BaseService[Family]):
    user: User
    invite_code: str
    db_session: AsyncSession

    async def process(self) -> Family:
        self.redis = await redis_client.get_client()

        family_id = await self._get_family_id_from_code()
        if family_id is None:
            raise InvalidInviteCodeError("Invite code is invalid or expired")

        family = await self._get_family(family_id)
        if family is None:
            raise InvalidInviteCodeError("Family for this invite code no longer exists")

        await self._join_family(family)

        return family

    async def _get_family_id_from_code(self) -> UUID | None:
        value = await self.redis.get(self._invite_code_key(self.invite_code))
        if value is None:
            return None
        family_id_str = value.decode() if isinstance(value, bytes) else value
        return UUID(family_id_str)

    async def _get_family(self, family_id: UUID) -> Family | None:
        return await FamilyRepository(self.db_session).get_by_id(family_id)

    async def _join_family(self, family: Family) -> None:
        service = AddUserToFamilyService(
            family=family,
            user=self.user,
            permissions=UserFamilyPermissionModelSchema(can_invite_users=True),
            db_session=self.db_session,
        )
        await service.run_process()

    @staticmethod
    def _invite_code_key(code: str) -> str:
        return f"family_invite:{code}"
