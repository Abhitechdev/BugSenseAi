"""Tests for database connection and operations."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.db.url import normalize_async_database_url
from app.models.models import ErrorAnalysis


@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection works."""
    # Use a test database URL
    test_url = normalize_async_database_url("postgresql://test:test@localhost:5432/test")
    
    engine = create_async_engine(test_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Test connection
    async with async_session() as session:
        try:
            result = await session.execute(text("SELECT 1"))
        except (OSError, SQLAlchemyError) as exc:
            pytest.skip(f"PostgreSQL test database is not available locally: {exc}")
        else:
            assert result.scalar() == 1


@pytest.mark.asyncio
async def test_error_analysis_model():
    """Test ErrorAnalysis model operations."""
    # This would require a proper test database setup
    # For now, just test the model can be imported and has expected fields
    from app.models.models import ErrorAnalysis
    
    # Test model fields exist
    assert hasattr(ErrorAnalysis, 'id')
    assert hasattr(ErrorAnalysis, 'input_type')
    assert hasattr(ErrorAnalysis, 'input_text')
    assert hasattr(ErrorAnalysis, 'analysis_result')
    assert hasattr(ErrorAnalysis, 'language_detected')
    assert hasattr(ErrorAnalysis, 'created_at')


def test_database_url_normalization():
    """Test database URL normalization function."""
    from app.db.url import normalize_async_database_url
    
    # Test various input formats
    test_cases = [
        ("postgresql://user:pass@localhost:5432/db", "postgresql+asyncpg://user:pass@localhost:5432/db"),
        ("postgresql+psycopg2://user:pass@localhost:5432/db", "postgresql+asyncpg://user:pass@localhost:5432/db"),
        ("postgresql+asyncpg://user:pass@localhost:5432/db", "postgresql+asyncpg://user:pass@localhost:5432/db"),
    ]
    
    for input_url, expected in test_cases:
        result = normalize_async_database_url(input_url)
        assert result == expected
