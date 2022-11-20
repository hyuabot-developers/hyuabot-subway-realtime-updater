from sqlalchemy import PrimaryKeyConstraint, Column
from sqlalchemy.sql import sqltypes

from models import BaseModel


class SubwayRouteStation(BaseModel):
    __tablename__ = "subway_route_station"
    station_id = Column(sqltypes.String, primary_key=True)
    station_name = Column(sqltypes.String, nullable=False)
    route_id = Column(sqltypes.Integer, nullable=False)
    station_sequence = Column(sqltypes.Integer, nullable=False)
    cumulative_time = Column(sqltypes.Float, nullable=False)


class SubwayRealtime(BaseModel):
    __tablename__ = "subway_realtime"
    __table_args__ = (
        PrimaryKeyConstraint("station_id", "up_down_type", "arrival_sequence"),
    )
    station_id = Column(sqltypes.String, nullable=False)
    up_down_type = Column(sqltypes.String, nullable=False)
    arrival_sequence = Column(sqltypes.Integer, nullable=False)
    remaining_stop_count = Column(sqltypes.Integer, nullable=False)
    remaining_time = Column(sqltypes.Float, nullable=False)
    terminal_station_id = Column(sqltypes.String, nullable=False)
    current_station_name = Column(sqltypes.String, nullable=False)
    train_number = Column(sqltypes.String, nullable=False)
    last_updated_time = Column(sqltypes.DateTime, nullable=False)
    is_express_train = Column(sqltypes.Boolean, nullable=False)
    is_last_train = Column(sqltypes.Boolean, nullable=False)
    status_code = Column(sqltypes.Integer, nullable=False)
