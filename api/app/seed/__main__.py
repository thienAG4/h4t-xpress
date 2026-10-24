import argparse
import asyncio
import sys
import time

from app.core.config import get_settings
from app.core.db import engine
from app.seed.runner import run_seed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.seed", description="Load H4T Xpress demo data (SPEC §6.4)."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--reset", action="store_true", help="delete all data, then seed")
    mode.add_argument(
        "--if-empty", action="store_true", help="seed only when the database has no data"
    )
    parser.add_argument("--history-days", type=int, help="days of order history (default: env)")
    parser.add_argument("--seed", type=int, help="random seed (default: env)")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    if args.reset and get_settings().app_env == "production":
        print("Refusing to --reset when APP_ENV=production.", file=sys.stderr)
        return 2
    started = time.perf_counter()
    try:
        counts = await run_seed(
            reset=args.reset,
            if_empty=args.if_empty,
            history_days=args.history_days,
            random_seed=args.seed,
        )
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        await engine.dispose()

    if counts is None:
        print("Seed skipped: database already has data.")
        return 0
    width = max(len(name) for name in counts)
    for name, count in counts.items():
        print(f"  {name:<{width}}  {count:>6}")
    print(f"Seeded {sum(counts.values())} rows in {time.perf_counter() - started:.1f}s.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
