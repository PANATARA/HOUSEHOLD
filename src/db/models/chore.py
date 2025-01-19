import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base_model import BaseModel
from db.models.declarative_base import Base


class Chore(Base, BaseModel):
    __tablename__ = "family_chore"

    name: Mapped[str]
    description: Mapped[str]
    icon: Mapped[str]
    valuation: Mapped[int]
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="family.id", 
            ondelete="CASCADE",
        )
    )
    logs: Mapped["ChoreLog"] = relationship("ChoreLog", back_populates="chore")

    def __repr__(self):
        return super().__repr__()
    

class ChoreLog(Base, BaseModel):
    __tablename__ = "family_chore_log"

    message: Mapped[str]
    completed_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="users.id", 
            ondelete="SET NULL",
        )
    )
    chore_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            column="family_chore.id", 
            ondelete="CASCADE",
        )
    )
    chore: Mapped["Chore"] = relationship("Chore", back_populates="logs")
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="chore_log") # type: ignore
    completed_by: Mapped["User"] = relationship("User", back_populates="chore_logs")  # type: ignore
    
    def __repr__(self):
        return super().__repr__()
