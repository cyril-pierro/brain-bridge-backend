from core import setup
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession


class CreateDBSession:
    """Synchronous database session context manager"""
    def __init__(self):
        self.db_factory = setup.database.get_session()
        self.session = None

    def __enter__(self) -> Session:
        self.session = self.db_factory()
        return self.session

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.session:
            if exc_type is not None:
                self.session.rollback()
            self.session.close()


class CreateAsyncDBSession:
    """Asynchronous database session context manager"""
    def __init__(self):
        self.db_factory = setup.database._async_engine

    async def __aenter__(self) -> AsyncSession:
        self.session = AsyncSession(self.db_factory)
        return self.session

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        if self.session:
            if exc_type is not None:
                await self.session.rollback()
            await self.session.close()
