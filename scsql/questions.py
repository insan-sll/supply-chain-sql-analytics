"""Load the analysis queries and the metadata in their header comments."""

from __future__ import annotations

from dataclasses import dataclass

from scsql.db import SQL_DIR


@dataclass(frozen=True)
class Question:
    id: str
    title: str
    question: str
    method: str
    sql: str


def _parse(text: str, qid: str) -> Question:
    meta: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("--"):
            break
        key, _, value = line[2:].partition(":")
        meta[key.strip().lower()] = value.strip()
    missing = {"title", "question", "method"} - meta.keys()
    if missing:
        raise ValueError(f"{qid}: missing header fields {sorted(missing)}")
    return Question(qid, meta["title"], meta["question"], meta["method"], text.strip())


def load_questions() -> list[Question]:
    files = sorted((SQL_DIR / "queries").glob("*.sql"))
    return [_parse(f.read_text(encoding="utf-8"), f.stem) for f in files]
