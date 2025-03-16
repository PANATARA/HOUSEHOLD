from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.family import Family
from db.models.user import User
from schemas.families import FamilyWithMembersSchema


@dataclass
class FamilyDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_family_with_members(self, family_id: UUID) -> FamilyWithMembersSchema | None:
        """Returns a pydantic model of the family and its members"""
        result = await self.db_session.execute(
            select(
                Family.id,
                Family.name,
                Family.icon,
                func.json_agg(
                    func.json_build_object(
                        "id",User.id,
                        "username",User.username,
                        "name",User.name,
                        "surname",User.surname,
                    )
                ).label("members")
                
            )
            .join(User, Family.id == User.family_id)
            .where(Family.id == family_id)
            .group_by(Family.id)
        )

        rows = result.mappings().all()
        
        if rows is None:
            return None
        family = FamilyWithMembersSchema.model_validate(rows[0])

        return family
