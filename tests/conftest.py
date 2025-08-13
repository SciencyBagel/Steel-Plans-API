import pathlib

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from steel_plans_api import app
from steel_plans_api.enums import UploadFileType
from steel_plans_api.pipeline import create_db_pipeline
from steel_plans_api.pipeline.db import get_conn, metadata


@pytest.fixture
def data_dir():
    return pathlib.Path(__file__).parent.joinpath('data/')


@pytest.fixture(scope='session', autouse=True)
def global_setup_and_teardown():
    pd.set_option('future.no_silent_downcasting', True)
    yield


@pytest.fixture(scope='session')
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create the schema once per test session
    metadata.create_all(eng)
    yield eng
    metadata.drop_all(eng)


@pytest.fixture
def db_conn(engine):
    conn = engine.connect()
    trans = conn.begin()

    try:
        yield conn
    finally:
        trans.rollback()
        conn.close()


@pytest.fixture
def seeded_db(data_dir, db_conn):
    for file_type in list(UploadFileType):
        with open(data_dir / file_type.value, 'rb') as f:
            save_file_to_db = create_db_pipeline(file_type)
            save_file_to_db(db_conn, f)

    return db_conn


@pytest.fixture(scope='function')
def client(db_conn):
    # Override FastAPI’s DB dependency to use our test session
    def _get_db_override():
        try:
            yield db_conn
        finally:
            pass

    app.dependency_overrides[get_conn] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
