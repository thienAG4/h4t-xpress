"""Static reference data: roles, permissions, areas, hubs, shifts, settings, name pools."""

from dataclasses import dataclass
from datetime import time

from app.modules.hubs.models import ShiftCode
from app.modules.incidents.models import IncidentCategory, IncidentType
from app.modules.orders.models import FailureReason
from app.modules.rbac.models import RoleCode

ROLES: list[tuple[RoleCode, str, str]] = [
    (RoleCode.DRIVER, "Driver", "Delivery driver using the mobile app"),
    (RoleCode.HUB_MANAGER, "Hub Manager", "Monitors and dispatches one hub"),
    (RoleCode.EXECUTIVE, "Executive", "Reads company-wide reports"),
    (RoleCode.SYSTEM_ADMIN, "System Admin", "Manages accounts, permissions and settings"),
]

# (code, group, description) - SPEC §2.2
PERMISSIONS: list[tuple[str, str, str]] = [
    ("shift.register", "driver", "Register or cancel work shifts"),
    ("availability.toggle", "driver", "Go online/offline for new orders"),
    ("offer.respond", "driver", "Accept or decline job offers"),
    ("order.update_own", "driver", "Scan, update status, deliver or fail own orders"),
    ("eta.update_own", "driver", "Manually update ETA of own orders"),
    ("incident.report", "driver", "Report a delivery incident"),
    ("hub.dashboard.view", "hub", "View the hub dashboard"),
    ("order.view_hub", "hub", "View orders of the hub"),
    ("order.reassign", "hub", "Reassign orders to another driver"),
    ("route.plan", "hub", "Plan, optimise and reorder routes"),
    ("incident.manage", "hub", "Classify, respond to and resolve incidents"),
    ("driver.view_hub", "hub", "View drivers of the hub and their locations"),
    ("report.view", "report", "View reports"),
    ("report.export", "report", "Export reports to Excel/PDF"),
    ("user.manage", "admin", "Create, edit and lock user accounts"),
    ("role.manage", "admin", "Edit the role-permission matrix"),
    ("hub.manage", "admin", "Manage hubs, areas and shifts"),
    ("settings.manage", "admin", "Edit dispatch, ETA and SLA parameters"),
    ("audit.view", "admin", "View the audit log"),
]

DEFAULT_ROLE_PERMISSIONS: dict[RoleCode, list[str]] = {
    RoleCode.DRIVER: [
        "shift.register",
        "availability.toggle",
        "offer.respond",
        "order.update_own",
        "eta.update_own",
        "incident.report",
    ],
    RoleCode.HUB_MANAGER: [
        "hub.dashboard.view",
        "order.view_hub",
        "order.reassign",
        "route.plan",
        "incident.manage",
        "driver.view_hub",
        "report.view",
    ],
    RoleCode.EXECUTIVE: ["report.view", "report.export"],
    RoleCode.SYSTEM_ADMIN: [
        "user.manage",
        "role.manage",
        "hub.manage",
        "settings.manage",
        "audit.view",
    ],
}


@dataclass(frozen=True)
class AreaSeed:
    code: str
    name: str
    ward: str
    lat: float
    lng: float
    radius_km: float
    streets: tuple[str, ...]


# Ward names follow the 2025 administrative reform (Bình Dương merged into TP.HCM).
AREAS: list[AreaSeed] = [
    AreaSeed(
        "DI_AN",
        "Dĩ An",
        "Dĩ An",
        10.9050,
        106.7700,
        3.0,
        ("Nguyễn An Ninh", "Lý Thường Kiệt", "Trần Hưng Đạo", "Đường số 9", "Nguyễn Tri Phương"),
    ),
    AreaSeed(
        "LINH_XUAN",
        "Linh Xuân",
        "Linh Xuân",
        10.8800,
        106.7750,
        2.5,
        ("Quốc lộ 1K", "Kha Vạn Cân", "Đường số 18", "Linh Trung", "Đường số 6"),
    ),
    AreaSeed(
        "THU_DUC",
        "Thủ Đức",
        "Thủ Đức",
        10.8500,
        106.7650,
        3.0,
        ("Võ Văn Ngân", "Đặng Văn Bi", "Lê Văn Chí", "Đoàn Kết", "Hoàng Diệu 2"),
    ),
    AreaSeed(
        "BINH_THANH",
        "Bình Thạnh",
        "Bình Thạnh",
        10.8080,
        106.7120,
        3.0,
        ("Xô Viết Nghệ Tĩnh", "Điện Biên Phủ", "Bạch Đằng", "Phan Đăng Lưu", "Nơ Trang Long"),
    ),
    AreaSeed(
        "QUAN_1",
        "Quận 1",
        "Bến Thành",
        10.7760,
        106.7000,
        2.0,
        ("Lê Lợi", "Nguyễn Huệ", "Pasteur", "Hai Bà Trưng", "Lý Tự Trọng"),
    ),
]

AREA_ADJACENCY: list[tuple[str, str]] = [
    ("DI_AN", "LINH_XUAN"),
    ("DI_AN", "THU_DUC"),
    ("LINH_XUAN", "THU_DUC"),
    ("THU_DUC", "BINH_THANH"),
    ("BINH_THANH", "QUAN_1"),
]


@dataclass(frozen=True)
class HubSeed:
    code: str
    name: str
    address: str
    lat: float
    lng: float
    area_code: str
    manager_email: str


HUBS: list[HubSeed] = [
    HubSeed(
        "DIAN",
        "H4T Hub Dĩ An",
        "15 Nguyễn An Ninh, P. Dĩ An, TP.HCM",
        10.9064,
        106.7697,
        "DI_AN",
        "hub.dian@demo.h4t",
    ),
    HubSeed(
        "LINHXUAN",
        "H4T Hub Linh Xuân",
        "120 Quốc lộ 1K, P. Linh Xuân, TP.HCM",
        10.8826,
        106.7720,
        "LINH_XUAN",
        "hub.linhxuan@demo.h4t",
    ),
    HubSeed(
        "THUDUC",
        "H4T Hub Thủ Đức",
        "48 Võ Văn Ngân, P. Thủ Đức, TP.HCM",
        10.8498,
        106.7712,
        "THU_DUC",
        "hub.thuduc@demo.h4t",
    ),
]

# (code, display name, start, end, capacity per hub)
SHIFTS: list[tuple[ShiftCode, str, time, time, int]] = [
    (ShiftCode.MORNING, "Morning", time(7, 0), time(12, 0), 12),
    (ShiftCode.AFTERNOON, "Afternoon", time(13, 0), time(18, 0), 12),
    (ShiftCode.FULL_DAY, "Full day", time(7, 0), time(18, 0), 8),
]

DRIVERS_PER_HUB = 10


def default_settings(demo_mode: bool) -> list[tuple[str, object, str]]:
    """(key, value, description) for system_settings. Demo mode shortens the offer timeout."""
    return [
        (
            "dispatch.weights",
            {"distance": 0.40, "load": 0.25, "performance": 0.20, "time_fit": 0.15},
            "Weights of the driver ranking score (BR5)",
        ),
        (
            "dispatch.offer_timeout_s",
            30 if demo_mode else 600,
            "Seconds a driver has to answer an offer before it expires (BR7)",
        ),
        ("dispatch.max_candidates_per_round", 5, "Drivers offered one by one per round (BR6)"),
        ("dispatch.max_rounds", 3, "Rounds before an order is put ON_HOLD (EX3)"),
        ("dispatch.round_retry_delay_s", 300, "Delay before a new dispatch round"),
        ("dispatch.max_active_orders", 20, "Max orders a driver can hold at once"),
        ("dispatch.max_distance_km", 15, "Distance at which the distance score reaches 0"),
        ("dispatch.location_fresh_min", 10, "GPS ping age that still counts as app open"),
        ("eta.service_time_min", 5, "Minutes spent at each stop"),
        (
            "eta.traffic_factors",
            [
                {"from": "07:00", "to": "09:00", "factor": 1.5},
                {"from": "16:00", "to": "19:00", "factor": 1.5},
            ],
            "Rush-hour multipliers on OSRM durations (estimate, not live traffic)",
        ),
        ("eta.default_traffic_factor", 1.1, "Multiplier outside rush hours"),
        ("eta.notify_threshold_min", 15, "ETA change that triggers a partner notification"),
        ("eta.recompute_interval_s", 30, "Minimum seconds between ETA recomputations per route"),
        ("eta.fallback_speed_kmh", 25, "Average speed used when OSRM is unavailable"),
        ("eta.fallback_road_factor", 1.4, "Straight-line to road distance factor"),
        ("sla.grace_min", 120, "An order is late when delivered after promised_at + grace"),
        ("delivery.max_attempts", 3, "Failed attempts before the order is returned"),
        ("shift.cutoff_time", "06:00", "Latest time to register for a shift on the same day"),
        ("shift.max_days_ahead", 7, "How far ahead drivers can register"),
        ("anomaly.eta_increase_count", 3, "Consecutive ETA increases that raise ETA_ANOMALY"),
        ("anomaly.eta_increase_total_min", 30, "Total ETA increase that raises ETA_ANOMALY"),
        ("anomaly.idle_minutes", 15, "Minutes without movement that raise DRIVER_IDLE"),
        ("anomaly.idle_radius_m", 50, "Movement below this radius counts as idle"),
    ]


SURNAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ",
    "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý",
]  # fmt: skip
MALE_MIDDLE = ["Văn", "Minh", "Đức", "Quang", "Hữu", "Thanh", "Gia", "Hoàng", "Công", "Tấn"]
FEMALE_MIDDLE = ["Thị", "Ngọc", "Thanh", "Thu", "Mỹ", "Bảo"]
MALE_GIVEN = [
    "An", "Bình", "Cường", "Dũng", "Duy", "Hải", "Hiếu", "Hùng", "Khang", "Khoa",
    "Long", "Nam", "Phát", "Phúc", "Quân", "Sơn", "Tài", "Thắng", "Thịnh", "Trí",
    "Trung", "Tuấn", "Việt", "Vinh", "Lộc", "Kiên",
]  # fmt: skip
FEMALE_GIVEN = [
    "Linh", "Mai", "Trang", "Hương", "Ngân", "Vy", "Hà", "Thảo", "Nhi", "Yến", "Châu", "Uyên",
]  # fmt: skip

PRODUCTS = [
    "Áo thun", "Tai nghe Bluetooth", "Sách", "Bình giữ nhiệt", "Ốp lưng điện thoại",
    "Giày thể thao", "Nồi chiên không dầu", "Bàn phím cơ", "Kem chống nắng",
    "Đồ chơi lắp ráp", "Balo", "Đèn bàn", "Chuột không dây", "Sạc dự phòng",
]  # fmt: skip

# Incidents generated in history: (type, weight, category, sample descriptions)
INCIDENT_PROFILES: list[tuple[IncidentType, int, IncidentCategory, tuple[str, ...]]] = [
    (
        IncidentType.TRAFFIC_JAM,
        30,
        IncidentCategory.OBJECTIVE,
        ("Heavy traffic jam on the main road, not moving.", "Road blocked near the market."),
    ),
    (
        IncidentType.WEATHER,
        20,
        IncidentCategory.OBJECTIVE,
        ("Heavy rain and flooded street.", "Storm, waiting for the rain to ease."),
    ),
    (
        IncidentType.TRAFFIC_ACCIDENT,
        10,
        IncidentCategory.OBJECTIVE,
        ("Accident ahead, police closed the lane.", "Minor collision, need to detour."),
    ),
    (
        IncidentType.VEHICLE_BREAKDOWN,
        22,
        IncidentCategory.SUBJECTIVE,
        ("Flat tire, cannot continue.", "Motorbike engine broke down."),
    ),
    (
        IncidentType.HEALTH,
        8,
        IncidentCategory.SUBJECTIVE,
        ("Feeling sick, cannot finish the route.", "Minor injury, need to stop."),
    ),
    (
        IncidentType.OTHER,
        10,
        IncidentCategory.OBJECTIVE,
        ("Recipient's building closed for inspection.", "Road works, need another way."),
    ),
]

HUB_RESPONSES = {
    IncidentCategory.OBJECTIVE: (
        "New route sent, please follow the updated stop order.",
        "Detour approved. Customer has been informed of the delay.",
    ),
    IncidentCategory.SUBJECTIVE: (
        "Another driver is coming to take over your orders. Stay safe.",
        "Orders reassigned. Please wait at your location for the handover.",
    ),
}

FAILURE_REASONS: list[tuple[FailureReason, int, str]] = [
    (FailureReason.CUSTOMER_UNREACHABLE, 40, "Called 3 times, no answer."),
    (FailureReason.CUSTOMER_ABSENT, 25, "Nobody at home."),
    (FailureReason.CUSTOMER_REFUSED, 20, "Customer refused to receive the parcel."),
    (FailureReason.WRONG_ADDRESS, 10, "Address does not exist."),
    (FailureReason.OTHER, 5, "Gate locked, security did not allow entry."),
]
