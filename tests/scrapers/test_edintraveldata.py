from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from scrapers.edintraveldata import poll_edintraveldata


@pytest.mark.asyncio
async def test_poll_edintraveldata_parses_measurement(monkeypatch):
    expected_ped_count = 42
    fake_html = f"""
    <html><body>
    <table class="grid" id="gridTable">
        <tr><th>Time</th><th>Ped</th></tr>
        <tr><td>12:00</td><td>{expected_ped_count}</td></tr>
    </table>
    </body></html>
    """

    # Patch scrape_urls to return our fake HTML
    monkeypatch.setattr('scrapers.edintraveldata.scrape_urls', AsyncMock(return_value=[fake_html]))

    # Patch SimpleCache to always miss
    mock_cache = MagicMock()
    mock_cache.read.return_value = None
    monkeypatch.setattr('scrapers.edintraveldata.SimpleCache', lambda *args, **kwargs: mock_cache)

    monkeypatch.setattr(
        'scrapers.edintraveldata.datetime',
        type('FakeDatetime', (), {'now': staticmethod(lambda: datetime(2024, 4, 30, 12, 15))}),
    )

    sensor_descriptions = [
        {
            'name': 'CEC123',
            'source': 'https://mockurl.com/',
            'type': 'CEC_PED_FLUX_COUNTER',
            'measurement_width_m': 2.0,
        }
    ]

    results = await poll_edintraveldata(sensor_descriptions)

    assert len(results) == 1
    result = results[0]
    assert result.sensor_name == 'CEC123'
    assert result.flow_pax_per_hour == expected_ped_count
    mock_cache.write.assert_called_once()
