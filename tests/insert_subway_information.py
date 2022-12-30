import csv

from aiohttp import ClientSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models import SubwayRoute, SubwayStation, SubwayRouteStation


async def initialize_subway_data(db_session: Session):
    await insert_subway_route(db_session)
    await insert_subway_station(db_session)


async def insert_subway_route(db_session: Session):
    route_list = [
        dict(route_id=1001, route_name="1호선"),
        dict(route_id=1002, route_name="2호선"),
        dict(route_id=1003, route_name="3호선"),
        dict(route_id=1004, route_name="4호선"),
        dict(route_id=1005, route_name="5호선"),
        dict(route_id=1006, route_name="6호선"),
        dict(route_id=1007, route_name="7호선"),
        dict(route_id=1008, route_name="8호선"),
        dict(route_id=1009, route_name="9호선"),
        dict(route_id=1071, route_name="수인분당선"),
        dict(route_id=1077, route_name="신분당선"),
        dict(route_id=1091, route_name="자기부상선"),
        dict(route_id=1092, route_name="우이신설선"),
        dict(route_id=1163, route_name="경의중앙선"),
        dict(route_id=1165, route_name="공항철도"),
        dict(route_id=1167, route_name="경춘선"),
    ]
    insert_statement = insert(SubwayRoute).values(route_list)
    insert_statement = insert_statement.on_conflict_do_update(
        index_elements=["route_id"],
        set_=dict(route_name=insert_statement.excluded.route_name),
    )
    db_session.execute(insert_statement)
    db_session.commit()


async def insert_subway_station(db_session: Session):
    base_url = "https://raw.githubusercontent.com/hyuabot-developers/hyuabot-subway-timetable/main"
    supported_routes = [1004, 1071]
    station_list: list[dict] = []
    station_name_list: list[dict] = []
    station_name_dict = {
        "신길온": "신길온천", "평촌동": "평촌", "과천청": "과천정부청사", "경마공": "경마공원", "총신대": "이수",
        "4이촌": "이촌", "숙대입": "숙대입구", "4서울": "서울역", "4충무": "충무로", "4동운": "동대문역사문화공원",
        "4동대": "동대문", "한성대": "한성대입구", "성신여": "성신여대입구", "미아4": "미아사거리", "4창동": "창동",
        "신인천": "인천", "남동인": "남동인더스파크", "인천논": "인천논현", "소래포": "소래포구", "신수원": "수원",
        "수원시": "수원시청", "매탄권": "매탄권선", "구룡역": "구룡", "강남구": "강남구청", "로데오": "압구정로데오",
    }
    for route_id in supported_routes:
        url = f"{base_url}/{route_id}/station.csv"
        async with ClientSession() as session:
            async with session.get(url) as response:
                reader = csv.reader((await response.text()).splitlines(), delimiter=",")
                for row_index, (station_number, station_name, cumulative_time) in enumerate(reader):
                    if station_name in station_name_dict.keys():
                        station_name = station_name_dict[station_name]
                    station_list.append(
                        dict(
                            station_id=station_number,
                            route_id=route_id,
                            station_name=station_name,
                            station_sequence=row_index,
                            cumulative_time=cumulative_time,
                        ),
                    )
                    station_name_list.append(dict(station_name=station_name))
    insert_statement = insert(SubwayStation).values(station_name_list)
    insert_statement = insert_statement.on_conflict_do_nothing()
    db_session.execute(insert_statement)
    db_session.commit()

    insert_statement = insert(SubwayRouteStation).values(station_list)
    insert_statement = insert_statement.on_conflict_do_update(
        index_elements=["station_id"],
        set_=dict(
            route_id=insert_statement.excluded.route_id,
            station_name=insert_statement.excluded.station_name,
            cumulative_time=insert_statement.excluded.cumulative_time,
            station_sequence=insert_statement.excluded.station_sequence,
        ),
    )
    db_session.execute(insert_statement)
    db_session.commit()
