from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from core.services import BaseService
from db.dals.wallets import AsyncWalletDAL
from db.models.user import User
from db.models.wallet import Wallet

@dataclass
class WalletCreatorService(BaseService):
    """Create and return a new User's wallet"""
    user: User | UUID
    db_session: AsyncSession

    async def __post_init__(self):
        if isinstance(self.user, User):
            self.user_id = self.user.id

    async def execute(self) -> Wallet:
        wallet = await self._create_wallet()
        return wallet
    
    async def _create_wallet(self) -> Wallet:
        wallet_dal = AsyncWalletDAL(self.db_session)
        wallet = await wallet_dal.create_wallet(self.user.id)
        return wallet
    
    async def validate(self):
        wallet_dal = AsyncWalletDAL(self.db_session)
        if await wallet_dal.exist_wallet_user(self.user_id):
            await wallet_dal.delete_wallet_user(self.user_id)
        
