import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class BaseModel:
	"""FIELDS:
	- primary_key : UUID
	- created_at : datetime
	- updated_at : datetime
	
	"""
	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	created_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())"),
    )
	updated_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())"),
        onupdate=datetime.now(timezone.utc),
    )