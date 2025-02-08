import uuid
from dataclasses import dataclass
from sqlalchemy import select

from core.base_dals import BaseDals
from db.models.family import Family, FamilySettings
from db.models.user import User



@dataclass
class AsyncFamilySettingsDAL(BaseDals):

    class Meta:
        model = FamilySettings

    async def get_settings_field(self, family_id: uuid.UUID, field: str) -> any:
        result = await self.db_session.execute(
            select(
                FamilySettings.field,
            )
            .where(FamilySettings.family_id == family_id)
        )

        rows = result.mappings().fetchone()

        if not rows:
            return None
        return rows[field]
