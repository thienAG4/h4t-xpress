"""Import every model so `Base.metadata` is complete (Alembic, seed, tests)."""

from app.core.db import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.models import OtpCode, RefreshToken
from app.modules.dispatch.models import DispatchOffer
from app.modules.files.models import File
from app.modules.hubs.models import Area, AreaAdjacency, Hub, Shift, ShiftRegistration
from app.modules.incidents.models import (
    Incident,
    IncidentFile,
    IncidentOrder,
    IncidentResolution,
)
from app.modules.orders.models import (
    Assignment,
    DeliveryAttempt,
    DeliveryAttemptFile,
    Order,
    OrderEvent,
)
from app.modules.partner.models import Partner, WebhookDelivery
from app.modules.rbac.models import Permission, Role, RolePermission
from app.modules.realtime.models import Notification
from app.modules.reports.models import DailyDriverStat
from app.modules.routing.models import Route, RouteStop
from app.modules.settings.models import SystemSetting
from app.modules.sim.models import SimShopnowOrder, SimShopnowWebhook
from app.modules.tracking.models import DriverLocation
from app.modules.users.models import DriverProfile, User
from app.worker.models import Job

__all__ = [
    "Area",
    "AreaAdjacency",
    "Assignment",
    "AuditLog",
    "Base",
    "DailyDriverStat",
    "DeliveryAttempt",
    "DeliveryAttemptFile",
    "DispatchOffer",
    "DriverLocation",
    "DriverProfile",
    "File",
    "Hub",
    "Incident",
    "IncidentFile",
    "IncidentOrder",
    "IncidentResolution",
    "Job",
    "Notification",
    "Order",
    "OrderEvent",
    "OtpCode",
    "Partner",
    "Permission",
    "RefreshToken",
    "Role",
    "RolePermission",
    "Route",
    "RouteStop",
    "Shift",
    "ShiftRegistration",
    "SimShopnowOrder",
    "SimShopnowWebhook",
    "SystemSetting",
    "User",
    "WebhookDelivery",
]
