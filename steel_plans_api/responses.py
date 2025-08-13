import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from .enums import UploadFileType
from .pipeline.analysis import ForecastProductionGroup


class Meta(BaseModel):
    timestamp: datetime.datetime
    version: str


class ResponseUploadFile(BaseModel):
    file_type: UploadFileType
    rows: int


class ResponseForecast(BaseModel):
    meta: Meta
    month: Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM")]
    groups: list[ForecastProductionGroup]
