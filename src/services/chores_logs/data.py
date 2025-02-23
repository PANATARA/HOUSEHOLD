from collections import defaultdict
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func


from db.models.chore import Chore, ChoreLog, ChoreLogConfirm
from db.models.user import User
from schemas.chores import ChoreShow
from schemas.chores_logs import ChoreLogConfirmation, ChoreLogDetailShow, ChoreLogShow
from schemas.users import UserResponse


@dataclass
class ChoreLogDataService:
    """Return family pydantic models"""

    db_session: AsyncSession

    async def get_family_choreslogs(
        self, family_id: UUID, offset: int, limit: int
    ) -> list[ChoreLogShow]:
        """Returns a pydantic model of the chores logs"""
        cl = aliased(ChoreLog)
        c = aliased(Chore)
        u = aliased(User)

        query = (
            select(
                cl.id.label("chorelog_id"),
                c.id.label("chore_id"),
                c.name.label("chore_name"),
                c.description.label("chore_description"),
                c.icon.label("chore_icon"),
                c.valuation.label("chore_valuation"),
                u.id.label("completed_by_id"),
                u.username.label("completed_by_username"),
                u.name.label("completed_by_name"),
                u.surname.label("completed_by_surname"),
                cl.created_at.label("chorelog_completed_at"),
                cl.message.label("chorelog_msg"),
                cl.status.label("chorelog_status"),
            )
            .join(u, cl.completed_by_id == u.id)
            .join(c, cl.chore_id == c.id)
            .where(c.family_id == family_id)
            .order_by(cl.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()
        chorelogs = [
            ChoreLogShow(
                id=data["chorelog_id"],
                completed_at=data["chorelog_completed_at"],
                message=data["chorelog_msg"],
                status=data["chorelog_status"],
                completed_by=UserResponse(
                    id=data["completed_by_id"],
                    username=data["completed_by_username"],
                    name=data["completed_by_name"],
                    surname=data["completed_by_surname"],
                ),
                chore=ChoreShow(
                    id=data["chore_id"],
                    name=data["chore_name"],
                    description=data["chore_description"],
                    icon=data["chore_icon"],
                    valuation=data["chore_valuation"],
                ),
            )
            for data in raw_data
        ]
        return chorelogs

    async def get_family_choreslog_detail(
        self, chorelog_id: UUID,
    ) -> ChoreLogDetailShow:
        confirm_user = aliased(User)

        query = (   
            select(
                ChoreLog.id.label('chorelog_id'),
                Chore.id.label('chore_id'),
                Chore.name.label('chore_name'),
                Chore.description.label('chore_description'),
                Chore.icon.label('chore_icon'),
                Chore.valuation.label('chore_valuation'),
                User.id.label('completed_by_id'),
                User.username.label('completed_by_username'),
                User.name.label('completed_by_name'),
                User.surname.label('completed_by_surname'),
                ChoreLog.created_at.label('chorelog_completed_at'),
                ChoreLog.message.label('chorelog_msg'),
                ChoreLog.status.label('chorelog_status'),
                func.json_agg(
                    func.json_build_object(
                        'id', ChoreLogConfirm.id,
                        'user', func.json_build_object(
                            'id', confirm_user.id,
                            'username', confirm_user.username,
                            'name', confirm_user.name,
                            'surname', confirm_user.surname
                        ),
                        'status', ChoreLogConfirm.status
                    )
                ).label('confirmed_by')
            )
            .join(User, ChoreLog.completed_by_id == User.id)
            .join(Chore, ChoreLog.chore_id == Chore.id)
            .join(ChoreLogConfirm, ChoreLog.id == ChoreLogConfirm.chore_log_id)
            .join(confirm_user, ChoreLogConfirm.user_id == confirm_user.id)
            .where(ChoreLog.id == chorelog_id)
            .group_by(ChoreLog.id, Chore.id, User.id)
        )

        query_result = await self.db_session.execute(query)
        item = query_result.mappings().first()

        if not item:
            return None 

        return ChoreLogDetailShow(
            id=item['chorelog_id'],
            chore=ChoreShow(
                id=item['chore_id'],
                name=item['chore_name'],
                description=item['chore_description'],
                icon=item['chore_icon'],
                valuation=item['chore_valuation']
            ),
            completed_by=UserResponse(
                id=item['completed_by_id'],
                username=item['completed_by_username'],
                name=item['completed_by_name'],
                surname=item['completed_by_surname']
            ),
            completed_at=item['chorelog_completed_at'],
            message=item['chorelog_msg'],
            status=item['chorelog_status'],
            confirmed_by=[
                ChoreLogConfirmation(
                    id=confirm['id'],
                    user=UserResponse(**confirm['user']),
                    status=confirm['status']
                )
                for confirm in item['confirmed_by']
            ]
        )

