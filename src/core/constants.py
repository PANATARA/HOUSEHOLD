import enum

default_user_settings = {
    "app_theme": "light"
}


default_admin_permissions = {
    "should_confirm_chore_completion": True,
}

default_user_permissions = {
    "should_confirm_chore_completion": False,
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
