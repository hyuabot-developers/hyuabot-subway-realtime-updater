import logging
import os
from datetime import date, datetime, timezone
from typing import Any

import requests
from zoneinfo import ZoneInfo
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models import SubwayTrainDelay


TRAIN_OPERATION_URL = os.getenv(
    "KORAIL_TRAIN_OPERATION_API_URL",
    "https://apis.data.go.kr/1613000/TrainOperationInfoService/getTrainOperationInfo",
)


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    response = payload.get("response", payload)
    header = response.get("header", {})
    code = str(header.get("resultCode", "00"))
    if code not in {"0", "00"}:
        raise RuntimeError(f"KORAIL train-operation request failed: {code}")
    body = response.get("body", {})
    body_items = body.get("items", [])
    items = body_items.get("item", []) if isinstance(body_items, dict) else body_items
    return [items] if isinstance(items, dict) else items or []


def _field(item: dict[str, Any], *names: str) -> Any:
    return next((item[name] for name in names if item.get(name) not in (None, "")), None)


def _datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_train_delay(
    payload: dict[str, Any], run_date: date, train_number: str, route_id: int, now: datetime,
) -> dict[str, Any] | None:
    matching_items = [
        item for item in _items(payload)
        if str(_field(item, "trainNo", "trainNumber", "trnNo")) == train_number
    ]
    if not matching_items:
        return None
    matching_items.sort(key=lambda item: int(_field(item, "stationSeq", "oprSeq", "trainOperationSequence") or 0))
    latest = matching_items[-1]
    planned = _datetime(_field(latest, "plannedArrivalTime", "planArrivalTime", "planArvlDt", "trainPlanArvlDt"))
    actual = _datetime(_field(latest, "actualArrivalTime", "arrivalTime", "arvlDt", "trainArvlDt"))
    station_name = _field(latest, "stationName", "stationNm", "stnNm")
    if planned is None or actual is None:
        return None
    return {
        "run_date": run_date,
        "train_number": train_number,
        "route_id": route_id,
        "delay_minutes": int((actual - planned).total_seconds() / 60),
        "reference_station_name": str(station_name) if station_name else None,
        "updated_at": now,
    }


def update_train_delays(
    db_session: Session,
    position_rows: list[dict[str, Any]],
    now: datetime | None = None,
) -> None:
    api_key = os.getenv("KORAIL_API_KEY")
    if not api_key:
        logging.warning("Skipping KORAIL delay API because KORAIL_API_KEY is not set.")
        return
    current_time = now or datetime.now(ZoneInfo("Asia/Seoul"))
    run_date = current_time.date()
    pairs = {(str(row["train_number"]), int(row.get("route_id") or 0)) for row in position_rows}
    values = []
    for train_number, route_id in pairs:
        try:
            response = requests.get(
                TRAIN_OPERATION_URL,
                params={
                    "serviceKey": api_key,
                    "runDate": run_date.strftime("%Y%m%d"),
                    "trainNo": train_number,
                    "dataType": "JSON",
                    "pageNo": "1",
                    "numOfRows": "100",
                },
                timeout=10,
            )
            response.raise_for_status()
            delay = parse_train_delay(response.json(), run_date, train_number, route_id, current_time)
            if delay is not None:
                values.append(delay)
        except Exception as error:  # noqa: BLE001 - one KORAIL train cannot block position data
            logging.warning("Skipping KORAIL delay for train %s: %s", train_number, error)
    if not values:
        return
    statement = insert(SubwayTrainDelay).values(values)
    db_session.execute(
        statement.on_conflict_do_update(
            index_elements=["run_date", "train_number"],
            set_={
                "route_id": statement.excluded.route_id,
                "delay_minutes": statement.excluded.delay_minutes,
                "reference_station_name": statement.excluded.reference_station_name,
                "updated_at": statement.excluded.updated_at,
            },
        ),
    )
