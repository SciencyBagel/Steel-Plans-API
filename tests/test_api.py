import pytest
from fastapi import status

import steel_plans_api


@pytest.mark.parametrize(
    'file_to_upload',
    [
        steel_plans_api.UploadFileType.MONTHLY_STEEL_GRADE_PRODUCTION.value,
        steel_plans_api.UploadFileType.DAILY_CHARGE_SCHEDULE.value,
        steel_plans_api.UploadFileType.MONTHLY_ORDER_FORECAST.value,
    ]
)
def test_upload_file(file_to_upload, data_dir, client):
    with open(data_dir / file_to_upload, 'rb') as f:
        files = {'file': (file_to_upload, f)}
        response = client.post(
            f'/files/{file_to_upload}',
            files=files,
        )
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.usefixtures('seeded_db')
@pytest.mark.parametrize('month', ['2024-09', '2024-08', '2024-07', '2024-06'])
def test_forecast(client, month):
    response = client.get('/forecast/production/', params={'month': month})
    data = response.json()

    assert month == data['month']

    for group in data['groups']:
        # check heats add up to group
        assert sum(grade['heats'] for grade in group['grades']) == group['heats']

        # check proportions are correct
        assert sum(grade['proportion'] for grade in group['grades']) == pytest.approx(1.0)
        for grade in group['grades']:
            assert grade['proportion'] * group['heats'] == pytest.approx(grade['heats'])
            # assert pytest.approx(pred_heat) == prop * group['heats'], (pred_heat, group['heats'])

    # for group 

    assert response.status_code == status.HTTP_200_OK
