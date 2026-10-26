# 0003. Partner webhooks through a transactional outbox

Date: 2026-10-25. Status: accepted.

## Context

The e-commerce partner (simulated by ShopNow) must hear about every status change, new ETA and delay reason (FR-J-03, BR10). Calling the partner inside the request would either slow the driver's app or lose events when the partner is down.

## Decision

Each change inserts a row in `webhook_deliveries` in the same transaction as the order change (`partner/webhooks.py: notify_partner`). The worker sends due rows every five seconds with `X-H4T-Event`, `X-H4T-Delivery` (unique id) and `X-H4T-Signature` (HMAC-SHA256 of the body) headers. Failures are retried after 1, 5 and 30 minutes, then marked `FAILED` after six attempts (EX7). The ShopNow simulator verifies the signature and only builds the customer tracking page from webhooks it accepted.

## Consequences

- The partner never hears about a change that was rolled back, and never misses one that was committed.
- Delivery is at least once: the partner must accept duplicates, using the `X-H4T-Delivery` id.
- The customer page is a faithful view of what the partner really received, which makes the integration visible in the demo.
