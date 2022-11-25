import asyncio
import datetime

import pytest
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from scripts.realtime import get_realtime_data
from models import BaseModel
from models import SubwayRealtime
from utils.database import get_db_engine
from tests.insert_subway_information import initialize_subway_data


class TestFetchRealtimeData:
    connection: Engine | None = None
    session_constructor = None
    session: Session | None = None

    @classmethod
    def setup_class(cls):
        cls.connection = get_db_engine()
        cls.session_constructor = sessionmaker(bind=cls.connection)
        # Database session check
        cls.session = cls.session_constructor()
        assert cls.session is not None
        # Migration schema check
        BaseModel.metadata.create_all(cls.connection)
        # Insert initial data
        asyncio.run(initialize_subway_data(cls.session))
        cls.session.commit()
        cls.session.close()

    @pytest.mark.asyncio
    async def test_fetch_realtime_data(self):
        connection = get_db_engine()
        session_constructor = sessionmaker(bind=connection)
        # Database session check
        session = session_constructor()
        # Get list to fetch
        session.execute(delete(SubwayRealtime))
        job_list = [
            get_realtime_data(session, 1004, "4호선"),
            get_realtime_data(session, 1071, "수인분당선")]
        await asyncio.gather(*job_list)

        # Check if the data is inserted
        arrival_list = session.query(SubwayRealtime).all()
        for arrival_item in arrival_list:  # type: SubwayRealtime
            assert type(arrival_item.station_id) is str
            assert type(arrival_item.up_down_type) is str
            assert type(arrival_item.arrival_sequence) is int
            assert type(arrival_item.remaining_stop_count) is int
            assert type(arrival_item.remaining_time) is float
            assert type(arrival_item.terminal_station_id) is str
            assert type(arrival_item.current_station_name) is str
            assert type(arrival_item.train_number) is str
            assert type(arrival_item.last_updated_time) is datetime.datetime
            assert type(arrival_item.is_express_train) is bool
            assert type(arrival_item.is_last_train) is bool
            assert type(arrival_item.status_code) is int
