import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.main import is_vercel_preview_deployment, nowcast_cache_autorefresh_iteration, refresh_cached_nowcast


@pytest.mark.asyncio
async def test_refresh_cached_nowcast_with_trade_secrets(monkeypatch):
    fake_sensor_data = ['sensor1', 'sensor2']
    fake_nowcast = {'oa001': 0.7, 'oa002': 0.3}

    monkeypatch.setattr('engine.main.TRADE_SECRETS_AVAILABLE', True)
    monkeypatch.setattr('engine.main.poll_all_sensors', AsyncMock(return_value=fake_sensor_data))
    monkeypatch.setattr('engine.main.generate_nowcast', lambda sensors: fake_nowcast)

    mock_cache = MagicMock()
    monkeypatch.setattr('engine.main.NOWCAST_CACHE', mock_cache)

    result = await refresh_cached_nowcast()

    assert result == fake_nowcast
    mock_cache.write.assert_called_once_with(fake_nowcast)


@pytest.mark.asyncio
async def test_refresh_cached_nowcast_without_trade_secrets(monkeypatch, tmp_path):
    monkeypatch.setattr('engine.main.TRADE_SECRETS_AVAILABLE', False)

    # Create a fake mock_nowcast.json file in a fake package structure
    mock_data = {'oa003': 0.1}
    mock_file = tmp_path / 'mock_nowcast.json'
    mock_file.write_text(json.dumps(mock_data), encoding='utf-8')

    # Patch files('engine') to return tmp_path
    monkeypatch.setattr('engine.main.files', lambda _: tmp_path)

    mock_cache = MagicMock()
    monkeypatch.setattr('engine.main.NOWCAST_CACHE', mock_cache)

    with patch('engine.main.log.warning') as mock_log:
        result = await refresh_cached_nowcast()

    assert result == mock_data
    mock_cache.write.assert_called_once_with(mock_data)
    mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_autorefresh_runs_when_time_is_in_window(monkeypatch):
    fake_now = datetime(2024, 4, 30, 10, 0)  # Tuesday 10am

    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_FIRST_HOUR', 9)
    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_LAST_HOUR', 17)
    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_FIRST_WEEKDAY', 0)
    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_LAST_WEEKDAY', 4)

    mock_refresh = AsyncMock()
    monkeypatch.setattr('engine.main.refresh_cached_nowcast', mock_refresh)

    with patch('engine.main.log.info') as mock_log:
        await nowcast_cache_autorefresh_iteration(fake_now)

    mock_refresh.assert_awaited_once()
    assert any('Autorefreshing cache' in call.args[0] for call in mock_log.call_args_list)


@pytest.mark.asyncio
async def test_autorefresh_skips_on_weekend(monkeypatch):
    fake_now = datetime(2024, 4, 28, 10, 0)  # Sunday

    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_FIRST_HOUR', 9)
    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_LAST_HOUR', 17)
    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_FIRST_WEEKDAY', 0)
    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_LAST_WEEKDAY', 4)

    mock_refresh = AsyncMock()
    monkeypatch.setattr('engine.main.refresh_cached_nowcast', mock_refresh)

    with patch('engine.main.log.debug') as mock_log:
        await nowcast_cache_autorefresh_iteration(fake_now)

    mock_refresh.assert_not_awaited()
    assert any('did not autorefresh cache' in call.args[0] for call in mock_log.call_args_list)


@pytest.mark.asyncio
async def test_autorefresh_handles_errors(monkeypatch):
    fake_now = datetime(2024, 4, 30, 10, 0)  # In bounds

    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_FIRST_HOUR', 9)
    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_LAST_HOUR', 17)
    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_FIRST_WEEKDAY', 0)
    monkeypatch.setattr('engine.main.config.NOWCAST_CACHE_AUTO_REFRESH_LAST_WEEKDAY', 4)

    async def raise_error():
        raise RuntimeError('oh no!')

    monkeypatch.setattr('engine.main.refresh_cached_nowcast', raise_error)

    mock_alert = patch('engine.main.alert_via_email').start()
    mock_log = patch('engine.main.log.error').start()

    await nowcast_cache_autorefresh_iteration(fake_now)

    mock_alert.assert_called_once()
    mock_log.assert_called()
    assert 'oh no!' in mock_alert.call_args[0][0]

    patch.stopall()


@pytest.mark.parametrize(
    'url',
    [
        'https://edicrowds-frontend-abc123-tristan-goss-projects.vercel.app',
        'https://edicrowds-frontend-preview-7fa9c7-tristan-goss-projects.vercel.app',
        'https://edicrowds-frontend-xyz-123-tristan-goss-projects.vercel.app',
    ],
)
def test_valid_vercel_preview_urls(url):
    assert is_vercel_preview_deployment(url) is True


@pytest.mark.parametrize(
    'url',
    [
        'http://edicrowds-frontend-abc123-tristan-goss-projects.vercel.app',  # wrong scheme
        'https://edicrowds-frontend--tristan-goss-projects.vercel.app',  # empty slug
        'https://otherdomain.com',  # totally different
        'https://edicrowds-frontend-abc123-tristan.vercel.app',  # wrong subdomain
        'https://vercel.app',  # bare domain
    ],
)
def test_invalid_vercel_preview_urls(url):
    assert is_vercel_preview_deployment(url) is False
