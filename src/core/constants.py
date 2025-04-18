import enum
from abc import abstractmethod

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

default_user_settings = {"app_theme": "light"}

default_admin_permissions = {
    "should_confirm_chore_completion": True,
}

default_user_permissions = {
    "should_confirm_chore_completion": False,
}

USER_URL_AVATAR_EXPIRE = 60 * 60 * 24
FAMILY_URL_AVATAR_EXPIRE = 60 * 60 * 24

class StorageFolderEnum(enum.Enum):
    users_avatars = "user_avatars"
    family_avatars = "family_avatars"


class PostgreSQLEnum(enum.Enum):

    @classmethod
    def get_subclasses(cls):
        return cls.__subclasses__()

    @classmethod
    @abstractmethod
    def get_enum_name(self) -> str:
        raise NotImplementedError("Please implement in the Enum class")


class StatusConfirmENUM(PostgreSQLEnum):
    awaits = "awaits"
    canceled = "canceled"
    approved = "approved"

    @classmethod
    def get_enum_name(self):
        return "status_confirm"


class PeerTransactionENUM(PostgreSQLEnum):
    transfer = "transfer"
    purchase = "purchase"

    @classmethod
    def get_enum_name(self):
        return "peer_transaction"


class RewardTransactionENUM(PostgreSQLEnum):
    reward_for_chore = "reward_for_chore"

    @classmethod
    def get_enum_name(self):
        return "system_transaction"


SAFE_METHODS = ["GET", "HEAD", "OPTIONS", "TRACE"]
