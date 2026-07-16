from aegis_command.core import Settings


def test_railway_postgres_url_uses_asyncpg_driver() -> None:
    settings = Settings(database_url="postgres://user:secret@postgres.internal:5432/aegis")

    assert settings.database_url == (
        "postgresql+asyncpg://user:secret@postgres.internal:5432/aegis"
    )


def test_standard_postgresql_url_uses_asyncpg_driver() -> None:
    settings = Settings(database_url="postgresql://user:secret@localhost:5432/aegis")

    assert settings.database_url == "postgresql+asyncpg://user:secret@localhost:5432/aegis"


def test_native_async_and_sqlite_urls_are_unchanged() -> None:
    async_url = "postgresql+asyncpg://user:secret@localhost:5432/aegis"
    sqlite_url = "sqlite+aiosqlite:///./aegis-command.db"

    assert Settings(database_url=async_url).database_url == async_url
    assert Settings(database_url=sqlite_url).database_url == sqlite_url
