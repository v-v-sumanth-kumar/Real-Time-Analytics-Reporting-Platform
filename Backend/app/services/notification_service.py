import json
from uuid import UUID

import httpx
import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.alert import AlertRule, InAppNotification
from app.repositories.alert_repository import NotificationRepository
from app.schemas.alert import NotificationResponse
from app.utils.pagination import PaginatedResult, PaginationParams

logger = structlog.get_logger(__name__)


class NotificationService:
    def __init__(self, session: AsyncSession, redis_client: aioredis.Redis | None = None) -> None:
        self.session = session
        self.redis = redis_client
        self.repo = NotificationRepository(session)
        self.settings = get_settings()

    async def list(
        self, organization_id: UUID, user_id: UUID, params: PaginationParams
    ) -> PaginatedResult[NotificationResponse]:
        result = await self.repo.list_for_org(organization_id, user_id, params)
        return PaginatedResult(
            items=[NotificationResponse.model_validate(n) for n in result.items],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

    async def mark_read(self, notification_id: UUID, organization_id: UUID):
        return await self.repo.mark_read(notification_id, organization_id)

    async def notify_alert_triggered(
        self, rule: AlertRule, value: float, incident_id: UUID
    ) -> None:
        channels = rule.notification_channels or {}
        title = f"Alert triggered: {rule.name}"
        message = (
            f"{rule.metric} {rule.operator} {rule.threshold} "
            f"(current: {value:.2f}, window: {rule.window_minutes}m)"
        )
        payload = {
            "alert_rule_id": str(rule.id),
            "incident_id": str(incident_id),
            "value": value,
            "status": "triggered",
        }
        await self._deliver(rule, channels, title, message, payload, "alert.triggered")

    async def notify_alert_resolved(
        self, rule: AlertRule, value: float, incident_id: UUID
    ) -> None:
        channels = rule.notification_channels or {}
        title = f"Alert resolved: {rule.name}"
        message = f"Metric returned to normal (current: {value:.2f})"
        payload = {
            "alert_rule_id": str(rule.id),
            "incident_id": str(incident_id),
            "value": value,
            "status": "resolved",
        }
        await self._deliver(rule, channels, title, message, payload, "alert.resolved")

    async def _deliver(
        self,
        rule: AlertRule,
        channels: dict,
        title: str,
        message: str,
        payload: dict,
        event_type: str,
    ) -> None:
        if channels.get("in_app", True):
            self.session.add(
                InAppNotification(
                    organization_id=rule.organization_id,
                    type=event_type,
                    title=title,
                    message=message,
                    payload=payload,
                )
            )
            await self.session.flush()

        if channels.get("email") and self.settings.smtp_host:
            await self._send_email(title, message, channels.get("email_to"))

        webhook_url = channels.get("webhook_url")
        if webhook_url:
            await self._send_webhook(webhook_url, {
                "text": message,
                "alert": rule.name,
                "value": payload.get("value"),
                "status": payload.get("status"),
            })

        await self._publish_ws(rule.organization_id, {
            "type": event_type,
            "payload": payload,
            "title": title,
            "message": message,
        })

    async def _send_email(self, subject: str, body: str, to: str | None) -> None:
        if not to:
            logger.info("email_skipped_no_recipient", subject=subject)
            return
        logger.info("email_sent_stub", to=to, subject=subject, body=body)

    async def _send_webhook(self, url: str, payload: dict) -> None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json=payload)
        except Exception as e:
            logger.warning("webhook_delivery_failed", url=url, error=str(e))

    async def _publish_ws(self, organization_id: UUID, message: dict) -> None:
        if not self.redis:
            return
        await self.redis.publish(
            f"org:{organization_id}:events",
            json.dumps(message),
        )
