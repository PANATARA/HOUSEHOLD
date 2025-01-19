from sqlalchemy.orm import  DeclarativeBase


class Base(DeclarativeBase):
	pass

# Models import
from db.models import *  # noqa