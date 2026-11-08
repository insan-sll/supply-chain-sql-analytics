import pytest

from scsql.db import build
from scsql.questions import load_questions


@pytest.fixture(scope="session")
def con():
    connection = build()
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def results(con):
    return {q.id: con.execute(q.sql).df() for q in load_questions()}
