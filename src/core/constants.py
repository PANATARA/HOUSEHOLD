import enum


class ChoreLogEnum(enum.Enum):
    awaiting_confirmation = 0
    canceled = 1
    completed = 2


class TransactionTypeEnum(enum.Enum):
    purchase = 0
    income = 1
    transfer = 2


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