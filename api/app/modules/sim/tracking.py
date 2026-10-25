"""Customer tracking page of ShopNow (S-03, `/track/:waybill`).

Built only from the order ShopNow sent and the signed webhooks it received, so the page
shows exactly what a real partner could tell its buyer: status, new ETA, the reason of a
delay with an apology, the driver's contact and the delivery photo.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.modules.partner.webhooks import (
    DELIVERED,
    DRIVER_ASSIGNED,
    ETA_CHANGED,
    FAILED,
    INCIDENT,
)
from app.modules.sim.models import SimShopnowOrder, SimShopnowWebhook
from app.modules.sim.schemas import TrackDriverOut, TrackOut, TrackStepOut

STATUS_LABELS = {
    "AWAITING_ASSIGNMENT": "Preparing for delivery",
    "ON_HOLD": "Waiting at the hub",
    "ASSIGNED": "Driver assigned",
    "PICKED_UP": "Picked up by the driver",
    "OUT_FOR_DELIVERY": "Out for delivery",
    "DELIVERED": "Delivered",
    "DELIVERY_FAILED": "Delivery attempt failed",
    "RESCHEDULED": "Delivery rescheduled",
    "RETURNING": "Returning to the hub",
    "RETURNED_TO_HUB": "Returned to the hub",
    "CANCELLED": "Cancelled",
}
EVENT_TITLES = {
    ETA_CHANGED: "New delivery time",
    INCIDENT: "Delay on the way",
    DELIVERED: "Delivered",
    FAILED: "Delivery attempt failed",
}
CLOSED_STATUSES = {"DELIVERED", "RETURNED_TO_HUB", "CANCELLED"}


def mask_name(full_name: str) -> str:
    """Public page: keep the given name only, e.g. "Tran Thi Mai" -> "T. T. Mai"."""
    parts = full_name.split()
    if len(parts) <= 1:
        return full_name
    return " ".join(f"{part[0]}." for part in parts[:-1]) + f" {parts[-1]}"


async def track(session: AsyncSession, waybill_code: str) -> TrackOut:
    code = waybill_code.strip().upper()
    record = await session.scalar(
        select(SimShopnowOrder).where(SimShopnowOrder.waybill_code == code)
    )
    if record is None:
        raise NotFound("We could not find this waybill", code="ORDER_NOT_FOUND")
    hooks = await session.scalars(
        select(SimShopnowWebhook)
        .where(SimShopnowWebhook.waybill_code == code, SimShopnowWebhook.signature_valid.is_(True))
        .order_by(SimShopnowWebhook.received_at)
    )

    steps = [
        TrackStepOut(
            at=record.created_at,
            event="order.created",
            status="AWAITING_ASSIGNMENT",
            title="Order received",
            message="ShopNow handed your parcel to H4T Xpress.",
        )
    ]
    driver: TrackDriverOut | None = None
    proof_url: str | None = None
    delay_message: str | None = None
    estimate = False
    for hook in hooks:
        data = hook.payload
        status = data.get("status")
        title = EVENT_TITLES.get(hook.event_type) or STATUS_LABELS.get(str(status), "Update")
        if hook.event_type == DRIVER_ASSIGNED and data.get("driver"):
            driver = TrackDriverOut(name=data["driver"]["name"], phone=data["driver"].get("phone"))
            title = f"Driver assigned: {driver.name}"
        elif hook.event_type == INCIDENT:
            delay_message = data.get("message")
        elif hook.event_type == DELIVERED:
            proof_url = data.get("proof_url")
            delay_message = None
        estimate = bool(data.get("eta_is_estimate"))
        steps.append(
            TrackStepOut(
                at=hook.received_at,
                event=hook.event_type,
                status=status,
                title=title,
                message=data.get("message"),
            )
        )

    status = record.last_status or "AWAITING_ASSIGNMENT"
    promised_at = datetime.fromisoformat(record.payload["promised_at"])
    eta = record.current_eta
    is_late = eta is not None and eta > promised_at and status not in CLOSED_STATUSES
    return TrackOut(
        waybill_code=record.waybill_code,
        partner_order_ref=record.partner_order_ref,
        recipient_name=mask_name(record.payload.get("recipient_name", "")),
        delivery_address=record.payload.get("delivery_address", ""),
        status=status,
        status_label=STATUS_LABELS.get(status, status),
        promised_at=promised_at,
        eta=eta,
        eta_is_estimate=estimate,
        is_late=is_late,
        delay_message=delay_message if status not in CLOSED_STATUSES else None,
        driver=driver if status not in CLOSED_STATUSES or status == "DELIVERED" else None,
        proof_url=proof_url,
        steps=list(reversed(steps)),
    )
