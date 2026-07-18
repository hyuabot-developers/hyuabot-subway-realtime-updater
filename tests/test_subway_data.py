import asyncio
import datetime
from unittest.mock import MagicMock, patch

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
        get_realtime_data(session, 1004, "4호선")
        get_realtime_data(session, 1071, "수인분당선")
        get_realtime_data(session, 1093, "서해선")

        # Check if the data is inserted
        arrival_list = session.query(SubwayRealtime).all()
        for arrival_item in arrival_list:  # type: SubwayRealtime
            assert isinstance(arrival_item.station_id, str)
            assert isinstance(arrival_item.up_down_type, str)
            assert isinstance(arrival_item.arrival_seq, int)
            assert isinstance(arrival_item.remaining_stop_count, int)
            assert isinstance(arrival_item.remaining_time, datetime.timedelta)
            assert isinstance(arrival_item.terminal_station_id, str)
            assert isinstance(arrival_item.current_station_name, str)
            assert isinstance(arrival_item.train_number, str)
            assert isinstance(arrival_item.last_updated_time, datetime.datetime)
            assert isinstance(arrival_item.is_express_train, bool)
            assert isinstance(arrival_item.is_last_train, bool)
            assert isinstance(arrival_item.status_code, int)


@pytest.mark.parametrize(
    "payload",
    [
        {"realtimePositionList": []},
        {"RESULT": {"CODE": "INFO-200", "MESSAGE": "No data"}},
        {"errorMessage": {"code": "INFO-200", "message": "No data"}},
    ],
)
def test_empty_response_clears_stale_realtime_data(payload):
    session = MagicMock(spec=Session)
    session.execute.side_effect = [
        [("K449", 1, datetime.timedelta())],
        [("K258", 2, datetime.timedelta(minutes=10))],
        MagicMock(),
    ]
    response = MagicMock()
    response.json.return_value = payload

    with patch("scripts.realtime.requests.get", return_value=response) as request:
        get_realtime_data(session, 1071, "수인분당선")

    request.assert_called_once()
    assert request.call_args.kwargs["timeout"] == 5
    response.raise_for_status.assert_called_once_with()
    assert session.execute.call_count == 3
    delete_statement = session.execute.call_args_list[-1].args[0]
    assert set(delete_statement.compile().params["station_id_1"]) == {"K449", "K258"}
    session.commit.assert_called_once_with()


def test_unsuccessful_response_preserves_stale_realtime_data():
    session = MagicMock(spec=Session)
    session.execute.return_value = [("S021", 1, datetime.timedelta())]
    response = MagicMock()
    response.json.return_value = {"RESULT": {"CODE": "ERROR-500", "MESSAGE": "Server error"}}

    with patch("scripts.realtime.requests.get", return_value=response), pytest.raises(RuntimeError):
        get_realtime_data(session, 1093, "서해선")

    assert session.execute.call_count == 1
    session.commit.assert_not_called()
