import datetime

from sqlalchemy import PrimaryKeyConstraint, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    pass


class SubwayStation(BaseModel):
    __tablename__ = "subway_station"
    station_name: Mapped[str] = mapped_column(String(30), primary_key=True)


class SubwayRoute(BaseModel):
    __tablename__ = "subway_route"
    route_id: Mapped[int] = mapped_column(primary_key=True)
    route_name: Mapped[str] = mapped_column(String(30), nullable=False)


class SubwayRouteStation(BaseModel):
    __tablename__ = "subway_route_station"
    station_id: Mapped[str] = mapped_column(primary_key=True)
    station_name: Mapped[str] = mapped_column(nullable=False)
    route_id: Mapped[int] = mapped_column(nullable=False)
    station_sequence: Mapped[int] = mapped_column(nullable=False)
    cumulative_time: Mapped[datetime.timedelta] = mapped_column(nullable=False)


class SubwayRealtime(BaseModel):
    __tablename__ = "subway_realtime"
    __table_args__ = (
        PrimaryKeyConstraint("station_id", "up_down_type", "arrival_sequence"),
    )
    station_id: Mapped[str] = mapped_column(nullable=False)
    up_down_type: Mapped[str] = mapped_column(nullable=False)
    arrival_sequence: Mapped[int] = mapped_column(nullable=False)
    remaining_stop_count: Mapped[int] = mapped_column(nullable=False)
    remaining_time: Mapped[datetime.timedelta] = mapped_column(nullable=False)
    terminal_station_id: Mapped[str] = mapped_column(nullable=False)
    current_station_name: Mapped[str] = mapped_column(nullable=False)
    train_number: Mapped[str] = mapped_column(nullable=False)
    last_updated_time: Mapped[datetime.datetime] = mapped_column(nullable=False)
    is_express_train: Mapped[bool] = mapped_column(nullable=False)
    is_last_train: Mapped[bool] = mapped_column(nullable=False)
    status_code: Mapped[int] = mapped_column(nullable=False)
