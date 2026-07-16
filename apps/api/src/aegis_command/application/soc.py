from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from aegis_command.analytics.features import SUSPICIOUS_COMMAND_MARKERS
from aegis_command.analytics.risk import RiskPolicy
from aegis_command.analytics.runtime import DetectionRuntime
from aegis_command.application.ports import AssessmentRepository, EnforcementAdapter
from aegis_command.domain.models import (
    AccessDecision,
    AuditEntry,
    AuditPage,
    BaselineComparison,
    EnforcementStatus,
    OverviewMetrics,
    RawLogEntry,
    ResponseAction,
    RiskSeverity,
    RiskTrendPoint,
    SecurityPolicy,
    SecurityPolicyUpdate,
    SessionAction,
    SessionActionCreate,
    SessionAssessment,
    SessionEvent,
    SessionInvestigation,
    SessionListItem,
    SessionPage,
    SessionStatus,
    SessionTimelineEvent,
    SocOverview,
)


def _severity(score: float) -> RiskSeverity:
    if score >= 85:
        return RiskSeverity.CRITICAL
    if score >= 70:
        return RiskSeverity.HIGH
    if score >= 40:
        return RiskSeverity.MEDIUM
    return RiskSeverity.LOW


def _fallback_event(assessment: SessionAssessment) -> SessionEvent:
    return SessionEvent(
        event_id=assessment.event_id,
        session_id=assessment.session_id,
        user_id=assessment.user_id,
        role="privileged-user",
        occurred_at=assessment.assessed_at,
        source_ip="not-captured",
        device_id="not-captured",
        resource="protected-resource",
        resource_sensitivity=assessment.features.get("asset_sensitivity", 0.5),
        commands=["Legacy telemetry summary"],
        session_duration_minutes=1,
        privilege_level=1,
    )


def _event_for(assessment: SessionAssessment) -> SessionEvent:
    return assessment.source_event or _fallback_event(assessment)


def _status_for(
    assessment: SessionAssessment, actions: Sequence[SessionAction]
) -> SessionStatus:
    if actions:
        latest = max(actions, key=lambda item: item.acted_at)
        if latest.action is ResponseAction.BLOCK:
            if latest.enforcement_status is EnforcementStatus.SUCCEEDED:
                return SessionStatus.CONTAINED
            return SessionStatus.FLAGGED
        if latest.action is ResponseAction.STEP_UP:
            return SessionStatus.CHALLENGED
        return SessionStatus.MONITORING
    if assessment.decision is AccessDecision.BLOCK:
        return SessionStatus.FLAGGED
    if assessment.decision is AccessDecision.STEP_UP_AUTH:
        return SessionStatus.CHALLENGED
    return SessionStatus.MONITORING


def _list_item(
    assessment: SessionAssessment, actions: Sequence[SessionAction]
) -> SessionListItem:
    event = _event_for(assessment)
    return SessionListItem(
        assessment_id=assessment.assessment_id,
        session_id=assessment.session_id,
        user_id=assessment.user_id,
        role=event.role,
        started_at=event.occurred_at - timedelta(minutes=event.session_duration_minutes),
        assessed_at=assessment.assessed_at,
        resource=event.resource,
        source_ip=event.source_ip,
        risk_score=assessment.risk_score,
        severity=_severity(assessment.risk_score),
        decision=assessment.decision,
        status=_status_for(assessment, actions),
        enforcement_status=assessment.enforcement_status,
    )


def _page_bounds(page: int, page_size: int, total: int) -> tuple[int, int, int]:
    total_pages = math.ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    return start, start + page_size, total_pages


def _latest_by_session(
    assessments: Sequence[SessionAssessment],
) -> list[SessionAssessment]:
    latest: dict[str, SessionAssessment] = {}
    for assessment in assessments:
        current = latest.get(assessment.session_id)
        if current is None or assessment.assessed_at > current.assessed_at:
            latest[assessment.session_id] = assessment
    return list(latest.values())


class SocService:
    def __init__(
        self,
        *,
        repository: AssessmentRepository,
        runtime: DetectionRuntime,
        policy: RiskPolicy,
        enforcement: EnforcementAdapter,
        vault_available: bool,
        vault_algorithm: str | None,
    ) -> None:
        self._repository = repository
        self._runtime = runtime
        self._policy = policy
        self._enforcement = enforcement
        self._vault_available = vault_available
        self._vault_algorithm = vault_algorithm

    async def overview(self) -> SocOverview:
        now = datetime.now(UTC)
        assessments = list(await self._repository.list_recent(5_000))
        actions = list(await self._repository.list_actions(limit=5_000))
        action_map: defaultdict[str, list[SessionAction]] = defaultdict(list)
        for action in actions:
            action_map[action.session_id].append(action)
        recent = _latest_by_session(
            [item for item in assessments if item.assessed_at >= now - timedelta(hours=24)]
        )
        items = [_list_item(item, action_map[item.session_id]) for item in recent]
        top_sessions = sorted(items, key=lambda item: item.risk_score, reverse=True)[:5]
        buckets: defaultdict[datetime, list[float]] = defaultdict(list)
        for item in recent:
            timestamp = item.assessed_at.replace(minute=0, second=0, microsecond=0)
            buckets[timestamp].append(item.risk_score)
        trend = [
            RiskTrendPoint(
                timestamp=timestamp,
                average_risk=round(sum(scores) / len(scores), 2),
                count=len(scores),
            )
            for timestamp, scores in sorted(buckets.items())
        ]
        flagged_statuses = {SessionStatus.FLAGGED, SessionStatus.CHALLENGED}
        metrics = OverviewMetrics(
            active_flags=sum(item.status in flagged_statuses for item in items),
            sessions_monitored_24h=len(recent),
            average_risk_score=(
                round(sum(item.risk_score for item in recent) / len(recent), 2)
                if recent
                else 0
            ),
            escalation_count=sum(
                item.decision in {AccessDecision.STEP_UP_AUTH, AccessDecision.BLOCK}
                for item in recent
            ),
            vault_status="QUANTUM_SAFE" if self._vault_available else "DEGRADED",
            vault_algorithm=self._vault_algorithm,
        )
        return SocOverview(
            generated_at=now,
            metrics=metrics,
            risk_trend=trend,
            top_sessions=top_sessions,
        )

    async def list_sessions(
        self,
        *,
        user: str | None,
        resource: str | None,
        min_risk: float | None,
        max_risk: float | None,
        decision: AccessDecision | None,
        status: SessionStatus | None,
        date_from: datetime | None,
        date_to: datetime | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> SessionPage:
        assessments = _latest_by_session(await self._repository.list_recent(10_000))
        actions = list(await self._repository.list_actions(limit=10_000))
        action_map: defaultdict[str, list[SessionAction]] = defaultdict(list)
        for action in actions:
            action_map[action.session_id].append(action)
        items = [_list_item(item, action_map[item.session_id]) for item in assessments]
        if user:
            needle = user.casefold()
            items = [
                item
                for item in items
                if needle in item.user_id.casefold() or needle in item.session_id.casefold()
            ]
        if resource:
            needle = resource.casefold()
            items = [item for item in items if needle in item.resource.casefold()]
        if min_risk is not None:
            items = [item for item in items if item.risk_score >= min_risk]
        if max_risk is not None:
            items = [item for item in items if item.risk_score <= max_risk]
        if decision is not None:
            items = [item for item in items if item.decision is decision]
        if status is not None:
            items = [item for item in items if item.status is status]
        if date_from is not None:
            items = [item for item in items if item.assessed_at >= date_from]
        if date_to is not None:
            items = [item for item in items if item.assessed_at <= date_to]
        sorters = {
            "risk_desc": (lambda item: item.risk_score, True),
            "risk_asc": (lambda item: item.risk_score, False),
            "recent": (lambda item: item.assessed_at, True),
            "oldest": (lambda item: item.assessed_at, False),
            "user_asc": (lambda item: item.user_id.casefold(), False),
            "user_desc": (lambda item: item.user_id.casefold(), True),
            "resource_asc": (lambda item: item.resource.casefold(), False),
            "resource_desc": (lambda item: item.resource.casefold(), True),
            "status_asc": (lambda item: item.status.value, False),
            "status_desc": (lambda item: item.status.value, True),
        }
        sort_key, reverse = sorters[sort]
        items.sort(key=sort_key, reverse=reverse)
        total = len(items)
        start, end, total_pages = _page_bounds(page, page_size, total)
        return SessionPage(
            items=items[start:end],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def investigation(self, session_id: str) -> SessionInvestigation | None:
        assessments = await self._repository.list_recent(10_000)
        matches = [item for item in assessments if item.session_id == session_id]
        if not matches:
            return None
        assessment = max(matches, key=lambda item: item.assessed_at)
        event = _event_for(assessment)
        actions = list(await self._repository.list_actions(session_id=session_id))
        reviews = list(await self._repository.list_reviews(assessment.assessment_id))
        started_at = event.occurred_at - timedelta(minutes=event.session_duration_minutes)
        return SessionInvestigation(
            assessment_id=assessment.assessment_id,
            session_id=assessment.session_id,
            user_id=assessment.user_id,
            role=event.role,
            started_at=started_at,
            ended_at=event.occurred_at,
            assessed_at=assessment.assessed_at,
            resource=event.resource,
            source_ip=event.source_ip,
            device_id=event.device_id,
            risk_score=assessment.risk_score,
            severity=_severity(assessment.risk_score),
            decision=assessment.decision,
            status=_status_for(assessment, actions),
            enforcement_status=assessment.enforcement_status,
            timeline=self._timeline(assessment, event, actions, started_at),
            baseline=self._baseline(event),
            risk_factors=assessment.factors,
            raw_logs=self._raw_logs(event, started_at),
            reviews=reviews,
            actions=actions,
        )

    async def respond(
        self, session_id: str, actor: str, body: SessionActionCreate
    ) -> SessionAction | None:
        assessments = await self._repository.list_recent(10_000)
        matches = [item for item in assessments if item.session_id == session_id]
        if not matches:
            return None
        assessment = max(matches, key=lambda item: item.assessed_at)
        decision = {
            ResponseAction.ALLOW: AccessDecision.ALLOW,
            ResponseAction.STEP_UP: AccessDecision.STEP_UP_AUTH,
            ResponseAction.BLOCK: AccessDecision.BLOCK,
        }[body.action]
        action_id = uuid4()
        result = await self._enforcement.enforce(
            assessment.model_copy(update={"decision": decision, "event_id": action_id})
        )
        return await self._repository.save_action(
            SessionAction(
                action_id=action_id,
                assessment_id=assessment.assessment_id,
                session_id=session_id,
                action=body.action,
                actor=actor,
                note=body.note,
                enforcement_status=result.status,
                enforcement_reference=result.reference,
                enforcement_error=result.error,
            )
        )

    async def get_policy(self) -> SecurityPolicy:
        policy = await self._repository.get_policy()
        if policy is None:
            policy = await self._repository.save_policy(
                SecurityPolicy(
                    step_up_threshold=self._policy.step_up_threshold,
                    block_threshold=self._policy.block_threshold,
                )
            )
        return policy

    async def update_policy(
        self, body: SecurityPolicyUpdate, actor: str
    ) -> SecurityPolicy:
        current = await self.get_policy()
        policy = SecurityPolicy(
            step_up_threshold=body.step_up_threshold,
            block_threshold=body.block_threshold,
            version=current.version + 1,
            updated_by=actor,
        )
        saved = await self._repository.save_policy(policy)
        self._policy.configure(
            step_up_threshold=saved.step_up_threshold,
            block_threshold=saved.block_threshold,
        )
        return saved

    async def audit(
        self,
        *,
        session_id: str | None,
        action: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        page_size: int,
    ) -> AuditPage:
        assessments = list(await self._repository.list_recent(10_000))
        actions = list(await self._repository.list_actions(limit=10_000))
        assessment_map = {item.assessment_id: item for item in assessments}
        entries = [
            AuditEntry(
                id=f"assessment:{item.assessment_id}",
                timestamp=item.assessed_at,
                session_id=item.session_id,
                assessment_id=item.assessment_id,
                event_type="RISK_DECISION",
                action=item.decision.value,
                actor="aegis-command-risk-engine",
                risk_score=item.risk_score,
                detail=f"{len(item.factors)} signals evaluated using {item.model_version}",
                status=item.enforcement_status.value,
            )
            for item in assessments
        ]
        entries.extend(
            AuditEntry(
                id=f"response:{item.action_id}",
                timestamp=item.acted_at,
                session_id=item.session_id,
                assessment_id=item.assessment_id,
                event_type="ANALYST_RESPONSE",
                action=item.action.value,
                actor=item.actor,
                risk_score=(
                    assessment_map[item.assessment_id].risk_score
                    if item.assessment_id in assessment_map
                    else 0
                ),
                detail=item.note,
                status=item.enforcement_status.value,
            )
            for item in actions
        )
        if session_id:
            needle = session_id.casefold()
            entries = [item for item in entries if needle in item.session_id.casefold()]
        if action:
            needle = action.casefold()
            entries = [item for item in entries if needle in item.action.casefold()]
        if date_from is not None:
            entries = [item for item in entries if item.timestamp >= date_from]
        if date_to is not None:
            entries = [item for item in entries if item.timestamp <= date_to]
        entries.sort(key=lambda item: item.timestamp, reverse=True)
        total = len(entries)
        start, end, total_pages = _page_bounds(page, page_size, total)
        return AuditPage(
            items=entries[start:end],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    def _baseline(self, event: SessionEvent) -> list[BaselineComparison]:
        profile = self._runtime.baseline.resolve(event)
        action_rate = len(event.commands) / event.session_duration_minutes
        typical_hour = math.atan2(profile.hour_sin, profile.hour_cos) / (2 * math.pi) * 24
        typical_hour %= 24
        comparisons = [
            ("Session duration", profile.duration_mean, event.session_duration_minutes, "min"),
            ("Command rate", profile.action_rate_mean, action_rate, "commands/min"),
            (
                "Source familiarity",
                100.0,
                100.0 if event.source_ip in profile.source_ips else 0.0,
                "%",
            ),
            (
                "Device familiarity",
                100.0,
                100.0 if event.device_id in profile.device_ids else 0.0,
                "%",
            ),
            ("Login hour", typical_hour, float(event.occurred_at.hour), "UTC hour"),
        ]
        return [
            BaselineComparison(
                metric=metric,
                baseline=round(baseline, 2),
                actual=round(actual, 2),
                unit=unit,
                deviation_percent=round(abs(actual - baseline) / max(abs(baseline), 1) * 100, 2),
            )
            for metric, baseline, actual, unit in comparisons
        ]

    @staticmethod
    def _timeline(
        assessment: SessionAssessment,
        event: SessionEvent,
        actions: Sequence[SessionAction],
        started_at: datetime,
    ) -> list[SessionTimelineEvent]:
        events = [
            SessionTimelineEvent(
                timestamp=started_at,
                kind="AUTHENTICATION",
                title="Privileged session opened",
                detail=f"{event.user_id} connected from {event.source_ip} on {event.device_id}",
                severity=RiskSeverity.LOW,
            )
        ]
        interval = event.session_duration_minutes * 60 / max(len(event.commands) + 1, 1)
        for index, command in enumerate(event.commands, start=1):
            suspicious = any(marker in command.casefold() for marker in SUSPICIOUS_COMMAND_MARKERS)
            events.append(
                SessionTimelineEvent(
                    timestamp=started_at + timedelta(seconds=interval * index),
                    kind="COMMAND",
                    title="Suspicious command" if suspicious else "Command observed",
                    detail=command,
                    severity=RiskSeverity.HIGH if suspicious else RiskSeverity.LOW,
                )
            )
        if event.privilege_escalated:
            events.append(
                SessionTimelineEvent(
                    timestamp=event.occurred_at - timedelta(seconds=1),
                    kind="PRIVILEGE_ESCALATION",
                    title="Privilege escalation detected",
                    detail=f"Effective privilege level increased to {event.privilege_level}",
                    severity=RiskSeverity.CRITICAL,
                )
            )
        events.append(
            SessionTimelineEvent(
                timestamp=assessment.assessed_at,
                kind="RISK_DECISION",
                title=f"Risk engine recommended {assessment.decision.value}",
                detail=f"Explainable risk score {assessment.risk_score:.0f}/100",
                severity=_severity(assessment.risk_score),
            )
        )
        events.extend(
            SessionTimelineEvent(
                timestamp=action.acted_at,
                kind="ANALYST_RESPONSE",
                title=f"Analyst selected {action.action.value}",
                detail=action.note,
                severity=(
                    RiskSeverity.HIGH
                    if action.action is ResponseAction.BLOCK
                    else RiskSeverity.MEDIUM
                ),
            )
            for action in actions
        )
        return sorted(events, key=lambda item: item.timestamp)

    @staticmethod
    def _raw_logs(event: SessionEvent, started_at: datetime) -> list[RawLogEntry]:
        entries = [
            RawLogEntry(
                timestamp=started_at,
                event_type="session.open",
                message="Privileged access session established",
                metadata={
                    "user_id": event.user_id,
                    "role": event.role,
                    "source_ip": event.source_ip,
                    "device_id": event.device_id,
                    "resource": event.resource,
                },
            )
        ]
        interval = event.session_duration_minutes * 60 / max(len(event.commands) + 1, 1)
        entries.extend(
            RawLogEntry(
                timestamp=started_at + timedelta(seconds=interval * index),
                event_type="process.command",
                message=command,
                metadata={"sequence": index, "privilege_level": event.privilege_level},
            )
            for index, command in enumerate(event.commands, start=1)
        )
        entries.append(
            RawLogEntry(
                timestamp=event.occurred_at,
                event_type="session.summary",
                message="Session telemetry normalized for behavioral analysis",
                metadata={
                    "duration_minutes": event.session_duration_minutes,
                    "failed_auth_attempts": event.failed_auth_attempts,
                    "bytes_transferred": event.bytes_transferred,
                    "privilege_escalated": event.privilege_escalated,
                },
            )
        )
        return entries
