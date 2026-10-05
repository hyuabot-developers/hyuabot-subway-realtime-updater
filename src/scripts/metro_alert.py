import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models import SubwayAlert


DEFAULT_SERVICE_URL = "https://apis.data.go.kr/6110000/SeoulMetroAlertService/getSubwayAlertList"
SOURCE = "SEOUL_METRO"
SUPPORTED_ROUTE_IDS = {1004, 1071, 1093}
ROUTE_NAMES = {
    "4호선": 1004,
    "수인분당선": 1071,
    "수인선": 1071,
    "분당선": 1071,
    "서해선": 1093,
}


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    response = payload.get("response", payload)
    header = response.get("header", {})
    code = str(header.get("resultCode", "00"))
    if code not in {"0", "00"}:
        raise RuntimeError(f"Seoul Metro alert request failed: {code}")
    body = response.get("body", {})
    body_items = body.get("items", [])
    items = body_items.get("item", []) if isinstance(body_items, dict) else body_items
    if isinstance(items, dict):
        return [items]
    return items or []


def _date_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _route_id(item: dict[str, Any]) -> int | None:
    raw = item.get("routeId") or item.get("lineId")
    route_id: int | None = None
    if raw is not None:
        try:
            route_id = int(raw)
        except (TypeError, ValueError):
            pass
    if route_id is None:
        route_name = str(item.get("lineName") or item.get("routeName") or item.get("lineNm") or "")
        route_id = next((value for name, value in ROUTE_NAMES.items() if name in route_name), None)
    return route_id if route_id in SUPPORTED_ROUTE_IDS else None


def parse_subway_alerts(payload: dict[str, Any], now: datetime | None = None) -> list[dict[str, Any]]:
    current_time = now or datetime.now(timezone.utc)
    alerts = []
    for item in _items(payload):
        route_id = _route_id(item)
        title = str(item.get("title") or item.get("alertTitle") or item.get("noticeTitle") or "").strip()
        if route_id is None or not title:
            continue
        starts_at = _date_time(item.get("startsAt") or item.get("startAt") or item.get("startDateTime"))
        ends_at = _date_time(item.get("endsAt") or item.get("endAt") or item.get("endDateTime"))
        if starts_at and starts_at > current_time:
            continue
        if ends_at and ends_at < current_time:
            continue
        raw_id = item.get("alertId") or item.get("noticeId") or item.get("id")
        identity = str(raw_id) if raw_id else hashlib.sha1(
            f"{route_id}|{title}|{starts_at}".encode(),
        ).hexdigest()
        alerts.append({
            "alert_id": identity[:50],
            "route_id": route_id,
            "title": title,
            "content": item.get("content") or item.get("alertContent") or item.get("noticeContent"),
            "starts_at": starts_at,
            "ends_at": ends_at,
            "source": SOURCE,
            "updated_at": current_time,
        })
    return alerts


def refresh_subway_alerts(db_session: Session, now: datetime | None = None) -> int:
    api_key = os.getenv("SEOUL_METRO_ALERT_API_KEY")
    if not api_key:
        logging.warning("Skipping Seoul Metro alert API because SEOUL_METRO_ALERT_API_KEY is not set.")
        return 0
    current_time = now or datetime.now(timezone.utc)
    service_url = os.getenv("SEOUL_METRO_ALERT_API_URL", DEFAULT_SERVICE_URL)
    response = requests.get(
        service_url,
        params={"serviceKey": api_key, "dataType": "JSON", "numOfRows": "100"},
        timeout=10,
    )
    response.raise_for_status()
    alerts = parse_subway_alerts(response.json(), current_time)
    alert_ids = [alert["alert_id"] for alert in alerts]
    stale_query = delete(SubwayAlert).where(SubwayAlert.source == SOURCE)
    if alert_ids:
        stale_query = stale_query.where(SubwayAlert.alert_id.not_in(alert_ids))
    db_session.execute(stale_query)
    if alerts:
        statement = insert(SubwayAlert).values(alerts)
        db_session.execute(
            statement.on_conflict_do_update(
                index_elements=["alert_id"],
                set_={
                    "route_id": statement.excluded.route_id,
                    "title": statement.excluded.title,
                    "content": statement.excluded.content,
                    "starts_at": statement.excluded.starts_at,
                    "ends_at": statement.excluded.ends_at,
                    "updated_at": statement.excluded.updated_at,
                },
            ),
        )
    return len(alerts)
