from typing import Any
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from config.setting import settings


class DatabaseSetup:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseSetup, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Construct an Database Operator with connection pooling"""
        # Configure connection pooling for better performance
        poolclass = QueuePool
        pool_pre_ping = True  # Verify connections before use
        pool_recycle = 3600  # Recycle connections after 1 hour
        max_overflow = 20  # Allow up to 20 connections beyond pool_size
        pool_size = 10  # Base pool size

        engine_kwargs = {
            "poolclass": poolclass,
            "pool_pre_ping": pool_pre_ping,
            "pool_recycle": pool_recycle,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "echo": settings.TESTING,  # Only log SQL in testing mode
        }

        if settings.TESTING:
            engine_kwargs["connect_args"] = {"check_same_thread": False}

        self._engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
        self._session_maker = sessionmaker(
            bind=self._engine, autocommit=False, autoflush=False, expire_on_commit=False
        )

        # Async engine setup for PostgreSQL
        async_engine_kwargs = {
            "echo": settings.TESTING,
            "pool_pre_ping": True,
        }
        self._async_engine = create_async_engine(
            settings.DATABASE_URL_ASYNC,
            **async_engine_kwargs
        )

        self._base = declarative_base()

    def get_session(self) -> sessionmaker:
        """Grant session

            This method returns the database
            session
        Returns:
            object: database session
        """
        return self._session_maker

    @property
    def get_base(self) -> Any:
        """Grant Base

            This method returns the
            database Base
        Returns:
            object: database base
        """
        return self._base

    @property
    def get_engine(self) -> Any:
        """Grant engine
            This method returns the
            database engine

        Returns:
            object: database engine
        """
        return self._engine


database = DatabaseSetup()
Base = database.get_base
