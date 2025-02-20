import enum

default_user_settings = {
    "app_theme": "light"
}


default_admin_permissions = {
    "should_confirm_chorelog": True,
    "should_confirm_creating_chore": True,
    "can_create_chore": True,
    "can_change_family_name": True,
    "can_kick_user": True,
    "can_invite_users": True,
    "can_promote_user": True,
}

default_user_permissions = {
    "should_confirm_chorelog": False,
    "should_confirm_creating_chore": False,
    "can_create_chore": False,
    "can_change_family_name": False,
    "can_kick_user": False,
    "can_invite_users": False,
    "can_promote_user": False,
}
from abc import abstractmethod


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
    canceled  ="canceled"
    approved = "approved"
    
    @classmethod
    def get_enum_name(self):
        return "status_confirm"


class WalletTransactionENUM(PostgreSQLEnum):
    transfer = "transfer"
    purchase = "purchase"
    income = "income"

    @classmethod
    def get_enum_name(self):
        return "transaction_type"
