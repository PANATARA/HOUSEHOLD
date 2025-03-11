from dataclasses import dataclass

from core.base_dals import BaseDals
from db.models.wallet import PeerTransaction, RewardTransaction
from schemas.coins_transactions import CreateRewardTransaction
from core.constants import RewardTransactionENUM


@dataclass
class PeerTransactionDAL(BaseDals):

    class Meta:
        model = PeerTransaction    


@dataclass
class RewardTransactionDAL(BaseDals):

    class Meta:
        model = RewardTransaction
    
    def create_reward_for_chore_transaction(self, data: CreateRewardTransaction):
        transaction_type = RewardTransactionENUM.reward_for_chore.value
        raw_data = data.model_dump()
        raw_data.update({"transaction_type": transaction_type})
        reward_transaction = super().create(raw_data)
        return reward_transaction