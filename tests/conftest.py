import pytest
from sqlalchemy import text

from part1.db import make_engine
from part1.setup import TABLES, initialize
from part2.view import create_view


@pytest.fixture(scope="session")
def engine():
    instance = make_engine()
    initialize(instance, reset=True)
    with instance.begin() as connection:
        create_view(connection)
    yield instance
    # Restore rows AND identity sequences after all tests, including failed tests.
    initialize(instance, reset=True)
    with instance.begin() as connection:
        create_view(connection)
    instance.dispose()


@pytest.fixture
def conn(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


@pytest.fixture
def data(conn):
    return {
        name: [dict(row) for row in conn.execute(text(f'SELECT * FROM "{name}"')).mappings()]
        for name in TABLES
    }
