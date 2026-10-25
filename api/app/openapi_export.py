"""Write the OpenAPI schema to a file; the web app generates its TypeScript types from it.

Usage: python -m app.openapi_export [path]   (default: openapi.json)
"""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    target.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"OpenAPI schema written to {target}")


if __name__ == "__main__":
    main()
