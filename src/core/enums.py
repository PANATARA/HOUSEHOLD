import enum
from abc import abstractmethod


class PostgreSQLEnum(enum.Enum):
    @classmethod
    def get_subclasses(cls):
        return cls.__subclasses__()

    @classmethod
    @abstractmethod
    def get_enum_name(self) -> str:
        raise NotImplementedError("Please implement in the Enum class")


class FrequencyTypeENUM(PostgreSQLEnum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"

    @classmethod
    def get_enum_name(self):
        return "frequency_type"
