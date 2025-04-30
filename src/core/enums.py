import enum
from abc import abstractmethod


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
