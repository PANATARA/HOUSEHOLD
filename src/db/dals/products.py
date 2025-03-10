from dataclasses import dataclass

from core.base_dals import BaseDals
from db.models.product import Product

@dataclass
class AsyncProductDAL(BaseDals):

    class Meta:
        model = Product