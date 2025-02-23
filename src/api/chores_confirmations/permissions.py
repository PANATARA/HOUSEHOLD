from uuid import UUID
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import get_user_id_from_token, oauth2_scheme
from db.models import User
from db.models.chore import Chore, ChoreLog, ChoreLogConfirm
from db.session import get_db
from core.exceptions import permission_denided

async def get_user_and_check_confirm_chorelog_permission(
        confirm_chorlog_id: UUID,  token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User | HTTPException:
    
    user_id: UUID = get_user_id_from_token(token)
    async with db.begin():
        query = (
            select(User)
            .join(ChoreLogConfirm, ChoreLogConfirm.user_id == User.id)
            .where(
                User.id == user_id, 
                ChoreLogConfirm.id == confirm_chorlog_id
            )
        )
        
        result = await db.execute(query)
        user = result.fetchone()
        
        if user is not None:
            return user[0]
        else:
            raise permission_denided