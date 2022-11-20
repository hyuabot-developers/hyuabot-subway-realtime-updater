import os

from aiohttp import ClientTimeout, ClientSession
from sqlalchemy import select, and_, delete, insert
from sqlalchemy.orm import Session

from models.subway import SubwayRealtime, SubwayRouteStation


async def get_realtime_data(db_session: Session, route_id: int, route_name: str) -> None:
    auth_key = os.getenv("METRO_AUTH_KEY")
    if auth_key is None:
        count = 5
        auth_key = "sample"
    else:
        count = 60
    url = f"http://swopenapi.seoul.go.kr/api/subway/{auth_key}/json/" \
          f"realtimePosition/0/{count}/{route_name}"
    timeout = ClientTimeout(total=3.0)
    arrival_list: list[dict] = []
    train_number_list: list[str] = []
    current_station = select([
        SubwayRouteStation.station_id, SubwayRouteStation.station_sequence,
        SubwayRouteStation.cumulative_time]).where(and_(SubwayRouteStation.station_name == "한대앞",
                                                        SubwayRouteStation.route_id == route_id))
    campus_station_id, campus_station_sequence, campus_cumulative_time = "", 0, 0.0
    for row in db_session.execute(current_station):
        campus_station_id, campus_station_sequence, campus_cumulative_time = row
        break
    if not campus_station_id:
        raise RuntimeError("Failed to get start station id")
    async with ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            response_json = await response.json()
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
                    current_location_query = select([
                        SubwayRouteStation.station_id,
                        SubwayRouteStation.station_sequence, SubwayRouteStation.cumulative_time
                    ]).where(and_(
                        SubwayRouteStation.station_name == current_station,
                        SubwayRouteStation.route_id == route_id))
                    current_station_id, current_station_sequence, current_cumulative_time = "", 0, 0.0
                    for row in db_session.execute(current_location_query):
                        current_station_id, current_station_sequence, current_cumulative_time = row
                        break
                    if not current_station_id:
                        continue

                    # 종착역 조회
                    terminal_station_query = select([SubwayRouteStation.station_id]).where(and_(
                        SubwayRouteStation.station_name == terminal_station,
                        SubwayRouteStation.route_id == route_id))
                    terminal_station_id = ""
                    for row in db_session.execute(terminal_station_query):
                        terminal_station_id, = row
                        break
                    if not terminal_station_id:
                        continue

                    # 데이터 추가
                    if int(heading) == 0 and \
                            not (terminal_station_id < campus_station_id < current_station_id):
                        continue
                    elif int(heading) == 1 and \
                            not (current_station_id < campus_station_id < terminal_station_id):
                        continue
                    if train_number in train_number_list:
                        arrival_list.remove(arrival_list[train_number_list.index(train_number)])
                        train_number_list.remove(train_number)
                    train_number_list.append(train_number)
                    arrival_list.append(dict(
                        station_id=campus_station_id,
                        current_station_name=current_station,
                        remaining_stop_count=abs(current_station_sequence - campus_station_sequence),
                        remaining_time=abs(current_cumulative_time - campus_cumulative_time),
                        up_down_type=int(heading) == 0,
                        terminal_station_id=terminal_station_id,
                        train_number=train_number,
                        last_updated_time=updated_time,
                        is_express_train=is_express_train == 1,
                        is_last_train=is_last_train == 1,
                        status_code=status_code
                    ))
    up_arrival_sequence, down_arrival_sequence = 0, 0
    for arrival_item in sorted(arrival_list, key=lambda x: x["remaining_time"]):
        if arrival_item["up_down_type"]:
            arrival_item["arrival_sequence"] = up_arrival_sequence
            up_arrival_sequence += 1
        else:
            arrival_item["arrival_sequence"] = down_arrival_sequence
            down_arrival_sequence += 1
    db_session.execute(delete(SubwayRealtime).where(SubwayRealtime.station_id == campus_station_id))
    if arrival_list:
        insert_statement = insert(SubwayRealtime).values(arrival_list)
        db_session.execute(insert_statement)
    db_session.commit()
