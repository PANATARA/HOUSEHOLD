from core.base_dals import BaseDals
from db.models.product import Product


class AsyncProductDAL(BaseDals[Product]):

    model = Product