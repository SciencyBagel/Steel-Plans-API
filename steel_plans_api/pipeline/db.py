import functools
from typing import Annotated

import sqlalchemy as sqla
from fastapi import Depends
from sqlalchemy import Date, Engine, Enum, Integer, String, create_engine, Time, inspect, Computed, Column, Connection

from ..enums import QualityGroup

DATABASE_URL = "sqlite:///./app.db"
TONS_PER_HEAT = 100

metadata = sqla.MetaData()

day_steel_production = sqla.Table(
    "daily_charge_schedule",
    metadata,
    Column('day', Date, primary_key=True, nullable=False),
    Column('start_time', Time, primary_key=True, nullable=False),
    Column('grade', String, primary_key=True, nullable=True),
    Column('mould_size', String, nullable=True),
)

month_steel_production = sqla.Table(
    'product_groups_monthly',
    metadata,
    Column('month', Date, nullable=False, primary_key=True),
    Column('grade', String, nullable=False, primary_key=True),
    Column('group', Enum(QualityGroup), nullable=False),
    Column('short_tons', Integer, nullable=False),
    Column('heats_produced', Integer, Computed(f'short_tons / {TONS_PER_HEAT}', persisted=True)),
)

month_group_order_forecast = sqla.Table(
    'steel_grade_production',
    metadata,
    Column('month', Date, primary_key=True, nullable=False),
    Column('group', Enum(QualityGroup), primary_key=True, nullable=False),
    Column('heats_orders_forecasted', Integer, primary_key=True, nullable=False),
)


@functools.lru_cache
def get_engine():
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    if not inspect(engine).get_table_names():
        metadata.create_all(engine)
    return engine


EngineDep = Annotated[Engine, Depends(get_engine)]


def get_conn(engine: EngineDep):
    with engine.begin() as conn:
        yield conn


ConnectionDep = Annotated[Connection, Depends(get_conn)]
