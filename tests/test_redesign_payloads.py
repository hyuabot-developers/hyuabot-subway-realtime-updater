import json
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from scripts.korail import parse_train_delay
from scripts.metro_alert import parse_subway_alerts, refresh_subway_alerts
from scripts.station_arrival import merge_station_arrivals, parse_station_arrivals


FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_station_arrival_fixture_merges_only_matching_train_and_direction():
    positions = [{
        "train_number": "001",
        "up_down_type": "0",
        "arrival_message": None,
        "arrival_message_detail": None,
        "remaining_seconds": None,
        "arrival_code": None,
    }, {
        "train_number": "002",
        "up_down_type": "0",
        "arrival_message": None,
        "arrival_message_detail": None,
        "remaining_seconds": None,
        "arrival_code": None,
    }]

    merge_station_arrivals(positions, parse_station_arrivals(fixture("station_arrival.json")))

    assert positions[0]["arrival_message"] == "전역 도착"
    assert positions[0]["arrival_message_detail"] == "이번 역은 한대앞역"
    assert positions[0]["remaining_seconds"] == 75
    assert positions[0]["arrival_code"] == 1
    assert positions[1]["arrival_message"] is None


def test_korail_fixture_calculates_latest_station_delay():
    now = datetime(2026, 10, 4, 1, 0, tzinfo=timezone.utc)

    delay = parse_train_delay(fixture("korail_train_operation.json"), date(2026, 10, 4), "001", 1004, now)

    assert delay == {
        "run_date": date(2026, 10, 4),
        "train_number": "001",
        "route_id": 1004,
        "delay_minutes": 3,
        "reference_station_name": "한대앞",
        "updated_at": now,
    }


def test_alert_fixture_filters_expired_and_maps_active_routes():
    now = datetime(2026, 10, 4, 1, 0, tzinfo=timezone.utc)

    alerts = parse_subway_alerts(fixture("metro_alerts.json"), now)

    assert len(alerts) == 1
    assert alerts[0]["alert_id"] == "alert-1"
    assert alerts[0]["route_id"] == 1004
    assert alerts[0]["title"] == "4호선 운행 지연"


def test_alert_refresh_uses_fixture_and_upserts_with_source_scope(monkeypatch):
    monkeypatch.setenv("SEOUL_METRO_ALERT_API_KEY", "fixture-key")
    response = MagicMock()
    response.json.return_value = fixture("metro_alerts.json")
    session = MagicMock(spec=Session)
    now = datetime(2026, 10, 4, 1, 0, tzinfo=timezone.utc)

    with patch("scripts.metro_alert.requests.get", return_value=response) as request:
        count = refresh_subway_alerts(session, now)

    assert count == 1
    request.assert_called_once()
    assert session.execute.call_count == 2
    assert "subway_alert" in str(session.execute.call_args_list[0].args[0])


def test_alert_refresh_skips_without_key(monkeypatch):
    monkeypatch.delenv("SEOUL_METRO_ALERT_API_KEY", raising=False)
    session = MagicMock(spec=Session)

    assert refresh_subway_alerts(session) == 0
    session.execute.assert_not_called()
