from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, Integer, String

from app.database.connection import Base


def _utcnow_naive() -> datetime:
    """Current UTC time as a naive datetime (SQLite stores it as text)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)

    device_id = Column(String(64), nullable=False, index=True)

    # From ESP32 (nullable: ESP may have no clock)
    timestamp = Column(DateTime, nullable=True)

    # Always set by backend on reception
    received_at = Column(
        DateTime,
        nullable=False,
        default=_utcnow_naive,
        index=True,
    )

    soil_moisture = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    air_humidity = Column(Float, nullable=False)

    prediction = Column(String(32), nullable=False)   # "irrigate" | "no_irrigate"
    pump_status = Column(String(8), nullable=False)   # "on" | "off"

    __table_args__ = (
        Index("ix_telemetry_device_received", "device_id", "received_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Telemetry id={self.id} device={self.device_id} "
            f"soil={self.soil_moisture} pump={self.pump_status}>"
        )