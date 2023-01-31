import asyncio

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
    job_list = [get_realtime_data(session, 1004, "4호선"),
                get_realtime_data(session, 1071, "수인분당선")]
    await asyncio.gather(*job_list)
    session.close()

if __name__ == '__main__':
    asyncio.run(main())
