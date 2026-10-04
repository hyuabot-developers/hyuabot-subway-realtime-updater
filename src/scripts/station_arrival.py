import logging
import os
from typing import Any
from urllib.parse import quote

import requests


BASE_URL = "http://swopenapi.seoul.go.kr/api/subway"


def _direction(value: Any) -> str | None:
    text = str(value or "").strip()
    if text in {"0", "상행", "내선"}:
        return "0"
    if text in {"1", "하행", "외선"}:
        return "1"
    return None


def parse_station_arrivals(payload: dict[str, Any]) -> list[dict[str, Any]]:
    arrivals = payload.get("realtimeArrivalList")
    if arrivals is None:
        result_code = payload.get("RESULT", {}).get("CODE")
        error_code = payload.get("errorMessage", {}).get("code")
        if result_code == "INFO-200" or error_code == "INFO-200":
            return []
        raise RuntimeError("Seoul Metro station-arrival response was unsuccessful")
    if not isinstance(arrivals, list):
        raise RuntimeError("Seoul Metro station-arrival response was invalid")
    parsed = []
    for item in arrivals:
        train_number = item.get("btrainNo")
        direction = _direction(item.get("updnLine"))
        if not train_number or direction is None:
            continue
        try:
            seconds = int(item.get("barvlDt")) if item.get("barvlDt") not in (None, "") else None
        except (TypeError, ValueError):
            seconds = None
        try:
            arrival_code = int(item.get("arvlCd")) if item.get("arvlCd") not in (None, "") else None
        except (TypeError, ValueError):
            arrival_code = None
        parsed.append({
            "train_number": str(train_number),
            "up_down_type": direction,
            "arrival_message": item.get("arvlMsg2") or None,
            "arrival_message_detail": item.get("arvlMsg3") or None,
            "remaining_seconds": seconds,
            "arrival_code": arrival_code,
        })
    return parsed


def merge_station_arrivals(position_rows: list[dict[str, Any]], station_arrivals: list[dict[str, Any]]) -> None:
    arrivals_by_train = {
        (arrival["train_number"], arrival["up_down_type"]): arrival
        for arrival in station_arrivals
    }
    for position in position_rows:
        match = arrivals_by_train.get((str(position["train_number"]), str(position["up_down_type"])))
        if match is None:
            continue
        position["arrival_message"] = match["arrival_message"]
        position["arrival_message_detail"] = match["arrival_message_detail"]
        position["remaining_seconds"] = match["remaining_seconds"]
        position["arrival_code"] = match["arrival_code"]


def fetch_station_arrivals(station_name: str) -> list[dict[str, Any]]:
    auth_key = os.getenv("METRO_AUTH_KEY")
    if not auth_key:
        logging.warning("Skipping Seoul Metro station-arrival details because METRO_AUTH_KEY is not set.")
        return []
    url = f"{BASE_URL}/{auth_key}/json/realtimeStationArrival/0/100/{quote(station_name)}"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return parse_station_arrivals(response.json())
