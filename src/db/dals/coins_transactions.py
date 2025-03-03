from dataclasses import dataclass

from core.base_dals import BaseDals
from db.models.wallet import PeerTransaction, RewardTransaction
from schemas.coins_transactions import CreatePurchaseTransaction, CreateRewardTransaction, CreateTransferTransaction
from core.constants import PeerTransactionENUM, RewardTransactionENUM


@dataclass
class PeerTransactionDAL(BaseDals):

    class Meta:
        model = PeerTransaction

    def create_purchase_transaction(self, data: CreatePurchaseTransaction) -> PeerTransaction:
        transaction_type = PeerTransactionENUM.purchase.value
        raw_data = data.model_dump()
        raw_data.update({"transaction_type": transaction_type})
        purchase_transaction = super().create(raw_data)
        return purchase_transaction

    def create_transfer_transaction(self, data: CreateTransferTransaction) -> PeerTransaction:
        transaction_type = PeerTransactionENUM.transfer.value
        raw_data = data.model_dump()
        raw_data.update({"transaction_type": transaction_type})
        transfer_transaction = super().create(raw_data)
        return transfer_transaction
    


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