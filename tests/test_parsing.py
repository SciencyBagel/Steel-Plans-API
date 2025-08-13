import pytest

from steel_plans_api.pipeline import parsing

cases = [
    pytest.param('steel_grade_production.xlsx', parsing.parse_monthly_steel_grade_file),
    pytest.param('daily_charge_schedule.xlsx', parsing.parse_daily_charge_schedule_file),
    pytest.param('product_groups_monthly.xlsx', parsing.parse_monthly_order_forecasts_file),
    pytest.param('steel_grade_production.xlsx', parsing.parse_daily_charge_schedule_file, marks=pytest.mark.xfail,
                 id='Wrong parser'),
]


@pytest.mark.parametrize('upload_file, parser', cases)
def test_parse(upload_file, data_dir, parser):
    with open(data_dir / upload_file, 'rb') as f:
        infos = parser(f)

    assert len(infos) > 0
