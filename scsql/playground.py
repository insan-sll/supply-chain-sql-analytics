"""Checks for the free-text SQL box in the app.

The database is opened read-only with external file access disabled, so these
checks are a second layer: one statement, read queries only, capped row count.
"""

from __future__ import annotations

import re

MAX_ROWS = 1000
_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)


class QueryRejected(ValueError):
    """Raised when a playground query is not a single read-only SELECT."""


def prepare(sql: str) -> str:
    """Return the query wrapped with a row limit, or raise QueryRejected."""
    body = _COMMENT.sub(" ", sql).strip().rstrip(";").strip()
    if not body:
        raise QueryRejected("Enter a query.")
    if ";" in body:
        raise QueryRejected("Run one statement at a time.")
    first = body.split(None, 1)[0].lower()
    if first not in {"select", "with", "from"}:
        raise QueryRejected("Only SELECT queries are allowed here.")
    return f"SELECT * FROM ({body}) AS q LIMIT {MAX_ROWS}"
