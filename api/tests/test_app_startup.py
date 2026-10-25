"""The real entry point must load every model, not only what the tests happen to import.

Runs in a fresh interpreter: the test session itself already imports all models through
the seed module, which once hid a missing import in app.main (orders -> route_stops FK).
"""

import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]

CHECK = """
import app.main
from sqlalchemy.orm import configure_mappers
from app.core.db import Base
configure_mappers()
for table in Base.metadata.sorted_tables:
    for fk in table.foreign_keys:
        fk.column  # raises NoReferencedTableError when a target table is not registered
print(len(Base.metadata.tables))
"""


def test_app_main_registers_every_table() -> None:
    result = subprocess.run(
        [sys.executable, "-c", CHECK], cwd=API_DIR, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert int(result.stdout.strip()) == 35
