from uuid import UUID
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.auth_actions import oauth2_scheme
from core.security import decode_jwt_token
from db.dals.users import AsyncUserDAL
from db.models import User
from db.session import get_db
from core.exceptions import permission_denided

async def get_user_and_check_is_family_admin(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    
    payload = decode_jwt_token(token)

    user_id: UUID = payload.get("sub")
    user_is_family_admin: bool = payload.get("is_family_admin")
    if not user_is_family_admin:
        raise permission_denided
    
    async with db.begin():
        user_dal = AsyncUserDAL(db)
        user =  await user_dal.get_by_id(user_id)
    return user
    