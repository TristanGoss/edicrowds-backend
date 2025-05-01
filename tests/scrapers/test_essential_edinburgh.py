from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from scrapers import essential_edinburgh


@pytest.fixture
def diurnal_mock_config(monkeypatch):
    monkeypatch.setattr('scrapers.essential_edinburgh.WORKDAYS_PER_WEEK', 5)
    monkeypatch.setattr('scrapers.essential_edinburgh.HOURS_PER_DAY', 24)

    weekday = [1] * 8 + [2] * 8 + [1] * 8  # flatter lunch peak (total = 32)
    weekend = [1] * 24  # flat distribution
    monkeypatch.setattr(
        'scrapers.essential_edinburgh.config',
        type('config', (), {'EE_WEEKDAY_DIURNAL': weekday, 'EE_WEEKEND_DIURNAL': weekend}),
    )


@pytest.fixture
def mock_monday_of_week(monkeypatch):
    monkeypatch.setattr('scrapers.essential_edinburgh.monday_of_week', lambda week, year=None: date(2024, 4, 1))


@pytest.fixture
def mock_today(monkeypatch):
    monkeypatch.setattr(
        'scrapers.essential_edinburgh.date', type('MockDate', (), {'today': staticmethod(lambda: date(2024, 4, 8))})
    )


def test_identity_transform():
    transform = essential_edinburgh.get_pixel_to_data_transform(
        pix_1=(0, 0), data_1=(0, 0), pix_2=(1, 1), data_2=(1, 1)
    )

    xs = np.array([0, 0.5, 1])
    ys = np.array([0, 0.5, 1])
    data_xs, data_ys = transform(xs, ys)

    np.testing.assert_allclose(data_xs, xs)
    np.testing.assert_allclose(data_ys, ys)


def test_scaling_and_offset():
    transform = essential_edinburgh.get_pixel_to_data_transform(
        pix_1=(10, 20), data_1=(100, 200), pix_2=(20, 40), data_2=(200, 400)
    )

    xs = np.array([10, 15, 20])
    ys = np.array([20, 30, 40])
    data_xs, data_ys = transform(xs, ys)

    expected_xs = np.array([100, 150, 200])
    expected_ys = np.array([200, 300, 400])

    np.testing.assert_allclose(data_xs, expected_xs)
    np.testing.assert_allclose(data_ys, expected_ys)


def test_non_uniform_transform():
    transform = essential_edinburgh.get_pixel_to_data_transform(
        pix_1=(0, 0), data_1=(0, 0), pix_2=(2, 4), data_2=(10, 100)
    )

    xs = np.array([0, 1, 2])
    ys = np.array([0, 2, 4])
    data_xs, data_ys = transform(xs, ys)

    expected_xs = np.array([0, 5, 10])
    expected_ys = np.array([0, 50, 100])

    np.testing.assert_allclose(data_xs, expected_xs)
    np.testing.assert_allclose(data_ys, expected_ys)


def test_raises_on_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        essential_edinburgh.get_pixel_to_data_transform(
            pix_1=(0, 0),
            data_1=(0, 0),
            pix_2=(0, 1),
            data_2=(1, 2),  # pix_x2 == pix_x1 triggers divide-by-zero
        )


@pytest.mark.parametrize(
    'filename, last_yvals',
    [
        ('PrincesStExample.jpg', [160, 190, 147]),
        ('RoseStExample.jpg', [103, 93]),
    ],
)
def test_extract_lines_from_graph(filename, last_yvals):
    image_path = Path('tests/test_inputs/essential_edinburgh') / filename
    image_bytes = image_path.read_bytes()

    lines = essential_edinburgh.extract_lines_from_graph(image_bytes)
    for line, last_yval in zip(lines, last_yvals):
        line_yvals = line[1]
        assert line_yvals[-1] == last_yval


def test_monday_of_week_is_monday():
    for week in [1, 10, 25, 52]:
        d = essential_edinburgh.monday_of_week(week, 2024)
        assert d.weekday() == 0  # Monday is 0 in Python's weekday()


def test_monday_of_week_known_values():
    # Known values based on the function logic (not ISO week)
    # Jan 1, 2024 is a Monday → week 1 starts on Jan 1
    assert essential_edinburgh.monday_of_week(1, 2024) == date(2024, 1, 1)
    # Week 2: one week after Jan 1
    assert essential_edinburgh.monday_of_week(2, 2024) == date(2024, 1, 8)

    # Jan 1, 2023 is a Sunday → first Monday before/on Jan 1 is Dec 26, 2022
    assert essential_edinburgh.monday_of_week(1, 2023) == date(2022, 12, 26)
    assert essential_edinburgh.monday_of_week(2, 2023) == date(2023, 1, 2)


def test_monday_of_week_defaults_to_this_year(monkeypatch):
    monkeypatch.setattr('scrapers.essential_edinburgh.date', lambda y, m, d: date(2025, 3, 20))  # mock today's date
    d = essential_edinburgh.monday_of_week(1)
    assert d.year in [2024, 2025]  # depends on Jan 1 weekday, but should not raise


def test_extract_most_recent_measurements_christmas_and_new_year_averaging(monkeypatch):
    monkeypatch.setattr('scrapers.essential_edinburgh.WEEKS_PER_YEAR', 52)

    x = np.arange(1, 53)  # 52 weeks
    y1 = np.arange(52) + 100
    y2 = np.arange(52) + 200

    data = {'Sensor A': [(x, y1), (x, y2)]}

    result = essential_edinburgh.extract_most_recent_measurements(data)

    expected_avg = int(np.mean([y1[0], y1[-1], y2[0], y2[-1]]))
    assert result['Sensor A'] == expected_avg


def test_extract_most_recent_measurements_uses_shortest_series_last_y_value(
    mock_monday_of_week, mock_today, monkeypatch
):
    monkeypatch.setattr('scrapers.essential_edinburgh.WEEKS_PER_YEAR', 52)

    # First result ends at week 30, second at week 40
    x1 = np.arange(1, 31)
    y1 = np.arange(30) + 50

    x2 = np.arange(1, 41)
    y2 = np.arange(40) + 100

    data = {'Sensor B': [(x1, y1), (x2, y2)]}

    result = essential_edinburgh.extract_most_recent_measurements(data)

    assert result['Sensor B'] == y1[-1]  # Should return last y of the shortest series


def test_extract_most_recent_measurements_handles_multiple_keys(mock_monday_of_week, mock_today, monkeypatch):
    monkeypatch.setattr('scrapers.essential_edinburgh.WEEKS_PER_YEAR', 52)
    expected_output = 123

    x = np.arange(1, 53)
    y = np.ones(52) * expected_output

    data = {'Sensor A': [(x, y)], 'Sensor B': [(x, y)]}

    result = essential_edinburgh.extract_most_recent_measurements(data)
    for value in result.values():
        assert value == expected_output


def test_weekday_diurnal_correction(diurnal_mock_config):
    dt = datetime(2024, 4, 17, 10)  # Wednesday at 10am
    result = essential_edinburgh.correct_for_diurnal_and_day_of_week({'Rose St': 7000}, dt)

    # Expected fraction at 10am: part of middle third (weight 2 / total weight 32)
    expected_fraction = 2 / sum([1] * 8 + [2] * 8 + [1] * 8)
    expected_value = 7000 / 7 * expected_fraction

    assert 'Rose St' in result
    np.testing.assert_approx_equal(result['Rose St'], expected_value)


def test_weekend_diurnal_correction(diurnal_mock_config):
    dt = datetime(2024, 4, 14, 15)  # Sunday at 3pm
    result = essential_edinburgh.correct_for_diurnal_and_day_of_week({'Princes St': 14000}, dt)

    expected_fraction = 1 / 24
    expected_value = 14000 / 7 * expected_fraction

    np.testing.assert_approx_equal(result['Princes St'], expected_value)


def test_invalid_diurnal_model_length(monkeypatch):
    dt = datetime(2024, 4, 17, 10)
    monkeypatch.setattr('scrapers.essential_edinburgh.WORKDAYS_PER_WEEK', 5)
    monkeypatch.setattr('scrapers.essential_edinburgh.HOURS_PER_DAY', 24)
    monkeypatch.setattr(
        'scrapers.essential_edinburgh.config',
        type(
            'config',
            (),
            {
                'EE_WEEKDAY_DIURNAL': [1] * 23,  # wrong length
                'EE_WEEKEND_DIURNAL': [1] * 24,
            },
        ),
    )

    with pytest.raises(AssertionError, match='Diurnal model needs to have length 24'):
        essential_edinburgh.correct_for_diurnal_and_day_of_week({'Any St': 1000}, dt)


@pytest.mark.asyncio
async def test_scrape_dashboard_extracts_data(monkeypatch):
    # Mock image src HTML
    html = """
    <html><body>
    <img src="https://mockcdn.com/images/PS-52-Week_Update.png">
    <img src="https://mockcdn.com/images/RoseSt-52-Week_Update.png">
    </body></html>
    """
    monkeypatch.setattr('scrapers.essential_edinburgh.scrape_urls', AsyncMock(return_value=[html]))

    # Mock requests.get to return fake image bytes
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.content = b'fake-image-bytes'
    monkeypatch.setattr('scrapers.essential_edinburgh.requests.get', lambda url: mock_response)

    # Mock extract_lines_from_graph
    correct_ps_measurement = 20
    monkeypatch.setattr(
        'scrapers.essential_edinburgh.extract_lines_from_graph',
        lambda _: [(np.array([1, 2]), np.array([10, correct_ps_measurement]))],
    )

    # Mock pixel-to-data transform to identity
    monkeypatch.setattr(
        'scrapers.essential_edinburgh.get_pixel_to_data_transform', lambda **kwargs: lambda x, y: (x, y)
    )

    # Patch config values
    monkeypatch.setattr(
        'scrapers.essential_edinburgh.config',
        type(
            'config',
            (),
            {
                'EE_PAGE_LOAD_INDICATOR_SELECTOR': '#content',
                'EE_PRINCES_IMG_TO_DATA_CALIB': {},
                'EE_ROSE_IMG_TO_DATA_CALIB': {},
                'EE_FALLBACK_PRINCES_FOOTFALL_PAX_PER_WEEK': 999,
                'EE_FALLBACK_ROSE_FOOTFALL_PAX_PER_WEEK': 888,
            },
        ),
    )

    result = await essential_edinburgh.scrape_dashboard()

    assert 'EE001' in result and 'EE002' in result
    assert isinstance(result['EE001'], list)
    assert result['EE001'][0][0][0] == 1
    assert result['EE001'][0][1][1] == correct_ps_measurement


@pytest.mark.asyncio
async def test_scrape_dashboard_uses_fallback(monkeypatch):
    html = "<html><body><img src='unrelated.png'></body></html>"
    monkeypatch.setattr('scrapers.essential_edinburgh.scrape_urls', AsyncMock(return_value=[html]))

    PS_fallback = 123
    RS_fallback = 456
    monkeypatch.setattr(
        'scrapers.essential_edinburgh.config',
        type(
            'config',
            (),
            {
                'EE_PAGE_LOAD_INDICATOR_SELECTOR': '#content',
                'EE_PRINCES_IMG_TO_DATA_CALIB': {},
                'EE_ROSE_IMG_TO_DATA_CALIB': {},
                'EE_FALLBACK_PRINCES_FOOTFALL_PAX_PER_WEEK': PS_fallback,
                'EE_FALLBACK_ROSE_FOOTFALL_PAX_PER_WEEK': RS_fallback,
            },
        ),
    )

    result = await essential_edinburgh.scrape_dashboard()

    assert result['EE001'][0][1][0] == PS_fallback
    assert result['EE002'][0][1][0] == RS_fallback
