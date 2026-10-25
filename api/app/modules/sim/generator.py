"""Random but plausible ShopNow orders around a hub (names, addresses, parcels)."""

import math
import random
from datetime import timedelta
from decimal import Decimal

from app.core.clock import utc_now
from app.modules.orders.models import OrderPriority
from app.modules.partner.schemas import OrderItemIn, PartnerOrderIn
from app.seed import catalog

_rng = random.SystemRandom()


def random_point(lat: float, lng: float, radius_km: float) -> tuple[float, float]:
    distance = radius_km * math.sqrt(_rng.random())
    angle = _rng.uniform(0, 2 * math.pi)
    d_lat = distance * math.cos(angle) / 111.0
    d_lng = distance * math.sin(angle) / (111.0 * math.cos(math.radians(lat)))
    return round(lat + d_lat, 6), round(lng + d_lng, 6)


def area_for_hub(hub_code: str) -> catalog.AreaSeed:
    hub = next(h for h in catalog.HUBS if h.code == hub_code)
    return next(a for a in catalog.AREAS if a.code == hub.area_code)


def random_name() -> str:
    surname = _rng.choice(catalog.SURNAMES)
    if _rng.random() < 0.5:
        return f"{surname} {_rng.choice(catalog.MALE_MIDDLE)} {_rng.choice(catalog.MALE_GIVEN)}"
    return f"{surname} {_rng.choice(catalog.FEMALE_MIDDLE)} {_rng.choice(catalog.FEMALE_GIVEN)}"


def random_phone() -> str:
    # Retired 012x prefix: generated numbers cannot belong to real people.
    return f"0123{_rng.randint(0, 999_999):06d}"


def random_order(hub_code: str, waybill_code: str, *, express: bool) -> PartnerOrderIn:
    area = area_for_hub(hub_code)
    lat, lng = random_point(area.lat, area.lng, area.radius_km)
    hours = _rng.uniform(4, 6) if express else _rng.uniform(7, 10)
    cod = 0 if _rng.random() < 0.35 else _rng.randrange(50_000, 2_000_000, 1_000)
    return PartnerOrderIn(
        waybill_code=waybill_code,
        partner_order_ref=f"SN-ORD-{_rng.randint(10_000_000, 99_999_999)}",
        hub_code=hub_code,
        recipient_name=random_name(),
        recipient_phone=random_phone(),
        delivery_address=(
            f"{_rng.randint(1, 350)} {_rng.choice(area.streets)}, P. {area.ward}, TP.HCM"
        ),
        delivery_lat=lat,
        delivery_lng=lng,
        weight_kg=Decimal(str(round(_rng.uniform(0.2, 12.0), 2))),
        length_cm=Decimal(str(round(_rng.uniform(10, 60), 1))),
        width_cm=Decimal(str(round(_rng.uniform(10, 40), 1))),
        height_cm=Decimal(str(round(_rng.uniform(5, 40), 1))),
        cod_amount=Decimal(cod),
        items=[
            OrderItemIn(name=_rng.choice(catalog.PRODUCTS), qty=_rng.randint(1, 3))
            for _ in range(_rng.choices([1, 2, 3], weights=[70, 22, 8])[0])
        ],
        priority=OrderPriority.EXPRESS if express else OrderPriority.NORMAL,
        promised_at=utc_now() + timedelta(hours=hours),
    )


def is_express(ratio: float) -> bool:
    return _rng.random() < ratio
