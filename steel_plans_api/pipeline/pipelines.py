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
    parser, table = pipelines[api_param_type]

    def pipeline(conn: sqla.Connection, file: BinaryIO) -> Sequence[sqla.RowMapping]:
        models: list[BaseModel] = parser(file)
        stmt = sqla.insert(table).returning(table)
        res = conn.execute(stmt, [model.model_dump() for model in models]).mappings().all()

        return res

    return pipeline
