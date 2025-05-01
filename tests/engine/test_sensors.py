from datetime import datetime
from unittest.mock import AsyncMock

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

from engine.classes import PedFluxCounterMeasurement
from engine.sensors import poll_all_sensors


@pytest.mark.asyncio
async def test_poll_all_sensors(monkeypatch):
    # Fake sensor descriptions
    sensors = gpd.GeoDataFrame(
        [
            {'name': 'Sensor A', 'type': 'CEC_PED_FLUX_COUNTER', 'oa_code': 'OA001', 'measurement_width_m': 2.0},
            {'name': 'Sensor B', 'type': 'OTHER', 'oa_code': np.nan, 'measurement_width_m': 1.0},
        ]
    )

    monkeypatch.setattr('engine.sensors.gpd.read_file', lambda _: sensors)

    fake_meas = [
        PedFluxCounterMeasurement(sensor_name='Sensor A', datetime=datetime(202, 6, 7), flow_pax_per_hour=3600)
    ]

    async_mock_poll_ee = AsyncMock(return_value=[])
    async_mock_poll_edin = AsyncMock(return_value=fake_meas)
    monkeypatch.setattr('engine.sensors.poll_essential_edinburgh', async_mock_poll_ee)
    monkeypatch.setattr('engine.sensors.poll_edintraveldata', async_mock_poll_edin)

    monkeypatch.setattr(
        'engine.sensors.SensorType', type('SensorType', (), {'CEC_PED_FLUX_COUNTER': 'CEC_PED_FLUX_COUNTER'})
    )

    monkeypatch.setattr('engine.sensors.AVERAGE_WALKING_SPEED_MPS', 1.3)

    df = await poll_all_sensors()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1  # Only one had valid OA code
    density = df.iloc[0]['density_pax_per_m2']
    expected = 3600 / 3600 / 2.0 / 1.3  # = 0.3846
    np.testing.assert_approx_equal(density, expected)
