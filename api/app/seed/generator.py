"""Builds every demo row in memory (deterministic for a given random seed and date).

History is simulated order by order so that events, assignments, offers, attempts,
incidents and daily stats stay consistent with each other and with the state machine.
"""

import math
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.core.db import Base
from app.core.security import hash_password, hash_token
from app.modules.dispatch.models import DispatchOffer, OfferSource, OfferStatus
from app.modules.hubs.models import (
    Area,
    AreaAdjacency,
    Hub,
    Shift,
    ShiftCode,
    ShiftRegistration,
    ShiftRegistrationStatus,
)
from app.modules.incidents.models import (
    Incident,
    IncidentCategory,
    IncidentOrder,
    IncidentPriority,
    IncidentResolution,
    IncidentSource,
    IncidentStatus,
    ResolutionSolution,
    ResolutionStatus,
)
from app.modules.orders.models import (
    ActorType,
    Assignment,
    AssignmentLeg,
    AssignmentStatus,
    AttemptOutcome,
    DeliveryAttempt,
    EtaSource,
    FailureReason,
    Order,
    OrderEvent,
    OrderEventType,
    OrderPriority,
    OrderStatus,
)
from app.modules.partner.models import Partner, PartnerStatus
from app.modules.rbac.models import Permission, Role, RoleCode, RolePermission
from app.modules.reports.models import DailyDriverStat
from app.modules.routing.models import Route, RouteStatus, RouteStop, StopStatus
from app.modules.settings.models import SystemSetting
from app.modules.sim.models import SimShopnowOrder, SimShopnowWebhook
from app.modules.users.models import DriverAvailability, DriverProfile, Gender, User, UserStatus
from app.seed import catalog

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
SLA_GRACE = timedelta(minutes=120)
# Drivers 3 to 5 of every hub are already on the road today (maps, route planning, GPS).
BUSY_POSITIONS = (2, 3, 4)
HISTORY_OFFER_TIMEOUT = timedelta(minutes=10)

Row = dict[str, Any]


@dataclass
class AreaInfo:
    id: uuid.UUID
    seed: catalog.AreaSeed


@dataclass
class HubInfo:
    id: uuid.UUID
    seed: catalog.HubSeed
    manager_id: uuid.UUID | None = None


@dataclass
class DriverInfo:
    id: uuid.UUID
    hub_code: str
    skill: float  # probability that an attempt succeeds
    incident_rate: float


def minutes(value: float) -> timedelta:
    return timedelta(minutes=value)


class DemoDataBuilder:
    def __init__(
        self,
        *,
        now: datetime,
        history_days: int,
        random_seed: int,
        demo_mode: bool,
        demo_password: str,
        shopnow_api_key: str,
        shopnow_webhook_secret: str,
        shopnow_webhook_url: str,
    ) -> None:
        self.rng = random.Random(random_seed)
        self.now = now.astimezone(UTC)
        self.today = self.now.astimezone(TZ).date()
        self.history_days = history_days
        self.demo_mode = demo_mode
        self.demo_password = demo_password
        self.shopnow_api_key = shopnow_api_key
        self.shopnow_webhook_secret = shopnow_webhook_secret
        self.shopnow_webhook_url = shopnow_webhook_url

        self.rows: dict[type[Base], list[Row]] = defaultdict(list)
        self.role_ids: dict[RoleCode, uuid.UUID] = {}
        self.areas: dict[str, AreaInfo] = {}
        self.neighbors: dict[str, list[str]] = defaultdict(list)
        self.hubs: dict[str, HubInfo] = {}
        self.shift_ids: dict[tuple[str, ShiftCode], uuid.UUID] = {}
        self.drivers_by_hub: dict[str, list[DriverInfo]] = defaultdict(list)
        self.partner_id: uuid.UUID | None = None

        self._waybill_seq: dict[date, int] = defaultdict(int)
        self._active_assignment: dict[uuid.UUID, Row] = {}
        self._stats: dict[tuple[uuid.UUID, date], dict[str, int]] = defaultdict(
            lambda: {"assigned": 0, "delivered": 0, "failed": 0, "on_time": 0, "incidents": 0}
        )
        self._driver_hub: dict[uuid.UUID, str] = {}
        self._profiles: dict[uuid.UUID, Row] = {}

    # ------------------------------------------------------------------ helpers

    def uid(self) -> uuid.UUID:
        return uuid.UUID(int=self.rng.getrandbits(128), version=4)

    def add(self, model: type[Base], row: Row) -> Row:
        self.rows[model].append(row)
        return row

    def local(self, day: date, hour: int, minute: int = 0) -> datetime:
        return datetime.combine(day, time(hour, minute), TZ).astimezone(UTC)

    def random_point(self, lat: float, lng: float, radius_km: float) -> tuple[float, float]:
        distance = radius_km * math.sqrt(self.rng.random())
        angle = self.rng.uniform(0, 2 * math.pi)
        d_lat = distance * math.cos(angle) / 111.0
        d_lng = distance * math.sin(angle) / (111.0 * math.cos(math.radians(lat)))
        return round(lat + d_lat, 6), round(lng + d_lng, 6)

    def person(self, male_ratio: float = 0.5) -> tuple[str, Gender]:
        surname = self.rng.choice(catalog.SURNAMES)
        if self.rng.random() < male_ratio:
            middle = self.rng.choice(catalog.MALE_MIDDLE)
            given = self.rng.choice(catalog.MALE_GIVEN)
            return f"{surname} {middle} {given}", Gender.MALE
        middle = self.rng.choice(catalog.FEMALE_MIDDLE)
        given = self.rng.choice(catalog.FEMALE_GIVEN)
        return f"{surname} {middle} {given}", Gender.FEMALE

    def address_in(self, area_code: str) -> tuple[str, float, float]:
        area = self.areas[area_code].seed
        lat, lng = self.random_point(area.lat, area.lng, area.radius_km)
        street = self.rng.choice(area.streets)
        return f"{self.rng.randint(1, 350)} {street}, P. {area.ward}, TP.HCM", lat, lng

    @staticmethod
    def fake_phone(prefix: str, number: int) -> str:
        # 012x prefixes were retired in 2018, so these numbers cannot belong to real people.
        return f"{prefix}{number:06d}"

    # -------------------------------------------------------------- entry point

    def build(self) -> dict[type[Base], list[Row]]:
        self._reference_data()
        self._people()
        self._partner()
        self._shift_registrations()
        self._history()
        self._orders_today()
        self._routes_today()
        self._daily_stats()
        return self.rows

    # ---------------------------------------------------------- reference data

    def _reference_data(self) -> None:
        for role_code, name, description in catalog.ROLES:
            role_id = self.uid()
            self.role_ids[role_code] = role_id
            self.add(
                Role,
                {
                    "id": role_id,
                    "code": role_code.value,
                    "name": name,
                    "description": description,
                    "is_system": True,
                },
            )

        permission_ids: dict[str, uuid.UUID] = {}
        for code, group, description in catalog.PERMISSIONS:
            permission_ids[code] = self.uid()
            self.add(
                Permission,
                {
                    "id": permission_ids[code],
                    "code": code,
                    "group": group,
                    "description": description,
                },
            )
        for granted_role, permission_codes in catalog.DEFAULT_ROLE_PERMISSIONS.items():
            for permission_code in permission_codes:
                self.add(
                    RolePermission,
                    {
                        "role_id": self.role_ids[granted_role],
                        "permission_id": permission_ids[permission_code],
                    },
                )

        for area in catalog.AREAS:
            area_info = AreaInfo(self.uid(), area)
            self.areas[area.code] = area_info
            self.add(
                Area,
                {
                    "id": area_info.id,
                    "code": area.code,
                    "name": area.name,
                    "center_lat": area.lat,
                    "center_lng": area.lng,
                    "radius_km": area.radius_km,
                },
            )
        for a, b in catalog.AREA_ADJACENCY:
            self.neighbors[a].append(b)
            self.neighbors[b].append(a)
            for left, right in ((a, b), (b, a)):
                self.add(
                    AreaAdjacency,
                    {"area_id": self.areas[left].id, "neighbor_area_id": self.areas[right].id},
                )

        for hub in catalog.HUBS:
            hub_info = HubInfo(self.uid(), hub)
            self.hubs[hub.code] = hub_info
            self.add(
                Hub,
                {
                    "id": hub_info.id,
                    "code": hub.code,
                    "name": hub.name,
                    "address": hub.address,
                    "lat": hub.lat,
                    "lng": hub.lng,
                    "area_id": self.areas[hub.area_code].id,
                },
            )
            for shift_code, name, start, end, capacity in catalog.SHIFTS:
                shift_id = self.uid()
                self.shift_ids[(hub.code, shift_code)] = shift_id
                self.add(
                    Shift,
                    {
                        "id": shift_id,
                        "hub_id": hub_info.id,
                        "code": shift_code,
                        "name": name,
                        "start_time": start,
                        "end_time": end,
                        "capacity": capacity,
                        "is_active": True,
                    },
                )

        for key, value, description in catalog.default_settings(self.demo_mode):
            self.add(SystemSetting, {"key": key, "value": value, "description": description})

    # ------------------------------------------------------------------ people

    def _user(
        self,
        *,
        role: RoleCode,
        email: str,
        phone: str,
        hub_id: uuid.UUID | None,
        male_ratio: float,
        address: str | None = None,
    ) -> uuid.UUID:
        user_id = self.uid()
        name, gender = self.person(male_ratio)
        self.add(
            User,
            {
                "id": user_id,
                "full_name": name,
                "email": email,
                "phone": phone,
                "password_hash": hash_password(self.demo_password),
                "role_id": self.role_ids[role],
                "hub_id": hub_id,
                "national_id": f"079{self.rng.randint(0, 999_999_999):09d}",
                "gender": gender,
                "address": address,
                "status": UserStatus.ACTIVE,
                "last_login_at": None,
                "created_at": self.now - timedelta(days=self.history_days + 30),
                "updated_at": self.now - timedelta(days=self.history_days + 30),
            },
        )
        return user_id

    def _people(self) -> None:
        self._user(
            role=RoleCode.SYSTEM_ADMIN,
            email="admin@demo.h4t",
            phone=self.fake_phone("0120", 301),
            hub_id=None,
            male_ratio=0.5,
        )
        self._user(
            role=RoleCode.EXECUTIVE,
            email="exec@demo.h4t",
            phone=self.fake_phone("0120", 201),
            hub_id=None,
            male_ratio=0.5,
        )
        for index, hub in enumerate(self.hubs.values(), start=1):
            hub.manager_id = self._user(
                role=RoleCode.HUB_MANAGER,
                email=hub.seed.manager_email,
                phone=self.fake_phone("0120", 100 + index),
                hub_id=hub.id,
                male_ratio=0.5,
            )

        number = 0
        for hub in self.hubs.values():
            for _ in range(catalog.DRIVERS_PER_HUB):
                number += 1
                address, _, _ = self.address_in(hub.seed.area_code)
                driver_id = self._user(
                    role=RoleCode.DRIVER,
                    email=f"driver{number}@demo.h4t",
                    phone=self.fake_phone("0120", number),
                    hub_id=hub.id,
                    male_ratio=0.85,
                    address=address,
                )
                last_lat, last_lng = self.random_point(hub.seed.lat, hub.seed.lng, 1.5)
                letter = self.rng.choice("ABCDEFGHKLMNPSTUVX")
                self._profiles[driver_id] = self.add(
                    DriverProfile,
                    {
                        "user_id": driver_id,
                        "vehicle_plate": (
                            f"59{letter}{self.rng.randint(1, 9)}-"
                            f"{self.rng.randint(100, 999)}.{self.rng.randint(10, 99)}"
                        ),
                        "license_no": f"79{self.rng.randint(0, 9_999_999_999):010d}",
                        "home_area_id": self.areas[hub.seed.area_code].id,
                        "availability": DriverAvailability.OFFLINE,
                        "rating": Decimal(str(round(self.rng.uniform(4.2, 5.0), 2))),
                        "last_lat": last_lat,
                        "last_lng": last_lng,
                        "last_seen_at": None,
                    },
                )
                info = DriverInfo(
                    id=driver_id,
                    hub_code=hub.seed.code,
                    skill=self.rng.uniform(0.86, 0.97),
                    incident_rate=self.rng.uniform(0.03, 0.09),
                )
                self.drivers_by_hub[hub.seed.code].append(info)
                self._driver_hub[driver_id] = hub.seed.code

    def _partner(self) -> None:
        self.partner_id = self.uid()
        self.add(
            Partner,
            {
                "id": self.partner_id,
                "code": "SHOPNOW",
                "name": "ShopNow",
                "api_key_hash": hash_token(self.shopnow_api_key),
                "webhook_url": self.shopnow_webhook_url,
                "webhook_secret": self.shopnow_webhook_secret,
                "status": PartnerStatus.ACTIVE,
            },
        )

    def _shift_registrations(self) -> None:
        """Most drivers have registered for today and the next two days (UC-01)."""
        taken: dict[tuple[str, ShiftCode, date], int] = defaultdict(int)
        capacity = {code: cap for code, _, _, _, cap in catalog.SHIFTS}
        for offset in range(3):
            work_date = self.today + timedelta(days=offset)
            for hub_code, drivers in self.drivers_by_hub.items():
                for position, driver in enumerate(drivers):
                    # driver1 and driver2 (first two of the first hub) always work full days,
                    # so the demo script with two driver windows works on any day.
                    is_demo_pair = hub_code == catalog.HUBS[0].code and position < 2
                    on_road_today = offset == 0 and position in BUSY_POSITIONS
                    if not (is_demo_pair or on_road_today) and self.rng.random() > 0.85:
                        continue
                    preferred = (
                        ShiftCode.FULL_DAY
                        if is_demo_pair or on_road_today
                        else self.rng.choices(
                            [ShiftCode.MORNING, ShiftCode.AFTERNOON, ShiftCode.FULL_DAY],
                            weights=[35, 30, 35],
                        )[0]
                    )
                    if taken[(hub_code, preferred, work_date)] >= capacity[preferred]:
                        continue
                    taken[(hub_code, preferred, work_date)] += 1
                    self.add(
                        ShiftRegistration,
                        {
                            "id": self.uid(),
                            "driver_id": driver.id,
                            "shift_id": self.shift_ids[(hub_code, preferred)],
                            "work_date": work_date,
                            "status": ShiftRegistrationStatus.REGISTERED,
                            "cancelled_at": None,
                            "created_at": self.now - minutes(self.rng.randint(60, 4320)),
                        },
                    )

    # ----------------------------------------------------------------- orders

    def _new_order(
        self, hub: HubInfo, day: date, created: datetime, promised: datetime, express: bool
    ) -> Row:
        area_code = hub.seed.area_code
        if self.rng.random() > 0.8 and self.neighbors[area_code]:
            area_code = self.rng.choice(self.neighbors[area_code])
        address, lat, lng = self.address_in(area_code)
        self._waybill_seq[day] += 1
        recipient, _ = self.person()
        items = [
            {"name": self.rng.choice(catalog.PRODUCTS), "qty": self.rng.randint(1, 3)}
            for _ in range(self.rng.choices([1, 2, 3], weights=[70, 22, 8])[0])
        ]
        cod = 0 if self.rng.random() < 0.35 else self.rng.randrange(50_000, 2_000_000, 1_000)
        assert self.partner_id is not None
        return self.add(
            Order,
            {
                "id": self.uid(),
                "partner_id": self.partner_id,
                "waybill_code": f"SN{day:%y%m%d}{self._waybill_seq[day]:05d}",
                "partner_order_ref": f"SN-ORD-{self.rng.randint(10_000_000, 99_999_999)}",
                "hub_id": hub.id,
                "status": OrderStatus.AWAITING_ASSIGNMENT,
                "priority": OrderPriority.EXPRESS if express else OrderPriority.NORMAL,
                "recipient_name": recipient,
                "recipient_phone": self.fake_phone("0123", self.rng.randint(0, 999_999)),
                "delivery_address": address,
                "delivery_lat": lat,
                "delivery_lng": lng,
                "delivery_area_id": self.areas[area_code].id,
                "weight_kg": Decimal(str(round(self.rng.uniform(0.2, 12.0), 2))),
                "length_cm": Decimal(str(round(self.rng.uniform(10, 60), 1))),
                "width_cm": Decimal(str(round(self.rng.uniform(10, 40), 1))),
                "height_cm": Decimal(str(round(self.rng.uniform(5, 40), 1))),
                "cod_amount": Decimal(cod),
                "items": items,
                "note": None,
                "promised_at": promised,
                "current_eta": None,
                "eta_source": None,
                "eta_degraded": False,
                "current_driver_id": None,
                "route_stop_id": None,
                "handover_from_driver_id": None,
                "active_incident_id": None,
                "delivered_at": None,
                "cancelled_at": None,
                "failed_attempts": 0,
                "created_at": created,
                "updated_at": created,
            },
        )

    def _event(
        self,
        order: Row,
        at: datetime,
        from_status: OrderStatus | None,
        to_status: OrderStatus | None,
        actor_type: ActorType,
        actor: uuid.UUID | None = None,
        *,
        event_type: OrderEventType = OrderEventType.STATUS_CHANGED,
        lat: float | None = None,
        lng: float | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.add(
            OrderEvent,
            {
                "id": self.uid(),
                "order_id": order["id"],
                "type": event_type,
                "from_status": from_status,
                "to_status": to_status,
                "actor_user_id": actor,
                "actor_type": actor_type,
                "lat": lat,
                "lng": lng,
                "payload": payload or {},
                "created_at": at,
            },
        )
        if to_status is not None:
            order["status"] = to_status
        order["updated_at"] = max(order["updated_at"], at)

    def _stat(self, driver_id: uuid.UUID, at: datetime) -> dict[str, int]:
        return self._stats[(driver_id, at.astimezone(TZ).date())]

    def _offers(
        self,
        order: Row,
        accepted: DriverInfo,
        pool: list[DriverInfo],
        accepted_at: datetime,
        round_no: int,
        source: OfferSource = OfferSource.AUTO,
    ) -> None:
        """Sequential offers that end with `accepted` saying yes at `accepted_at` (BR6-BR8)."""
        others = [driver for driver in pool if driver.id != accepted.id]
        refused = self.rng.sample(
            others, k=min(len(others), self.rng.choices([0, 1, 2], weights=[70, 22, 8])[0])
        )
        if source is OfferSource.MANUAL:
            refused = []
        timeline: list[tuple[DriverInfo, OfferStatus, timedelta]] = []
        for driver in refused:
            if self.rng.random() < 0.6:
                timeline.append((driver, OfferStatus.DECLINED, minutes(self.rng.uniform(0.5, 3))))
            else:
                timeline.append((driver, OfferStatus.EXPIRED, HISTORY_OFFER_TIMEOUT))
        timeline.append((accepted, OfferStatus.ACCEPTED, minutes(self.rng.uniform(0.3, 4))))

        offered_at = accepted_at - sum((duration for _, _, duration in timeline), timedelta())
        score = self.rng.uniform(82, 95)
        for rank, (driver, status, duration) in enumerate(timeline, start=1):
            responded_at = offered_at + duration
            self.add(
                DispatchOffer,
                {
                    "id": self.uid(),
                    "order_id": order["id"],
                    "driver_id": driver.id,
                    "round": round_no,
                    "rank": rank,
                    "score": Decimal(str(round(score, 2))),
                    "score_breakdown": {
                        "distance": round(self.rng.uniform(0.5, 1.0), 3),
                        "load": round(self.rng.uniform(0.4, 1.0), 3),
                        "performance": round(driver.skill, 3),
                        "time_fit": round(self.rng.uniform(0.7, 1.0), 3),
                    },
                    "source": source,
                    "status": status,
                    "offered_at": offered_at,
                    "expires_at": offered_at + HISTORY_OFFER_TIMEOUT,
                    "responded_at": None if status is OfferStatus.EXPIRED else responded_at,
                    "decline_reason": "Too far from my route"
                    if status is OfferStatus.DECLINED
                    else None,
                    "created_at": offered_at,
                },
            )
            offered_at = responded_at
            score -= self.rng.uniform(2, 7)

    def _assign(self, order: Row, driver: DriverInfo, at: datetime) -> None:
        row = self.add(
            Assignment,
            {
                "id": self.uid(),
                "order_id": order["id"],
                "driver_id": driver.id,
                "leg": AssignmentLeg.DELIVERY,
                "status": AssignmentStatus.ACTIVE,
                "assigned_at": at,
                "ended_at": None,
                "end_reason": None,
                "created_at": at,
            },
        )
        self._active_assignment[order["id"]] = row
        order["current_driver_id"] = driver.id
        self._event(
            order,
            at,
            OrderStatus.AWAITING_ASSIGNMENT,
            OrderStatus.ASSIGNED,
            ActorType.SYSTEM,
            event_type=OrderEventType.ASSIGNED,
            payload={"driver_id": str(driver.id)},
        )
        self._stat(driver.id, at)["assigned"] += 1

    def _end_assignment(
        self, order: Row, at: datetime, status: AssignmentStatus, reason: str | None = None
    ) -> None:
        row = self._active_assignment.pop(order["id"])
        row["status"] = status
        row["ended_at"] = at
        row["end_reason"] = reason

    def _pickup_and_go(self, order: Row, driver: DriverInfo, assigned_at: datetime) -> datetime:
        """ASSIGNED -> PICKED_UP (scan at hub) -> OUT_FOR_DELIVERY. Returns departure time."""
        hub = self.hubs[driver.hub_code].seed
        picked = assigned_at + minutes(self.rng.randint(10, 40))
        self._event(
            order,
            picked,
            OrderStatus.ASSIGNED,
            OrderStatus.PICKED_UP,
            ActorType.USER,
            driver.id,
            lat=hub.lat,
            lng=hub.lng,
        )
        out = picked + minutes(self.rng.randint(5, 20))
        self._event(
            order,
            out,
            OrderStatus.PICKED_UP,
            OrderStatus.OUT_FOR_DELIVERY,
            ActorType.USER,
            driver.id,
        )
        return out

    def _attempt(
        self,
        order: Row,
        driver: DriverInfo,
        at: datetime,
        *,
        success: bool,
        proposed_date: date | None = None,
    ) -> None:
        lat, lng = self.random_point(order["delivery_lat"], order["delivery_lng"], 0.05)
        reason: FailureReason | None = None
        note: str | None = None
        if not success:
            reasons = catalog.FAILURE_REASONS
            reason, _, note = self.rng.choices(reasons, weights=[w for _, w, _ in reasons])[0]
        self.add(
            DeliveryAttempt,
            {
                "id": self.uid(),
                "order_id": order["id"],
                "driver_id": driver.id,
                "outcome": AttemptOutcome.DELIVERED if success else AttemptOutcome.FAILED,
                "failure_reason": reason,
                "note": note,
                "proposed_reschedule_date": proposed_date,
                "lat": lat,
                "lng": lng,
                "attempted_at": at,
                "created_at": at,
            },
        )
        order["current_eta"] = at
        order["eta_source"] = EtaSource.SYSTEM
        stat = self._stat(driver.id, at)
        if success:
            self._event(
                order,
                at,
                OrderStatus.OUT_FOR_DELIVERY,
                OrderStatus.DELIVERED,
                ActorType.USER,
                driver.id,
                lat=lat,
                lng=lng,
            )
            order["delivered_at"] = at
            stat["delivered"] += 1
            if at <= order["promised_at"] + SLA_GRACE:
                stat["on_time"] += 1
            self._end_assignment(order, at, AssignmentStatus.COMPLETED)
        else:
            assert reason is not None
            self._event(
                order,
                at,
                OrderStatus.OUT_FOR_DELIVERY,
                OrderStatus.DELIVERY_FAILED,
                ActorType.USER,
                driver.id,
                lat=lat,
                lng=lng,
                payload={"reason": reason.value},
            )
            order["failed_attempts"] += 1
            stat["failed"] += 1
            self._end_assignment(order, at, AssignmentStatus.COMPLETED, f"Failed: {reason.value}")

    def _return_to_hub(self, order: Row, hub: HubInfo, at: datetime) -> None:
        self._event(
            order,
            at + minutes(10),
            OrderStatus.DELIVERY_FAILED,
            OrderStatus.RETURNING,
            ActorType.SYSTEM,
        )
        self._event(
            order,
            at + minutes(self.rng.randint(60, 180)),
            OrderStatus.RETURNING,
            OrderStatus.RETURNED_TO_HUB,
            ActorType.USER,
            hub.manager_id,
        )

    def _incident(
        self, order: Row, hub: HubInfo, driver: DriverInfo, pool: list[DriverInfo], at: datetime
    ) -> tuple[DriverInfo, datetime]:
        """Driver reports an incident; the hub resolves it. Returns (driver, resume time)."""
        profiles = catalog.INCIDENT_PROFILES
        incident_type, _, category, descriptions = self.rng.choices(
            profiles, weights=[weight for _, weight, _, _ in profiles]
        )[0]
        express = order["priority"] is OrderPriority.EXPRESS
        if express or (category is IncidentCategory.SUBJECTIVE and self.rng.random() < 0.5):
            priority = IncidentPriority.HIGH
        else:
            priority = self.rng.choice([IncidentPriority.MEDIUM, IncidentPriority.LOW])
        classified = at + minutes(self.rng.randint(2, 10))
        resolved = classified + minutes(self.rng.randint(3, 15))
        lat, lng = self.random_point(order["delivery_lat"], order["delivery_lng"], 1.5)
        incident_id = self.uid()
        assert hub.manager_id is not None
        self.add(
            Incident,
            {
                "id": incident_id,
                "hub_id": hub.id,
                "driver_id": driver.id,
                "type": incident_type,
                "source": IncidentSource.DRIVER,
                "description": self.rng.choice(descriptions),
                "lat": lat,
                "lng": lng,
                "suggested_category": category,
                "category": category,
                "priority": priority,
                "status": IncidentStatus.RESOLVED,
                "hub_response": self.rng.choice(catalog.HUB_RESPONSES[category]),
                "handled_by": hub.manager_id,
                "reported_at": at,
                "classified_at": classified,
                "resolved_at": resolved,
                "created_at": at,
                "updated_at": resolved,
            },
        )
        self.add(IncidentOrder, {"incident_id": incident_id, "order_id": order["id"]})
        self._stat(driver.id, at)["incidents"] += 1
        self._event(
            order,
            at,
            None,
            None,
            ActorType.USER,
            driver.id,
            event_type=OrderEventType.INCIDENT,
            lat=lat,
            lng=lng,
            payload={"incident_id": str(incident_id), "type": incident_type.value},
        )

        if category is IncidentCategory.OBJECTIVE:
            delay = self.rng.uniform(20, 90)
            self._resolution(incident_id, ResolutionSolution.ROUTE_SUGGESTED, hub, resolved)
            self._event(
                order,
                resolved,
                None,
                None,
                ActorType.SYSTEM,
                event_type=OrderEventType.ETA_CHANGED,
                payload={"delay_min": round(delay), "reason": incident_type.value},
            )
            return driver, at + minutes(delay)

        # Subjective: hand the order over to another driver of the same hub (UC-04).
        replacement = self.rng.choice([d for d in pool if d.id != driver.id])
        self._resolution(
            incident_id, ResolutionSolution.DRIVER_REASSIGNMENT, hub, resolved, replacement.id
        )
        self._end_assignment(
            order, resolved, AssignmentStatus.REASSIGNED, f"Incident {incident_type.value}"
        )
        self._event(
            order,
            resolved,
            OrderStatus.OUT_FOR_DELIVERY,
            OrderStatus.AWAITING_ASSIGNMENT,
            ActorType.USER,
            hub.manager_id,
            payload={"incident_id": str(incident_id), "handover_from": str(driver.id)},
        )
        accepted = resolved + minutes(self.rng.randint(2, 6))
        self._offers(order, replacement, pool, accepted, round_no=1, source=OfferSource.MANUAL)
        self._assign(order, replacement, accepted)
        order["handover_from_driver_id"] = driver.id
        handover = accepted + minutes(self.rng.randint(20, 45))
        self._event(
            order,
            handover,
            OrderStatus.ASSIGNED,
            OrderStatus.PICKED_UP,
            ActorType.USER,
            replacement.id,
            lat=lat,
            lng=lng,
            payload={"handover_from": str(driver.id)},
        )
        out = handover + minutes(self.rng.randint(2, 5))
        self._event(
            order,
            out,
            OrderStatus.PICKED_UP,
            OrderStatus.OUT_FOR_DELIVERY,
            ActorType.USER,
            replacement.id,
        )
        return replacement, out

    def _resolution(
        self,
        incident_id: uuid.UUID,
        solution: ResolutionSolution,
        hub: HubInfo,
        at: datetime,
        new_driver_id: uuid.UUID | None = None,
    ) -> None:
        assert hub.manager_id is not None
        self.add(
            IncidentResolution,
            {
                "id": self.uid(),
                "incident_id": incident_id,
                "solution": solution,
                "new_driver_id": new_driver_id,
                "route_snapshot": {"reordered": True}
                if solution is ResolutionSolution.ROUTE_SUGGESTED
                else None,
                "status": ResolutionStatus.DONE,
                "note": None,
                "decided_by": hub.manager_id,
                "decided_at": at,
                "created_at": at,
                "updated_at": at,
            },
        )

    # ----------------------------------------------------------------- history

    def _history(self) -> None:
        for offset in range(self.history_days, 0, -1):
            day = self.today - timedelta(days=offset)
            # Volume grows slowly over the period so charts show a trend.
            growth = 1 - offset / max(self.history_days, 1)
            for hub in self.hubs.values():
                count = self.rng.randint(9, 14) + round(3 * growth)
                if day.weekday() >= 5:
                    count = max(5, round(count * 0.8))
                drivers = self.drivers_by_hub[hub.seed.code]
                on_duty = self.rng.sample(drivers, k=self.rng.randint(6, min(9, len(drivers))))
                for _ in range(count):
                    self._history_order(day, hub, on_duty)

    def _history_order(self, day: date, hub: HubInfo, on_duty: list[DriverInfo]) -> None:
        rng = self.rng
        created = self.local(day, 6) + minutes(rng.randint(0, 240))
        express = rng.random() < 0.15
        promised = created + timedelta(hours=rng.uniform(4, 6) if express else rng.uniform(7, 10))
        order = self._new_order(hub, day, created, promised, express)
        self._event(order, created, None, OrderStatus.AWAITING_ASSIGNMENT, ActorType.PARTNER)

        if rng.random() < 0.02:
            cancelled = created + minutes(rng.randint(20, 120))
            order["cancelled_at"] = cancelled
            self._event(
                order,
                cancelled,
                OrderStatus.AWAITING_ASSIGNMENT,
                OrderStatus.CANCELLED,
                ActorType.PARTNER,
                payload={"reason": "Cancelled by buyer"},
            )
            return

        # Usually assigned quickly; sometimes the hub has a backlog (late orders).
        wait = rng.uniform(180, 420) if rng.random() < 0.1 else rng.expovariate(1 / 25)
        driver = rng.choice(on_duty)
        assigned = created + minutes(5 + wait)
        self._offers(order, driver, on_duty, assigned, round_no=1)
        self._assign(order, driver, assigned)
        out = self._pickup_and_go(order, driver, assigned)

        travel = min(max(rng.gauss(90, 45), 15), 300)
        if rng.random() < driver.incident_rate:
            progress = rng.uniform(0.2, 0.7)
            driver, resume = self._incident(
                order, hub, driver, on_duty, out + minutes(travel * progress)
            )
            arrive = resume + minutes(travel * (1 - progress))
        else:
            arrive = out + minutes(travel)

        if rng.random() < driver.skill:
            self._attempt(order, driver, arrive, success=True)
            return

        next_day = day + timedelta(days=1)
        reschedule = next_day < self.today and rng.random() < 0.7
        self._attempt(
            order, driver, arrive, success=False, proposed_date=next_day if reschedule else None
        )
        if not reschedule:
            self._return_to_hub(order, hub, arrive)
            return

        self._event(
            order,
            arrive + minutes(5),
            OrderStatus.DELIVERY_FAILED,
            OrderStatus.RESCHEDULED,
            ActorType.SYSTEM,
            payload={"reschedule_date": next_day.isoformat()},
        )
        released = self.local(next_day, 7, 30) + minutes(rng.randint(0, 90))
        self._event(
            order,
            released,
            OrderStatus.RESCHEDULED,
            OrderStatus.AWAITING_ASSIGNMENT,
            ActorType.SYSTEM,
        )
        pool = self.drivers_by_hub[hub.seed.code]
        retry_driver = driver if rng.random() < 0.5 else rng.choice(pool)
        assigned = released + minutes(rng.randint(5, 40))
        self._offers(order, retry_driver, pool, assigned, round_no=1)
        self._assign(order, retry_driver, assigned)
        out = self._pickup_and_go(order, retry_driver, assigned)
        arrive = out + minutes(min(max(rng.gauss(80, 40), 15), 240))
        if rng.random() < 0.85:
            self._attempt(order, retry_driver, arrive, success=True)
        else:
            self._attempt(order, retry_driver, arrive, success=False)
            self._return_to_hub(order, hub, arrive)

    # ------------------------------------------------------------------- today

    def _orders_today(self) -> None:
        """Fresh orders waiting for dispatch, as if ShopNow had just sent them."""
        for hub in self.hubs.values():
            for _ in range(13 + self.rng.randint(0, 2)):
                created = self.now - minutes(self.rng.randint(5, 150))
                express = self.rng.random() < 0.15
                promised = created + timedelta(
                    hours=self.rng.uniform(4, 6) if express else self.rng.uniform(7, 9)
                )
                order = self._new_order(hub, self.today, created, promised, express)
                self._event(
                    order, created, None, OrderStatus.AWAITING_ASSIGNMENT, ActorType.PARTNER
                )
                self.add(
                    SimShopnowOrder,
                    {
                        "id": self.uid(),
                        "waybill_code": order["waybill_code"],
                        "partner_order_ref": order["partner_order_ref"],
                        "payload": {
                            "waybill_code": order["waybill_code"],
                            "hub_code": hub.seed.code,
                            "recipient_name": order["recipient_name"],
                            "recipient_phone": order["recipient_phone"],
                            "delivery_address": order["delivery_address"],
                            "delivery_lat": order["delivery_lat"],
                            "delivery_lng": order["delivery_lng"],
                            "weight_kg": str(order["weight_kg"]),
                            "cod_amount": str(order["cod_amount"]),
                            "items": order["items"],
                            "priority": order["priority"].value,
                            "promised_at": promised.isoformat(),
                        },
                        "last_status": OrderStatus.AWAITING_ASSIGNMENT.value,
                        "current_eta": None,
                        "last_event_at": created,
                        "created_at": created,
                        "updated_at": created,
                    },
                )

    def _routes_today(self) -> None:
        """A few drivers per hub are halfway through today's route, so the hub map, route
        planning and the GPS simulator have something to show right after seeding."""
        for hub in self.hubs.values():
            drivers = self.drivers_by_hub[hub.seed.code]
            for index, position in enumerate(BUSY_POSITIONS):
                if position < len(drivers):
                    self._busy_route(hub, drivers[position], first_done=index == 0)

    def _busy_route(self, hub: HubInfo, driver: DriverInfo, *, first_done: bool) -> None:
        rng = self.rng
        started = self.now - minutes(rng.randint(45, 100))
        assigned = started - minutes(rng.randint(35, 50))
        route_id = self.uid()
        self.add(
            Route,
            {
                "id": route_id,
                "hub_id": hub.id,
                "driver_id": driver.id,
                "work_date": self.today,
                "status": RouteStatus.IN_PROGRESS,
                "polyline": None,
                "total_distance_m": None,
                "total_duration_s": None,
                "published_at": assigned,
                "started_at": started,
                "completed_at": None,
                "created_at": assigned,
                "updated_at": started,
            },
        )
        orders: list[Row] = []
        for _ in range(rng.choice([3, 4])):
            created = assigned - minutes(rng.randint(20, 90))
            express = rng.random() < 0.2
            promised = created + timedelta(
                hours=rng.uniform(4, 5) if express else rng.uniform(6, 8)
            )
            order = self._new_order(hub, self.today, created, promised, express)
            self._event(order, created, None, OrderStatus.AWAITING_ASSIGNMENT, ActorType.PARTNER)
            self._offers(order, driver, [driver], assigned, round_no=1)
            self._assign(order, driver, assigned)
            picked = assigned + minutes(rng.randint(10, 25))
            self._event(order, picked, OrderStatus.ASSIGNED, OrderStatus.PICKED_UP,
                        ActorType.USER, driver.id, lat=hub.seed.lat, lng=hub.seed.lng)  # fmt: skip
            self._event(order, started, OrderStatus.PICKED_UP, OrderStatus.OUT_FOR_DELIVERY,
                        ActorType.USER, driver.id)  # fmt: skip
            orders.append(order)

        # Visit stops nearest first, as the driver would.
        here = (hub.seed.lat, hub.seed.lng)
        ordered: list[Row] = []
        remaining = orders[:]
        while remaining:
            closest = min(
                remaining,
                key=lambda o: math.dist(here, (o["delivery_lat"], o["delivery_lng"])),
            )
            ordered.append(closest)
            remaining.remove(closest)
            here = (closest["delivery_lat"], closest["delivery_lng"])

        if first_done:
            self._attempt(ordered[0], driver, started + minutes(rng.randint(15, 30)), success=True)
        pending = [o for o in ordered if o["status"] == OrderStatus.OUT_FOR_DELIVERY]
        # The driver is part of the way to the next stop.
        last = ordered[0] if first_done else None
        origin = (
            (last["delivery_lat"], last["delivery_lng"]) if last else (hub.seed.lat, hub.seed.lng)
        )
        target = (pending[0]["delivery_lat"], pending[0]["delivery_lng"])
        share = rng.uniform(0.3, 0.6)
        position = (
            round(origin[0] + (target[0] - origin[0]) * share, 6),
            round(origin[1] + (target[1] - origin[1]) * share, 6),
        )
        profile = self._profiles[driver.id]
        profile["last_lat"], profile["last_lng"] = position

        clock = self.now
        here = position
        for seq, order in enumerate(ordered, start=1):
            stop_id = self.uid()
            done = order["status"] == OrderStatus.DELIVERED
            eta = order["delivered_at"] if done else None
            if not done:
                point = (order["delivery_lat"], order["delivery_lng"])
                km = math.dist(here, point) * 111.0
                clock += minutes(km * 1.4 / 25 * 60 * 1.1)
                eta = clock
                clock += minutes(5)
                here = point
                order["current_eta"] = eta
                order["eta_source"] = EtaSource.SYSTEM
                order["eta_degraded"] = True
            order["route_stop_id"] = stop_id
            self.add(
                RouteStop,
                {
                    "id": stop_id,
                    "route_id": route_id,
                    "seq": seq,
                    "address": order["delivery_address"],
                    "lat": order["delivery_lat"],
                    "lng": order["delivery_lng"],
                    "recipient_name": order["recipient_name"],
                    "recipient_phone": order["recipient_phone"],
                    "eta": eta,
                    "status": StopStatus.DONE if done else StopStatus.PENDING,
                    "arrived_at": order["delivered_at"] if done else None,
                    "created_at": assigned,
                    "updated_at": started,
                },
            )
            self._shop_record(hub, order, driver)

    def _shop_record(self, hub: HubInfo, order: Row, driver: DriverInfo) -> None:
        """ShopNow's copy of an order, with the webhooks it would have received."""
        self.add(
            SimShopnowOrder,
            {
                "id": self.uid(),
                "waybill_code": order["waybill_code"],
                "partner_order_ref": order["partner_order_ref"],
                "payload": {
                    "waybill_code": order["waybill_code"],
                    "hub_code": hub.seed.code,
                    "recipient_name": order["recipient_name"],
                    "recipient_phone": order["recipient_phone"],
                    "delivery_address": order["delivery_address"],
                    "delivery_lat": order["delivery_lat"],
                    "delivery_lng": order["delivery_lng"],
                    "weight_kg": str(order["weight_kg"]),
                    "cod_amount": str(order["cod_amount"]),
                    "items": order["items"],
                    "priority": order["priority"].value,
                    "promised_at": order["promised_at"].isoformat(),
                },
                "last_status": order["status"].value,
                "current_eta": order["current_eta"],
                "last_event_at": order["updated_at"],
                "created_at": order["created_at"],
                "updated_at": order["updated_at"],
            },
        )
        events = [
            row
            for row in self.rows[OrderEvent]
            if row["order_id"] == order["id"] and row["to_status"] is not None
        ]
        name = next(row["full_name"] for row in self.rows[User] if row["id"] == driver.id)
        phone = next(row["phone"] for row in self.rows[User] if row["id"] == driver.id)
        for event in events[1:]:
            status = event["to_status"]
            kind = {
                OrderStatus.ASSIGNED: "order.driver_assigned",
                OrderStatus.DELIVERED: "order.delivered",
            }.get(status, "order.status_changed")
            payload: dict[str, Any] = {
                "event": kind,
                "waybill_code": order["waybill_code"],
                "partner_order_ref": order["partner_order_ref"],
                "status": status.value,
                "eta": order["current_eta"].isoformat() if order["current_eta"] else None,
                "eta_is_estimate": True,
                "promised_at": order["promised_at"].isoformat(),
            }
            if status == OrderStatus.ASSIGNED:
                payload["driver"] = {"name": name, "phone": phone}
            if status == OrderStatus.OUT_FOR_DELIVERY:
                payload["message"] = "Your parcel is on its way."
            self.add(
                SimShopnowWebhook,
                {
                    "id": self.uid(),
                    "event_type": kind,
                    "waybill_code": order["waybill_code"],
                    "payload": payload,
                    "signature_valid": True,
                    "received_at": event["created_at"] + timedelta(seconds=3),
                },
            )

    def _daily_stats(self) -> None:
        for (driver_id, day), counters in sorted(
            self._stats.items(), key=lambda item: (item[0][1], str(item[0][0]))
        ):
            self.add(
                DailyDriverStat,
                {
                    "driver_id": driver_id,
                    "date": day,
                    "hub_id": self.hubs[self._driver_hub[driver_id]].id,
                    **counters,
                },
            )
