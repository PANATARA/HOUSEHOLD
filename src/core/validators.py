from uuid import UUID

from chores.models import Chore
from chores_completions.models import ChoreCompletion
from core.enums import StatusConfirmENUM
from core.exceptions.chores import ChoreNotFoundError
from core.exceptions.chores_completion import ChoreCompletionCanNotBeChanged, ChoreCompletionIsNotApproved
from core.exceptions.families import UserIsAlreadyFamilyMember, UserNotFoundInFamily
from core.exceptions.products import ProductError, ProductNotFoundError
from products.models import Product
from users.models import User


def validate_user_in_family(user: User, family_id: UUID) -> None:
    if user.family_id != family_id:
        raise UserNotFoundInFamily()


def validate_chore_is_active(chore: Chore) -> None:
    if not chore.is_active:
        raise ChoreNotFoundError()


def validate_chore_completion_is_changable(chore_completion: ChoreCompletion) -> None:
    if chore_completion.status != StatusConfirmENUM.awaits:
        raise ChoreCompletionCanNotBeChanged()

def validate_chore_completion_is_approved(chore_completion: ChoreCompletion) -> None:
    if chore_completion.status != StatusConfirmENUM.approved:
        raise ChoreCompletionIsNotApproved()

def validate_user_not_in_family(user: User) -> None:
    if user.family_id is not None:
        raise UserIsAlreadyFamilyMember()


def validate_product_is_active(product: Product) -> None:
    if not product.is_active:
        raise ProductNotFoundError()


def validate_user_can_buy_product(product: Product, byuer: User):
    if product.seller_id == byuer.id:
        raise ProductError()
