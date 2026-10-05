import json
from pathlib import Path

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
