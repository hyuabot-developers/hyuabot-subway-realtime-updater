import datetime

from sqlalchemy import Date, DateTime, PrimaryKeyConstraint, String, Text, func
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
    station_seq: Mapped[int] = mapped_column(nullable=False)
    cumulative_time: Mapped[datetime.timedelta] = mapped_column(nullable=False)


class SubwayRealtime(BaseModel):
    __tablename__ = "subway_realtime"
    __table_args__ = (
        PrimaryKeyConstraint("station_id", "up_down_type", "arrival_seq"),
    )
    station_id: Mapped[str] = mapped_column(nullable=False)
    up_down_type: Mapped[str] = mapped_column(nullable=False)
    arrival_seq: Mapped[int] = mapped_column(nullable=False)
    remaining_stop_count: Mapped[int] = mapped_column(nullable=False)
    remaining_time: Mapped[datetime.timedelta] = mapped_column(nullable=False)
    terminal_station_id: Mapped[str] = mapped_column(nullable=False)
    current_station_name: Mapped[str] = mapped_column(nullable=False)
    train_number: Mapped[str] = mapped_column(nullable=False)
    last_updated_time: Mapped[datetime.datetime] = mapped_column(nullable=False)
    is_express_train: Mapped[bool] = mapped_column(nullable=False)
    is_last_train: Mapped[bool] = mapped_column(nullable=False)
    status_code: Mapped[int] = mapped_column(nullable=False)
    arrival_message: Mapped[str | None] = mapped_column(String(100), nullable=True)
    arrival_message_detail: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remaining_seconds: Mapped[int | None] = mapped_column(nullable=True)
    arrival_code: Mapped[int | None] = mapped_column(nullable=True)


class SubwayTrainDelay(BaseModel):
    __tablename__ = "subway_train_delay"
    __table_args__ = (
        PrimaryKeyConstraint("run_date", "train_number", name="pk_subway_train_delay"),
    )
    run_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    train_number: Mapped[str] = mapped_column(String(10), nullable=False)
    route_id: Mapped[int | None] = mapped_column(nullable=True)
    delay_minutes: Mapped[int | None] = mapped_column(nullable=True)
    reference_station_name: Mapped[str | None] = mapped_column(String(30), nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SubwayAlert(BaseModel):
    __tablename__ = "subway_alert"
    alert_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    route_id: Mapped[int | None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="SEOUL_METRO")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
