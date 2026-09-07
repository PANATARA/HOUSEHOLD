from datetime import date
from uuid import UUID

from chores.models import Chore
from core.exceptions.chores import ChoreNotFoundError
from core.exceptions.chores_completion import (
    ChoreCompletionCanNotBeChanged,
)
from core.exceptions.families import UserIsAlreadyFamilyMember, UserNotFoundInFamily
from core.exceptions.products import ProductError, ProductNotFoundError
from planned_chores.models import PlannedChore, QuickPlannedChore
from products.models import Product
from users.models import User


def validate_user_in_family(user: User, family_id: UUID) -> None:
    if user.family_id != family_id:
        raise UserNotFoundInFamily()


def validate_chore_is_active(chore: Chore) -> None:
    if not chore.is_active:
        raise ChoreNotFoundError()


def validate_date_is_not_in_past(due_date: date) -> None:
    if due_date < date.today():
        raise ChoreCompletionCanNotBeChanged()


def validate_planned_chore_is_completed(target: PlannedChore) -> None:
    if target.completed_by_id is None:
        raise ChoreCompletionCanNotBeChanged()


def validate_planned_chore_is_not_completed(target: PlannedChore) -> None:
    if target.completed_by_id is not None:
        raise ChoreCompletionCanNotBeChanged()


def validate_quick_planned_chore_is_not_completed(target: QuickPlannedChore) -> None:
    if target.completed_by_id is not None:
        raise ChoreCompletionCanNotBeChanged()


def validate_quick_planned_chore_is_completed(target: QuickPlannedChore) -> None:
    if target.completed_by_id is None:
        raise ChoreCompletionCanNotBeChanged()


def validate_user_not_in_family(user: User) -> None:
    if user.family_id is not None:
        raise UserIsAlreadyFamilyMember()


def validate_product_is_active(product: Product) -> None:
    if not product.is_active:
        raise ProductNotFoundError()


def validate_user_can_buy_product(product: Product, byuer: User):
    if product.seller_id == byuer.id:
        raise ProductError()
