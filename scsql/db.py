"""Build the DuckDB database from the generated tables."""

from __future__ import annotations

from pathlib import Path

import duckdb

from scsql.generate import SEED, generate

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

# Parents before children, so foreign keys are satisfied on insert.
TABLES = [
    "suppliers",
    "warehouses",
    "products",
    "orders",
    "order_lines",
    "shipments",
    "purchase_orders",
    "inventory_daily",
]


def build(path: str | Path = ":memory:", seed: int = SEED) -> duckdb.DuckDBPyConnection:
    """Create the schema, load every table and create the views."""
    frames = generate(seed)
    con = duckdb.connect(str(path))
    con.execute((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
    for name in TABLES:
        df = frames[name]
        columns = ", ".join(df.columns)
        con.register("staging", df)
        con.execute(f"INSERT INTO {name} ({columns}) SELECT {columns} FROM staging")
        con.unregister("staging")
    con.execute((SQL_DIR / "views.sql").read_text(encoding="utf-8"))
    return con


def build_file(path: str | Path, seed: int = SEED) -> Path:
    """Build the database into a file and close it, for read-only use later."""
    path = Path(path)
    path.unlink(missing_ok=True)
    build(path, seed).close()
    return path
