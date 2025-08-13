import datetime
import itertools
from typing import BinaryIO, Annotated

import numpy as np
import pandas as pd
import pydantic

from ..enums import QualityGroup

_DEFAULT_MAX_ALLOWED_MISSING_VALUES_PER_COLUMN = 2  # heuristic
COLS_PER_DAY = 3


def _parse_timestamp_to_time(value: pd.Timestamp):
    return value.time()


class ParsingDayChargeScheduleEntry(pydantic.BaseModel):
    day: datetime.date
    start_time: Annotated[datetime.time, pydantic.BeforeValidator(_parse_timestamp_to_time)]
    grade: str | None
    mould_size: str | None


class ParsingMonthSteelProductionEntry(pydantic.BaseModel):
    month: datetime.date
    group: QualityGroup
    grade: str
    short_tons: int


class ParsingOrderForecastEntry(pydantic.BaseModel):
    month: datetime.date
    group: QualityGroup
    heats_orders_forecasted: int


def _drop_empty_columns(df: pd.DataFrame, *, max_empty_vals=_DEFAULT_MAX_ALLOWED_MISSING_VALUES_PER_COLUMN):
    # keep columns with data
    good_columns = df.isna().sum() <= max_empty_vals
    df = df.loc[:, good_columns]
    return df


def _impute_column_numerics_if_missing(df: pd.DataFrame):
    # account for possibility of missing data with imputation
    # select numeric columns
    indexer = df.select_dtypes(include='number').columns

    # fill NaNs in numeric columns/rows with median
    df[indexer] = df[indexer].fillna(df[indexer].median())

    return df


def _split_columns(df):
    # split for every 3rd column
    chunks = []
    for start_time_idx, grade_idx, mould_size_idx in itertools.batched(df.columns, COLS_PER_DAY):
        start_times = df.iloc[:, start_time_idx]
        grades = df.iloc[:, grade_idx]
        mould_sizes = df.iloc[:, mould_size_idx]

        chunk = pd.concat([start_times, grades, mould_sizes], axis=1, ignore_index=True)
        chunk.columns = chunk.iloc[0].values
        chunk = chunk[1:].reset_index(drop=True)

        chunks.append(chunk)

    return chunks


def parse_daily_charge_schedule_file(file: BinaryIO) -> list[ParsingDayChargeScheduleEntry]:
    """
    Assumptions:
    - title at first row
    - grouped columns with a title, and 3 subcolumns
    """
    ret: list[ParsingDayChargeScheduleEntry] = []

    df = pd.read_excel(file, skiprows=1)  # assuming title is first row
    days = df.columns[~df.columns.astype(str).str.startswith("Unnamed")].values

    # drop the unhelpful column labels
    df.columns = pd.RangeIndex(df.shape[1])

    # split for every 3rd column
    unprocessed_chunks = _split_columns(df)

    # process each chunk
    processed_chunks = []
    chunk: pd.DataFrame
    for day, chunk in zip(days, unprocessed_chunks):
        pchunk: pd.DataFrame = chunk.replace('-', np.nan)
        pchunk.replace({np.nan: None}, inplace=True)
        pchunk = pchunk.dropna(axis=0, how='all')
        pchunk['Day'] = day
        pchunk = pchunk.infer_objects()
        processed_chunks.append(pchunk)

    for pchunk in processed_chunks:
        pdict = pchunk.to_dict(orient='records')
        for row in pdict:
            info = ParsingDayChargeScheduleEntry(
                day=row['Day'],
                start_time=row['Start time'],
                grade=row['Grade'],
                mould_size=row['Mould size']
            )
            ret.append(info)

    return ret


def parse_monthly_steel_grade_file(file: BinaryIO) -> list[ParsingMonthSteelProductionEntry]:
    # ASSUMPTION: year is the number after the month

    ret: list[ParsingMonthSteelProductionEntry] = []

    # Process data
    df = pd.read_excel(file, skiprows=1)

    # fill cells with missing quality groups
    df['Quality group'] = df['Quality group'].ffill()

    df = _drop_empty_columns(df)  # drop columns first before imputation
    df = _impute_column_numerics_if_missing(df)

    for _, row in df.iterrows():
        group = row['Quality group']
        grade = row['Grade']

        # assuming that month columns are always after the first 2 columns
        months_data = row.iloc[2:]

        # need to iterate the next columns since
        # column names are dynamically named
        for month, tons in months_data.items():
            info = ParsingMonthSteelProductionEntry(
                group=QualityGroup[group.upper()],
                month=month,  # type: ignore
                grade=grade,
                short_tons=tons
            )

            ret.append(info)

    return ret


def parse_monthly_order_forecasts_file(file: BinaryIO) -> list[ParsingOrderForecastEntry]:
    ret: list[ParsingOrderForecastEntry] = []

    # Process data
    df = pd.read_excel(file, skiprows=1)
    df = _drop_empty_columns(df)
    df = _impute_column_numerics_if_missing(df)

    for _, row in df.iterrows():
        group = row['Quality:']

        # assuming that month columns are always after the first one
        months_data = row.iloc[1:]

        # need to iterate the next columns since
        # column names are dynamically named
        for month, heats_orders_forecasted in months_data.items():
            info = ParsingOrderForecastEntry(
                group=QualityGroup[group.upper()],
                month=month,  # type: ignore
                heats_orders_forecasted=heats_orders_forecasted
            )

            ret.append(info)

    return ret
