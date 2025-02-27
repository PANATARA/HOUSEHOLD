from uuid import UUID
from fastapi import Depends
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.actions import oauth2_scheme
from core.security import get_user_id_from_token
from db.models import User
from db.models.chore import Chore, ChoreCompletion
from db.session import get_db
from core.exceptions import permission_denided

async def get_user_and_check_chore_completion_permission(
        chore_completion_id: UUID,  token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    
    user_id: UUID = get_user_id_from_token(token)
    async with db.begin():
        query = (
            select(User)
            .where(
                User.id == user_id,
                exists().where(
                    (ChoreCompletion.id == chore_completion_id) & 
                    (ChoreCompletion.chore_id == Chore.id) & 
                    (User.family_id == Chore.family_id)
                )
            )
        )
        
        result = await db.execute(query)
        user = result.fetchone()
        
        if user is not None:
            return user[0]
        else:
            raise permission_denided