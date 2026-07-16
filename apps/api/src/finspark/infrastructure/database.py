from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from finspark.application.ports import AssessmentRepository
from finspark.domain.models import (
    AssessmentReview,
    SecurityPolicy,
    SessionAction,
    SessionAssessment,
)


class Base(DeclarativeBase):
    pass


class AssessmentRecord(Base):
    __tablename__ = "assessments"

    assessment_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)


class AssessmentReviewRecord(Base):
    __tablename__ = "assessment_reviews"

    review_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessments.assessment_id", ondelete="CASCADE"), index=True
    )
    reviewer: Mapped[str] = mapped_column(String(128), index=True)
    disposition: Mapped[str] = mapped_column(String(32), index=True)
    comment: Mapped[str] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)


class SessionActionRecord(Base):
    __tablename__ = "session_actions"

    action_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessments.assessment_id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    actor: Mapped[str] = mapped_column(String(128), index=True)
    action: Mapped[str] = mapped_column(String(32), index=True)
    acted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)


class SecurityPolicyRecord(Base):
    __tablename__ = "security_policy"

    policy_key: Mapped[str] = mapped_column(String(64), primary_key=True)
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

    async def save(self, assessment: SessionAssessment) -> SessionAssessment:
        existing = await self.get_by_event_id(assessment.event_id)
        if existing is not None and existing.assessment_id != assessment.assessment_id:
            return existing
        record = AssessmentRecord(
            assessment_id=str(assessment.assessment_id),
            event_id=str(assessment.event_id),
            session_id=assessment.session_id,
            user_id=assessment.user_id,
            assessed_at=assessment.assessed_at,
            risk_score=assessment.risk_score,
            decision=assessment.decision.value,
            payload=assessment.model_dump(mode="json"),
        )
        async with self._factory() as session:
            await session.merge(record)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                concurrent = await self.get_by_event_id(assessment.event_id)
                if concurrent is not None:
                    return concurrent
                raise
        return assessment

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

    async def get_by_event_id(self, event_id: UUID) -> SessionAssessment | None:
        statement = select(AssessmentRecord).where(AssessmentRecord.event_id == str(event_id))
        async with self._factory() as session:
            record = await session.scalar(statement)
        return SessionAssessment.model_validate(record.payload) if record else None

    async def save_review(self, review: AssessmentReview) -> AssessmentReview:
        record = AssessmentReviewRecord(
            review_id=str(review.review_id),
            assessment_id=str(review.assessment_id),
            reviewer=review.reviewer,
            disposition=review.disposition.value,
            comment=review.comment,
            reviewed_at=review.reviewed_at,
            payload=review.model_dump(mode="json"),
        )
        async with self._factory.begin() as session:
            session.add(record)
        return review

    async def list_reviews(self, assessment_id: UUID) -> Sequence[AssessmentReview]:
        statement = (
            select(AssessmentReviewRecord)
            .where(AssessmentReviewRecord.assessment_id == str(assessment_id))
            .order_by(AssessmentReviewRecord.reviewed_at.desc())
        )
        async with self._factory() as session:
            records = (await session.scalars(statement)).all()
        return [AssessmentReview.model_validate(record.payload) for record in records]

    async def save_action(self, action: SessionAction) -> SessionAction:
        record = SessionActionRecord(
            action_id=str(action.action_id),
            assessment_id=str(action.assessment_id),
            session_id=action.session_id,
            actor=action.actor,
            action=action.action.value,
            acted_at=action.acted_at,
            payload=action.model_dump(mode="json"),
        )
        async with self._factory.begin() as session:
            session.add(record)
        return action

    async def list_actions(
        self, session_id: str | None = None, limit: int = 5_000
    ) -> Sequence[SessionAction]:
        statement = select(SessionActionRecord).order_by(
            SessionActionRecord.acted_at.desc()
        )
        if session_id is not None:
            statement = statement.where(SessionActionRecord.session_id == session_id)
        statement = statement.limit(limit)
        async with self._factory() as session:
            records = (await session.scalars(statement)).all()
        return [SessionAction.model_validate(record.payload) for record in records]

    async def get_policy(self) -> SecurityPolicy | None:
        async with self._factory() as session:
            record = await session.get(SecurityPolicyRecord, "default")
        return SecurityPolicy.model_validate(record.payload) if record else None

    async def save_policy(self, policy: SecurityPolicy) -> SecurityPolicy:
        record = SecurityPolicyRecord(
            policy_key="default",
            payload=policy.model_dump(mode="json"),
        )
        async with self._factory.begin() as session:
            await session.merge(record)
        return policy

    async def ping(self) -> bool:
        try:
            async with self._factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


class InMemoryAssessmentRepository(AssessmentRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, SessionAssessment] = {}
        self._event_index: dict[UUID, UUID] = {}
        self._reviews: dict[UUID, list[AssessmentReview]] = {}
        self._actions: list[SessionAction] = []
        self._policy: SecurityPolicy | None = None

    async def save(self, assessment: SessionAssessment) -> SessionAssessment:
        existing_id = self._event_index.get(assessment.event_id)
        if existing_id is not None and existing_id != assessment.assessment_id:
            return self._items[existing_id]
        self._items[assessment.assessment_id] = assessment
        self._event_index[assessment.event_id] = assessment.assessment_id
        return assessment

    async def list_recent(self, limit: int = 50) -> Sequence[SessionAssessment]:
        return sorted(self._items.values(), key=lambda item: item.assessed_at, reverse=True)[:limit]

    async def get(self, assessment_id: UUID) -> SessionAssessment | None:
        return self._items.get(assessment_id)

    async def get_by_event_id(self, event_id: UUID) -> SessionAssessment | None:
        assessment_id = self._event_index.get(event_id)
        return self._items.get(assessment_id) if assessment_id else None

    async def save_review(self, review: AssessmentReview) -> AssessmentReview:
        self._reviews.setdefault(review.assessment_id, []).append(review)
        return review

    async def list_reviews(self, assessment_id: UUID) -> Sequence[AssessmentReview]:
        return sorted(
            self._reviews.get(assessment_id, []),
            key=lambda review: review.reviewed_at,
            reverse=True,
        )

    async def save_action(self, action: SessionAction) -> SessionAction:
        self._actions.append(action)
        return action

    async def list_actions(
        self, session_id: str | None = None, limit: int = 5_000
    ) -> Sequence[SessionAction]:
        actions = self._actions
        if session_id is not None:
            actions = [item for item in actions if item.session_id == session_id]
        return sorted(actions, key=lambda item: item.acted_at, reverse=True)[:limit]

    async def get_policy(self) -> SecurityPolicy | None:
        return self._policy

    async def save_policy(self, policy: SecurityPolicy) -> SecurityPolicy:
        self._policy = policy
        return policy


def utc_now() -> datetime:
    return datetime.now(UTC)
