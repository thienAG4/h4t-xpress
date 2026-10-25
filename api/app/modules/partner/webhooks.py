"""Outbound partner webhooks (SPEC §3.7, BR10, BR11, EX7).

Events are written to `webhook_deliveries` in the same transaction as the order change
(transactional outbox); the worker sends them with an HMAC-SHA256 signature and retries
with backoff 1 -> 5 -> 30 minutes, at most 6 attempts.
"""

import json
import logging
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utc_now
from app.core.db import SessionLocal
from app.core.security import sign_webhook
from app.modules.orders.models import Order
from app.modules.partner.models import Partner, WebhookDelivery, WebhookStatus
from app.modules.partner.service import enqueue_webhook
from app.modules.users.models import User

logger = logging.getLogger(__name__)

DRIVER_ASSIGNED = "order.driver_assigned"
STATUS_CHANGED = "order.status_changed"
ETA_CHANGED = "order.eta_changed"
INCIDENT = "order.incident"
DELIVERED = "order.delivered"
FAILED = "order.failed"

BACKOFF = [timedelta(minutes=1), timedelta(minutes=5)] + [timedelta(minutes=30)] * 3
MAX_ATTEMPTS = 6


# =============================== Event payloads ===============================


def order_payload(order: Order, *, driver: User | None = None, **extra: Any) -> dict[str, Any]:
    """What the partner may know about an order: status, ETA, driver contact, reasons."""
    payload: dict[str, Any] = {
        "waybill_code": order.waybill_code,
        "partner_order_ref": order.partner_order_ref,
        "status": order.status.value,
        "eta": order.current_eta.isoformat() if order.current_eta else None,
        "eta_is_estimate": order.eta_degraded,
        "promised_at": order.promised_at.isoformat(),
    }
    if driver is not None:
        payload["driver"] = {"name": driver.full_name, "phone": driver.phone}
    payload.update({key: value for key, value in extra.items() if value is not None})
    return payload


def notify_partner(
    session: AsyncSession,
    order: Order,
    event_type: str,
    *,
    driver: User | None = None,
    **extra: Any,
) -> None:
    """Queue a webhook for the order's partner (committed with the caller's transaction)."""
    enqueue_webhook(
        session, order.partner_id, event_type, order_payload(order, driver=driver, **extra)
    )


# =============================== Delivery (worker) ===============================


async def deliver_pending_webhooks(
    *, client: httpx.AsyncClient | None = None, limit: int = 20
) -> int:
    """Send due webhooks. Returns how many were attempted."""
    now = utc_now()
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(WebhookDelivery, Partner)
                .join(Partner, Partner.id == WebhookDelivery.partner_id)
                .where(
                    WebhookDelivery.status == WebhookStatus.PENDING,
                    WebhookDelivery.next_attempt_at <= now,
                )
                .order_by(WebhookDelivery.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True, of=WebhookDelivery)
            )
        ).all()
        if not rows:
            return 0

        http = client or httpx.AsyncClient(timeout=5)
        try:
            for delivery, partner in rows:
                await _send_one(http, delivery, partner)
        finally:
            if client is None:
                await http.aclose()
        await session.commit()
    return len(rows)


async def _send_one(http: httpx.AsyncClient, delivery: WebhookDelivery, partner: Partner) -> None:
    body = json.dumps(delivery.payload, ensure_ascii=False, separators=(",", ":")).encode()
    headers = {
        "Content-Type": "application/json",
        "X-H4T-Event": delivery.event_type,
        "X-H4T-Delivery": str(delivery.id),
        "X-H4T-Signature": sign_webhook(body, partner.webhook_secret),
    }
    error: str | None
    try:
        response = await http.post(partner.webhook_url, content=body, headers=headers)
        error = None if 200 <= response.status_code < 300 else f"HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        error = f"{type(exc).__name__}: {exc}"[:500]

    delivery.attempts += 1
    if error is None:
        delivery.status = WebhookStatus.SENT
        delivery.sent_at = utc_now()
        delivery.last_error = None
        return
    delivery.last_error = error
    if delivery.attempts >= MAX_ATTEMPTS:
        delivery.status = WebhookStatus.FAILED
        logger.warning(
            "[deliver_webhook] %s gave up after %d attempts", delivery.id, delivery.attempts
        )
    else:
        delivery.next_attempt_at = utc_now() + BACKOFF[delivery.attempts - 1]
