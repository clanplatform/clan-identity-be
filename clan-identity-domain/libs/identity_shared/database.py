"""Shared database utilities."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
import os


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class DatabaseManager:
    """Database connection manager."""
    
    def __init__(self, database_url: str):
        self.engine = create_async_engine(
            database_url,
            echo=os.getenv("ENVIRONMENT") == "development",
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        async with self.async_session_maker() as session:
            yield session
    
    async def close(self):
        """Close database connections."""
        await self.engine.dispose()
