import os
from datetime import timedelta, datetime

import requests
from pytz import timezone
from sqlalchemy import select, and_, delete, insert
from sqlalchemy.orm import Session

from models import SubwayRealtime, SubwayRouteStation


SUPPORT_STATION_NAMES_BY_ROUTE_ID = {
    1004: ["한대앞", "오이도"],
    1071: ["한대앞", "오이도"],
    1093: ["초지"],
}


def get_realtime_data(db_session: Session, route_id: int, route_name: str) -> None:
    auth_key = os.getenv("METRO_AUTH_KEY")
    if auth_key is None:
        count = 5
        auth_key = "sample"
    else:
        count = 60
    url = f"http://swopenapi.seoul.go.kr/api/subway/{auth_key}/json/" \
          f"realtimePosition/0/{count}/{route_name}"
    arrival_list: dict[str, list[dict]] = {}
    train_number_list: dict[str, list[str]] = {}
    support_station_name_list = SUPPORT_STATION_NAMES_BY_ROUTE_ID.get(route_id, [])
    support_station_list: list[dict] = []
    for support_station_name in support_station_name_list:
        support_station_query = select(
            SubwayRouteStation.station_id, SubwayRouteStation.station_seq,
            SubwayRouteStation.cumulative_time).where(and_(SubwayRouteStation.station_name == support_station_name,
                                                           SubwayRouteStation.route_id == route_id))
        station_id, station_seq, cumulative_time = "", 0, timedelta(seconds=0)
        for row in db_session.execute(support_station_query):
            station_id, station_seq, cumulative_time = row
            break
        if not station_id:
            raise RuntimeError("Failed to get start station id")
        support_station_list.append({
            "station_id": station_id,
            "station_seq": station_seq,
            "cumulative_time": cumulative_time,
        })
    response = requests.get(url)
    response_json = response.json()
    kst = timezone("Asia/Seoul")
    if "realtimePositionList" in response_json.keys():
        realtime_position_list = response_json["realtimePositionList"]
        for realtime_position_item in realtime_position_list:
            current_station = realtime_position_item["statnNm"]
            train_number = realtime_position_item["trainNo"]
            updated_time = realtime_position_item["recptnDt"]
            heading = realtime_position_item["updnLine"]
            terminal_station = realtime_position_item["statnTnm"]
            status_code = realtime_position_item["trainSttus"]
            is_express_train = realtime_position_item["directAt"]
            is_last_train = realtime_position_item["lstcarAt"]

            # 현재 위치 조회
            current_location_query = select(
                SubwayRouteStation.station_id,
                SubwayRouteStation.station_seq, SubwayRouteStation.cumulative_time,
            ).where(and_(
                SubwayRouteStation.station_name == current_station,
                SubwayRouteStation.route_id == route_id))
            current_station_id, current_station_seq, current_cumulative_time = "", 0, 0.0
            for row in db_session.execute(current_location_query):
                current_station_id, current_station_seq, current_cumulative_time = row
                break
            if not current_station_id:
                continue

            # 종착역 조회
            terminal_station_query = select(
                SubwayRouteStation.station_id,
                SubwayRouteStation.station_seq,
            ).where(and_(
                SubwayRouteStation.station_name == terminal_station,
                SubwayRouteStation.route_id == route_id))
            terminal_station_id, terminal_station_seq = "", 0
            for terminal_station_item in db_session.execute(terminal_station_query):
                terminal_station_id, terminal_station_seq = terminal_station_item
                break
            if not terminal_station_id:
                continue
            for support_station_index, support_station in enumerate(support_station_list):
                # 데이터 추가
                if int(heading) == 0 and \
                        not (terminal_station_seq <= support_station["station_seq"] < current_station_seq):
                    continue
                elif int(heading) == 1 and \
                        not (current_station_seq < support_station["station_seq"] <= terminal_station_seq):
                    continue
                if support_station["station_id"] not in arrival_list.keys():
                    arrival_list[support_station["station_id"]] = []
                    train_number_list[support_station["station_id"]] = []
                if train_number in train_number_list[support_station["station_id"]]:
                    arrival_list[support_station["station_id"]].remove(
                        arrival_list[support_station["station_id"]]
                        [train_number_list[support_station["station_id"]].index(train_number)])
                    train_number_list[support_station["station_id"]].remove(train_number)
                train_number_list[support_station["station_id"]].append(train_number)
                updated_at = kst.localize(datetime.strptime(updated_time, "%Y-%m-%d %H:%M:%S"))
                arrival_list[support_station["station_id"]].append({
                    "station_id": support_station["station_id"],
                    "current_station_name": current_station,
                    "remaining_stop_count": abs(current_station_seq - support_station["station_seq"]),
                    "remaining_time": abs(current_cumulative_time - support_station["cumulative_time"]),
                    "up_down_type": heading,
                    "terminal_station_id": terminal_station_id,
                    "train_number": train_number,
                    "last_updated_time": updated_at,
                    "is_express_train": is_express_train == 1,
                    "is_last_train": is_last_train == 1,
                    "status_code": status_code,
                })
    up_arrival_sequence, down_arrival_sequence = 0, 0
    for station_id in arrival_list.keys():
        for arrival_item in sorted(arrival_list[station_id], key=lambda x: x["remaining_time"]):
            if int(arrival_item["up_down_type"]) == 0:
                arrival_item["arrival_seq"] = up_arrival_sequence
                up_arrival_sequence += 1
            else:
                arrival_item["arrival_seq"] = down_arrival_sequence
                down_arrival_sequence += 1
        db_session.execute(delete(SubwayRealtime).where(SubwayRealtime.station_id == station_id))
        if arrival_list[station_id]:
            insert_statement = insert(SubwayRealtime).values(arrival_list[station_id])
            db_session.execute(insert_statement)
    db_session.commit()
