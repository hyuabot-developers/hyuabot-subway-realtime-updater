import asyncio
import os
import time

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

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
    get_realtime_data(session, 1004, "4호선")
    get_realtime_data(session, 1071, "수인분당선")
    get_realtime_data(session, 1093, "서해선")
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
