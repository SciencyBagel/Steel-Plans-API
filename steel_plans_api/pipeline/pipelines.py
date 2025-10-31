from typing import BinaryIO, Sequence

import sqlalchemy as sqla
from pydantic import BaseModel

from . import db, parsing
from ..enums import UploadFileType

__all__ = (
    'create_db_pipeline',
)

pipelines = {
    UploadFileType.MONTHLY_STEEL_GRADE_PRODUCTION: (parsing.parse_monthly_steel_grade_file,
                                                    db.month_steel_production),
    UploadFileType.DAILY_CHARGE_SCHEDULE: (parsing.parse_daily_charge_schedule_file,
                                           db.day_steel_production),
    UploadFileType.MONTHLY_ORDER_FORECAST: (parsing.parse_monthly_order_forecasts_file,
                                            db.month_group_order_forecast)
}


def create_db_pipeline(api_param_type: UploadFileType):
    """Creates a database pipeline based on the api paramater type.

    It uses the argument to identify a parser and table pair.

    Args:
        api_param_type: The type of upload file type

    Returns:
        A callable that takes a database connection, and a file and
        returns a sequence of row mappings.

    """

    parser, table = pipelines[api_param_type]

    def save_file_to_conn(file: BinaryIO, conn: sqla.Connection) -> Sequence[sqla.RowMapping]:
        models: list[BaseModel] = parser(file)
        stmt = sqla.insert(table).returning(table)
        res = conn.execute(stmt, [model.model_dump() for model in models]).mappings().all()

        return res

    return save_file_to_conn
