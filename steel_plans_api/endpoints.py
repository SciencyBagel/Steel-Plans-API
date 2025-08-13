import datetime
from typing import Annotated

import sqlalchemy as sqla
from fastapi import FastAPI, UploadFile, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError

from . import __version__
from .enums import UploadFileType
from .pipeline import analysis, db, create_db_pipeline
from .responses import ResponseForecast, ResponseUploadFile

__all__ = ('app',)

app = FastAPI(
    title='Steel Plans API',
    version=__version__
)


@app.get("/", include_in_schema=False)
async def docs_redirect():
    # immediately redirects to docs
    return RedirectResponse(url='/redoc')


# NOTE: Assumptions
# - the types of files uploaded have a general structure to them
# - expecting potentially typos/errors in files, pydantic validation will reject badly structured files
@app.post('/files/{type_of_file}', status_code=status.HTTP_201_CREATED, response_model=ResponseUploadFile, )
async def upload_file(type_of_file: UploadFileType, file: UploadFile, conn: db.ConnectionDep):
    """Uploads a file to the Steel Production and Order Database"""

    try:
        save_file_to_db = create_db_pipeline(type_of_file)
        rows = save_file_to_db(conn, file.file)

    except IntegrityError:
        # since post method, will return 409 (conflict) if integrity error
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='File already exists')

    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Invalid file format or structure')

    response = {
        'file_type': type_of_file,
        'rows': len(rows)
    }
    return response


# NOTE: Assumptions
# - from order forecast, can predict how much to make per quality group, but can't tell what proportions of steel grades per group
@app.get('/forecast/production/', response_model=ResponseForecast)
async def forecast_grade_production(month: Annotated[str, Query(description='Format: YYYY-MM')],
                                    conn: db.ConnectionDep):
    """Forecasts grade production for specified month.

    Requires existing quality groups order forecast for the requested month. If there is no production data,
    forecast will be empty.

    Note there is room for extension. There is plenty of more information that
    could be returned with the production forecast.

    """

    year_month = datetime.datetime.strptime(month, "%Y-%m")
    stmt = sqla.select(db.month_group_order_forecast).where(
        sqla.extract('year', db.month_group_order_forecast.c.month) == year_month.year,
        sqla.extract('month', db.month_group_order_forecast.c.month) == year_month.month,
    )
    group_order_forecast_for_month = conn.execute(stmt).mappings().all()
    if not group_order_forecast_for_month:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f'No order forecast data for {month}')

    stmt = sqla.select(db.month_steel_production)
    all_production_data = conn.execute(stmt).mappings().all()

    try:
        group_breakdowns = analysis.forecast_grade_breakdown(group_order_forecast_for_month, all_production_data,
                                                             year_month)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    response = {
        'meta': {
            'timestamp': datetime.datetime.now(),
            'version': __version__
        },
        'month': month,
        'groups': group_breakdowns,
    }

    return response
