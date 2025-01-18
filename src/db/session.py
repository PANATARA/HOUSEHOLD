from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import database

##############################################
# BLOCK FOR COMMON INTERACTION WITH DATABASE #
##############################################

# create async engine for interaction with database
engine = create_async_engine(database.REAL_DATABASE_URL, future=True, echo=True,
                             execution_options={"isolation_level": "AUTOCOMMIT"})

# create session for the interaction with database
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator:
    """Dependency for getting async session"""
    try:
        session: AsyncSession = async_session()
        yield session
    finally:
        await session.close()