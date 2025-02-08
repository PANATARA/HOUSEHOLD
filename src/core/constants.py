import enum


class ChoreLogEnum(enum.Enum):
    awaiting_confirmation = 0
    canceled = 1
    completed = 2


class TransactionTypeEnum(enum.Enum):
    purchase = 0
    income = 1
    transfer = 2