from planned_chores.models import PlannedChore
from core.base_dals import BaseDals, DeleteDALMixin
from core.exceptions.chores_completion import ChoreCompletionNotFoundError


class PlannedChoreRepository(BaseDals[PlannedChore], DeleteDALMixin):
    model = PlannedChore
    not_found_exception = ChoreCompletionNotFoundError  # !Improve!

    async def get_family_planned_chore():
        pass
