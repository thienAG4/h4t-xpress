from sqlalchemy import text

from app.core.db import engine
from app.seed import catalog
from app.seed.runner import run_seed

SCALAR_CHECKS = {
    # The last status event of every order must match its current status (BR3 history).
    "status_history_mismatch": """
        select count(*) from orders o
        join lateral (
            select to_status from order_events e
            where e.order_id = o.id and e.to_status is not null
            order by e.created_at desc, e.id desc limit 1
        ) last on true
        where last.to_status <> o.status
    """,
    "active_assignment_on_closed_order": """
        select count(*) from assignments a join orders o on o.id = a.order_id
        where a.status = 'ACTIVE' and o.status in ('DELIVERED', 'RETURNED_TO_HUB', 'CANCELLED')
    """,
    "delivered_without_attempt": """
        select count(*) from orders o
        where o.status = 'DELIVERED' and not exists (
            select 1 from delivery_attempts d
            where d.order_id = o.id and d.outcome = 'DELIVERED'
        )
    """,
    "accepted_offer_count_mismatch": """
        select count(*) from (
            select o.id from orders o
            left join dispatch_offers d on d.order_id = o.id and d.status = 'ACCEPTED'
            left join assignments a on a.order_id = o.id
            group by o.id having count(distinct d.id) <> count(distinct a.id)
        ) x
    """,
    "hub_manager_without_hub": """
        select count(*) from users u join roles r on r.id = u.role_id
        where r.code = 'HUB_MANAGER' and u.hub_id is null
    """,
}


async def test_seed_creates_reference_data_and_consistent_history() -> None:
    counts = await run_seed(reset=True, history_days=7, random_seed=1)

    assert counts is not None
    assert counts["roles"] == len(catalog.ROLES)
    assert counts["permissions"] == len(catalog.PERMISSIONS)
    assert counts["hubs"] == len(catalog.HUBS)
    assert counts["driver_profiles"] == len(catalog.HUBS) * catalog.DRIVERS_PER_HUB
    assert counts["users"] == counts["driver_profiles"] + len(catalog.HUBS) + 2
    assert counts["orders"] > 7 * len(catalog.HUBS) * 5
    assert counts["sim_shopnow_orders"] >= len(catalog.HUBS) * 13

    async with engine.connect() as conn:
        for name, sql in SCALAR_CHECKS.items():
            assert await conn.scalar(text(sql)) == 0, name

        awaiting = await conn.scalar(
            text("select count(*) from orders where status = 'AWAITING_ASSIGNMENT'")
        )
        assert awaiting == counts["sim_shopnow_orders"]


async def test_seed_is_skipped_when_data_exists() -> None:
    assert await run_seed(if_empty=True) is None


async def test_reset_reseeds_and_restarts_incident_codes() -> None:
    await run_seed(reset=True, history_days=7, random_seed=2)

    async with engine.connect() as conn:
        first_code = await conn.scalar(text("select min(code) from incidents"))
    assert first_code in (None, "INC-000001")
