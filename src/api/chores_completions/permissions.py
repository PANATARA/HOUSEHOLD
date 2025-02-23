from uuid import UUID
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_user_id_from_token, oauth2_scheme
from db.models import User
from db.models.chore import Chore, ChoreCompletion
from db.session import get_db
from core.exceptions import permission_denided

async def get_user_and_check_chore_completion_permission(
        chore_completion_id: UUID,  token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User | HTTPException:
    
    user_id: UUID = get_user_id_from_token(token)
    async with db.begin():
        query = (
            select(User)
            .where(
                User.id == user_id,
                User.family_id == Chore.family_id
            )
            .join(ChoreCompletion, ChoreCompletion.id == chore_completion_id)
            .join(Chore, Chore.id == ChoreCompletion.chore_id)
        )
        
        result = await db.execute(query)
        user = result.fetchone()
        
        if user is not None:
            return user[0]
        else:
            raise permission_denided