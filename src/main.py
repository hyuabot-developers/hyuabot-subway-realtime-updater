import asyncio
import logging
import os
import time

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from models import SubwayRealtime, SubwayRouteStation
from scripts.korail import update_train_delays
from scripts.metro_alert import refresh_subway_alerts
from scripts.realtime import get_realtime_data
from utils.database import get_db_engine, get_master_db_engine


async def main():
    connection = get_db_engine()
    session_constructor = sessionmaker(bind=connection)
    session = session_constructor()
    if session is None:
        raise RuntimeError("Failed to get db session")
    try:
        await execute_script(session)
    except OperationalError:
        connection = get_master_db_engine()
        session_constructor = sessionmaker(bind=connection)
        session = session_constructor()
        if session is None:
            raise RuntimeError("Failed to get db session")
        await execute_script(session)


async def execute_script(session):
    try:
        get_realtime_data(session, 1004, "4호선")
        get_realtime_data(session, 1071, "수인분당선")
        get_realtime_data(session, 1093, "서해선")
        position_query = select(
            SubwayRouteStation.route_id,
            SubwayRealtime.train_number,
            SubwayRealtime.current_station_name,
        ).join(
            SubwayRealtime,
            SubwayRealtime.station_id == SubwayRouteStation.station_id,
        ).where(SubwayRouteStation.route_id.in_((1004, 1071, 1093)))
        position_rows = [
            {"route_id": route_id, "train_number": train_number, "current_station_name": station_name}
            for route_id, train_number, station_name in session.execute(position_query)
        ]
        try:
            update_train_delays(session, position_rows)
        except Exception as error:  # noqa: BLE001 - KORAIL is optional
            logging.warning("KORAIL delay collection skipped: %s", error)
        try:
            refresh_subway_alerts(session)
        except Exception as error:  # noqa: BLE001 - alert feed is optional
            logging.warning("Seoul Metro alert collection skipped: %s", error)
        session.commit()
    finally:
        session.close()


async def run_loop():
    # CronJob fires every minute; loop several times within that window to
    # achieve sub-minute refresh (default: every 15s, 4 iterations per minute).
    iterations = int(os.getenv("LOOP_ITERATIONS", "4"))
    interval = float(os.getenv("LOOP_INTERVAL_SECONDS", "15"))
    for i in range(iterations):
        started_at = time.monotonic()
        try:
            await main()
        except Exception as e:  # noqa: BLE001 - keep loop alive on transient errors
            print("Subway realtime iteration failed:", e)
        if i < iterations - 1:
            await asyncio.sleep(max(0.0, interval - (time.monotonic() - started_at)))


if __name__ == '__main__':
    asyncio.run(run_loop())
