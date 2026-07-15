from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Float, String, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from finspark.application.ports import AssessmentRepository
from finspark.domain.models import SessionAssessment


class Base(DeclarativeBase):
    pass


class AssessmentRecord(Base):
    __tablename__ = "assessments"

    assessment_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


async def create_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session


class SqlAssessmentRepository(AssessmentRepository):
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def save(self, assessment: SessionAssessment) -> None:
        record = AssessmentRecord(
            assessment_id=str(assessment.assessment_id),
            session_id=assessment.session_id,
            user_id=assessment.user_id,
            assessed_at=assessment.assessed_at,
            risk_score=assessment.risk_score,
            decision=assessment.decision.value,
            payload=assessment.model_dump(mode="json"),
        )
        async with self._factory.begin() as session:
            session.add(record)

    async def list_recent(self, limit: int = 50) -> Sequence[SessionAssessment]:
        statement = (
            select(AssessmentRecord).order_by(AssessmentRecord.assessed_at.desc()).limit(limit)
        )
        async with self._factory() as session:
            records = (await session.scalars(statement)).all()
        return [SessionAssessment.model_validate(record.payload) for record in records]

    async def get(self, assessment_id: UUID) -> SessionAssessment | None:
        async with self._factory() as session:
            record = await session.get(AssessmentRecord, str(assessment_id))
        return SessionAssessment.model_validate(record.payload) if record else None


class InMemoryAssessmentRepository(AssessmentRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, SessionAssessment] = {}

    async def save(self, assessment: SessionAssessment) -> None:
        self._items[assessment.assessment_id] = assessment

    async def list_recent(self, limit: int = 50) -> Sequence[SessionAssessment]:
        return sorted(self._items.values(), key=lambda item: item.assessed_at, reverse=True)[:limit]

    async def get(self, assessment_id: UUID) -> SessionAssessment | None:
        return self._items.get(assessment_id)


def utc_now() -> datetime:
    return datetime.now(UTC)
