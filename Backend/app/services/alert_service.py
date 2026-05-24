from datetime import datetime, timedelta, timezone
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertIncident, AlertRule
from app.repositories.alert_repository import AlertIncidentRepository, AlertRuleRepository
from app.repositories.event_repository import EventRepository
from app.services.notification_service import NotificationService


class AlertService:
    OPERATORS = {
        "gt": lambda v, t: v > t,
        "lt": lambda v, t: v < t,
        "gte": lambda v, t: v >= t,
        "lte": lambda v, t: v <= t,
    }

    def __init__(self, session: AsyncSession, redis_client: aioredis.Redis | None = None) -> None:
        self.session = session
        self.rule_repo = AlertRuleRepository(session)
        self.incident_repo = AlertIncidentRepository(session)
        self.event_repo = EventRepository(session)
        self.notifications = NotificationService(session, redis_client)

    async def create(
        self, organization_id: UUID, user_id: UUID, data
    ):
        from app.schemas.alert import AlertRuleResponse

        rule = AlertRule(
            organization_id=organization_id,
            name=data.name,
            description=data.description,
            event_name=data.event_name,
            metric=data.metric,
            operator=data.operator,
            threshold=data.threshold,
            window_minutes=data.window_minutes,
            notification_channels=data.notification_channels.model_dump(),
            created_by=user_id,
            status="active",
        )
        self.session.add(rule)
        await self.session.flush()
        return AlertRuleResponse.model_validate(rule)

    async def list(self, organization_id: UUID, params):
        from app.schemas.alert import AlertRuleResponse

        result = await self.rule_repo.list_by_org(organization_id, params)
        return type(result)(
            items=[AlertRuleResponse.model_validate(r) for r in result.items],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

    async def get(self, organization_id: UUID, rule_id: UUID):
        from app.core.exceptions import NotFoundError
        from app.schemas.alert import AlertRuleResponse

        rule = await self.rule_repo.get_for_org(rule_id, organization_id)
        if not rule:
            raise NotFoundError("Alert rule not found")
        return AlertRuleResponse.model_validate(rule)

    async def update(self, organization_id: UUID, rule_id: UUID, data):
        from app.core.exceptions import NotFoundError
        from app.schemas.alert import AlertRuleResponse

        rule = await self.rule_repo.get_for_org(rule_id, organization_id)
        if not rule:
            raise NotFoundError("Alert rule not found")
        updates = data.model_dump(exclude_unset=True)
        if "notification_channels" in updates and updates["notification_channels"] is not None:
            channels = updates["notification_channels"]
            if hasattr(channels, "model_dump"):
                updates["notification_channels"] = channels.model_dump()
        for key, value in updates.items():
            setattr(rule, key, value)
        await self.session.flush()
        return AlertRuleResponse.model_validate(rule)

    async def delete(self, organization_id: UUID, rule_id: UUID) -> None:
        from app.core.exceptions import NotFoundError

        rule = await self.rule_repo.get_for_org(rule_id, organization_id)
        if not rule:
            raise NotFoundError("Alert rule not found")
        await self.rule_repo.soft_delete(rule)

    async def mute(self, organization_id: UUID, rule_id: UUID, minutes: int):
        from app.core.exceptions import NotFoundError
        from app.schemas.alert import AlertRuleResponse

        rule = await self.rule_repo.get_for_org(rule_id, organization_id)
        if not rule:
            raise NotFoundError("Alert rule not found")
        rule.status = "muted"
        rule.muted_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await self.session.flush()
        return AlertRuleResponse.model_validate(rule)

    async def unmute(self, organization_id: UUID, rule_id: UUID):
        from app.core.exceptions import NotFoundError
        from app.schemas.alert import AlertRuleResponse

        rule = await self.rule_repo.get_for_org(rule_id, organization_id)
        if not rule:
            raise NotFoundError("Alert rule not found")
        rule.status = "active"
        rule.muted_until = None
        await self.session.flush()
        return AlertRuleResponse.model_validate(rule)

    async def list_incidents(self, organization_id: UUID, rule_id: UUID, params):
        from app.core.exceptions import NotFoundError
        from app.schemas.alert import AlertIncidentResponse

        rule = await self.rule_repo.get_for_org(rule_id, organization_id)
        if not rule:
            raise NotFoundError("Alert rule not found")
        result = await self.incident_repo.list_by_rule(rule_id, params)
        return type(result)(
            items=[AlertIncidentResponse.model_validate(i) for i in result.items],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

    async def evaluate_rule(self, rule: AlertRule) -> None:
        now = datetime.now(timezone.utc)
        if rule.muted_until and rule.muted_until > now:
            return

        start = now - timedelta(minutes=rule.window_minutes)
        value = await self.event_repo.aggregate_total(
            rule.organization_id, rule.event_name, start, now
        )
        rule.last_value = value
        op_fn = self.OPERATORS.get(rule.operator, self.OPERATORS["gt"])
        breached = op_fn(value, rule.threshold)
        open_incident = await self.incident_repo.get_open_for_rule(rule.id)

        if breached:
            if not open_incident:
                incident = AlertIncident(
                    alert_rule_id=rule.id,
                    organization_id=rule.organization_id,
                    status="triggered",
                    triggered_value=value,
                    triggered_at=now,
                )
                self.session.add(incident)
                await self.session.flush()
                rule.status = "triggered"
                rule.last_triggered_at = now
                await self.notifications.notify_alert_triggered(rule, value, incident.id)
        elif open_incident and rule.status == "triggered":
            open_incident.status = "resolved"
            open_incident.resolved_at = now
            rule.status = "resolved"
            await self.notifications.notify_alert_resolved(rule, value, open_incident.id)
            rule.status = "active"

        await self.session.flush()

    async def evaluate_all(self) -> int:
        rules = await self.rule_repo.list_evaluable()
        for rule in rules:
            await self.evaluate_rule(rule)
        return len(rules)
