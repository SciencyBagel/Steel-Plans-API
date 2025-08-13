import enum

__all__ = (
    'UploadFileType',
)


class QualityGroup(str, enum.Enum):
    REBAR = 'REBAR'
    SBQ = 'SBQ'
    MBQ = 'MBQ'
    CHQ = 'CHQ'


class UploadFileType(str, enum.Enum):
    MONTHLY_STEEL_GRADE_PRODUCTION = 'steel_grade_production.xlsx'
    DAILY_CHARGE_SCHEDULE = 'daily_charge_schedule.xlsx'
    MONTHLY_ORDER_FORECAST = 'product_groups_monthly.xlsx'
