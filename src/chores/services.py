from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from chores.models import Chore, DefaultChore
from chores.repository import ChoreRepository, DefaultChoreRepository
from chores.schemas import ChoreCreateSchema
from core.services import BaseService
from families.models import Family


@dataclass
class ChoreCreatorService(BaseService[Chore]):
    """Create and return a new Family"""

    family: Family
    db_session: AsyncSession
    data: ChoreCreateSchema

    async def process(self) -> Chore:
        return await self._create_chore()

    async def _create_chore(self) -> Chore:
        chore_dal = ChoreRepository(self.db_session)

        return await chore_dal.create(
            Chore(
                name=self.data.name,
                description=self.data.description,
                icon=self.data.icon,
                icon_color=self.data.icon_color,
                icon_bg=self.data.icon_bg,
                valuation=self.data.valuation,
                family_id=self.family.id,
            )
        )


@dataclass
class ChoreFromDefaultService(BaseService[Chore | list[Chore]]):
    """Create Chore(s) from DefaultChore template(s)"""

    family_id: UUID
    db_session: AsyncSession
    default_chore_ids: UUID | list[UUID]
    language: str = "ru"

    async def process(self) -> Chore | list[Chore]:
        if isinstance(self.default_chore_ids, list):
            return await self._create_many()
        return await self._create_one()

    async def _create_one(self) -> Chore:
        default_chores = await DefaultChoreRepository(
            self.db_session
        ).get_by_ids_with_translations([self.default_chore_ids])  # type: ignore

        if not default_chores:
            raise ValueError(f"DefaultChore {self.default_chore_ids} not found")

        return await ChoreRepository(self.db_session).create(
            self._build_chore(default_chores[0])
        )

    async def _create_many(self) -> list[Chore]:
        default_chores = await DefaultChoreRepository(
            self.db_session
        ).get_by_ids_with_translations(self.default_chore_ids)  # type: ignore

        if not default_chores:
            raise ValueError("No DefaultChores found for given ids")

        chores = [self._build_chore(dc) for dc in default_chores]
        return await ChoreRepository(self.db_session).create_chores_many(chores)

    def _build_chore(self, dc: DefaultChore) -> Chore:
        translation = next(
            (t for t in dc.translations if t.language == self.language),
            dc.translations[0] if dc.translations else None,
        )
        return Chore(
            family_id=self.family.id,
            name=translation.name if translation else "",
            description=translation.description if translation else None,
            icon=dc.icon,
            icon_color=dc.icon_color,
            icon_bg=dc.icon_bg,
            valuation=dc.valuation,
        )

    def get_validators(self):
        return [lambda: self._validate_ids_not_empty()]

    def _validate_ids_not_empty(self) -> None:
        if isinstance(self.default_chore_ids, list) and not self.default_chore_ids:
            raise ValueError("default_chore_ids cannot be empty")
