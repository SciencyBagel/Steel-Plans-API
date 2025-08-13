import datetime
from typing import Annotated

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from ..enums import QualityGroup

ALPHA_ES = 0.3
USE_EXP_SMOOHTHING = True


# NOTE: use exponential smoothing because I put more value in recent
# grade proportions

class ForecastProductionGrade(BaseModel):
    grade: Annotated[str, Field(description="Steel grade code, e.g. A36")]
    heats: Annotated[int, Field(description="Total heats forcasted")]
    proportion: Annotated[float, Field(ge=0.0, le=1.0)]


class ForecastProductionGroup(BaseModel):
    group: QualityGroup
    heats: int
    grades: Annotated[list[ForecastProductionGrade], Field(description="Grade-level proportions")]

def _normalize(base):
    """Make proportions add up to 1 (or 0 if no data)"""

    base = base.copy()
    s = base['proportion'].sum()
    if s > 0:
        # proportions sum up to 1
        base['proportion'] = base['proportion'] / s
    else:
        # if no predicted proportions, proportions are uniform
        n = len(base)
        base['proportion'] = (1.0 / n) if n else 0.0
    return base


def _do_forecast_breakdown(omf_df: pd.DataFrame, pm_df: pd.DataFrame, m_period: pd.Period) -> list[
    ForecastProductionGroup]:
    """
    
    Args:
        omf_df: The order forecast for the target month
        pm_df: Historical mothly steel production data
    
    Returns:
        Forecasts per group, broken down by grades for the target month
        
    """

    pm_df['proportion'] = (
            pm_df['heats_produced'] /
            pm_df.groupby(["month", "group"])['heats_produced'].transform("sum")
    )

    group_forecasts: list[ForecastProductionGroup] = []
    for quality_group, grade_production in pm_df.groupby("group"):
        parts = []
        for grade, m_df in grade_production.groupby('grade'):
            # sort by month to prepare for exponentional smoothening
            sorted_df = m_df.sort_values('month')  # type: ignore

            # use exponential smoothing
            # no adjust to do simple forcast
            smoothed = sorted_df["proportion"].ewm(alpha=ALPHA_ES, adjust=False).mean().iloc[
                -1]  # last one is predicted value
            parts.append((grade, smoothed))

        group_prod_forecast = pd.DataFrame(parts, columns=['grade', 'proportion'])
        group_prod_forecast = _normalize(group_prod_forecast)
        group_prod_forecast['group'] = quality_group
        group_prod_forecast['target_month'] = m_period

        # attach group total heats for the target month (0 if not present)
        try:
            group_orders_forecasted = int(
                omf_df.loc[omf_df['group'] == quality_group, "heats_orders_forecasted"].iat[0])
        except IndexError:
            group_orders_forecasted = 0

        # calculate forecasted grade production by multiplifying forecasted grade proportions by forecasted group orders
        group_prod_forecast['raw_heats'] = group_prod_forecast['proportion'] * group_orders_forecasted
        group_prod_forecast['heats'] = np.floor(group_prod_forecast['raw_heats']).astype(
            int)  # heats floored to integers
        group_prod_forecast['__remainder'] = group_prod_forecast['raw_heats'] - group_prod_forecast['heats']

        # hamilton rounding
        remainder = group_orders_forecasted - group_prod_forecast['heats'].sum()
        if remainder > 0:

            group_prod_forecast = group_prod_forecast.sort_values(  # largest remainders go first
                by=["__remainder", "grade"],  # tie-breaker: remainder first, then grade
                ascending=[False, True]
            )  # type: ignore

            col_idx = group_prod_forecast.columns.get_loc('heats')
            for i in range(int(remainder)):
                group_prod_forecast.iat[i, col_idx] += 1

        group_prod_forecast = group_prod_forecast.drop(columns=['__remainder'])

        # make sure total heats produced match order forecast
        assert group_prod_forecast['heats'].sum() == group_orders_forecasted

        # normalize proportions to match forecasted heats
        group_prod_forecast['proportion'] = group_prod_forecast['heats'] / group_prod_forecast['heats'].sum()

        # save to pyantic model for decoupling pandas from endpoints
        # and make it easier to know what output structure to expect)
        grades = [ForecastProductionGrade(**grade) for _, grade in group_prod_forecast.iterrows()]

        fpg = ForecastProductionGroup(
            group=QualityGroup(quality_group),
            heats=group_orders_forecasted,
            grades=grades
        )
        group_forecasts.append(fpg)

    return group_forecasts


def forecast_grade_breakdown(m_groups_forecast, production_data, year_month: datetime.date) -> list[
    ForecastProductionGroup]:
    omf_df = pd.DataFrame(m_groups_forecast)
    omf_df["month"] = (
        pd.to_datetime(omf_df["month"], format="%Y-%m", errors="coerce")
        .dt.to_period("M")
    )

    pm_df = pd.DataFrame(production_data).drop('short_tons', axis=1)
    pm_df["month"] = (
        pd.to_datetime(pm_df["month"], format="%Y-%m", errors="coerce")
        .dt.to_period("M")
    )

    m_period = pd.Period(year_month, freq="M")
    # only query for target date

    result: list[ForecastProductionGroup] = _do_forecast_breakdown(omf_df, pm_df, m_period)

    return result
