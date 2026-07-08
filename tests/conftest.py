from __future__ import annotations

import sqlite3

import pytest

from erring.db import connect, initialize_database


@pytest.fixture
def conn() -> sqlite3.Connection:
    connection = connect(":memory:")
    initialize_database(connection)
    yield connection
    connection.close()

