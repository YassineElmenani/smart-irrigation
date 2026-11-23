from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.telemetry import Telemetry
from app.schemas.telemetry import TelemetryCreate


# ---------- helpers ----------

def _utcnow_naive() -> datetime:
    """Now in UTC, without tzinfo (matches how we store it in SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Any datetime → naive UTC. Pass-through if None or already naive.
    Keeps the DB consistent no matter what the ESP32 sends.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# ---------- write ----------

def create_telemetry(db: Session, payload: TelemetryCreate) -> Telemetry:
    """
    Persist one measurement.
    - timestamp: from ESP32 if provided, else None
    - received_at: ALWAYS now()  (server-side source of truth)
    """
    record = Telemetry(
        device_id=payload.device_id,
        timestamp=_normalize(payload.timestamp),
        received_at=_utcnow_naive(),
        soil_moisture=payload.soil_moisture,
        temperature=payload.temperature,
        air_humidity=payload.air_humidity,
        prediction=payload.prediction,
        pump_status=payload.pump_status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ---------- read ----------

def list_telemetry(
    db: Session,
    *,
    device_id: Optional[str] = None,
    since: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Telemetry]:
    """History, newest first, optionally filtered by device and/or time."""
    stmt = select(Telemetry).order_by(Telemetry.received_at.desc())

    if device_id:
        stmt = stmt.where(Telemetry.device_id == device_id)

    since_norm = _normalize(since)
    if since_norm:
        stmt = stmt.where(Telemetry.received_at >= since_norm)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_latest(db: Session, *, device_id: Optional[str] = None) -> Optional[Telemetry]:
    """Most recent record, or None."""
    stmt = select(Telemetry).order_by(Telemetry.received_at.desc()).limit(1)
    if device_id:
        stmt = stmt.where(Telemetry.device_id == device_id)
    return db.scalars(stmt).first()


def get_stats(
    db: Session,
    *,
    device_id: Optional[str] = None,
    hours: int = 24,
) -> dict:
    """Aggregated numbers over the last N hours (for the dashboard)."""
    since = _utcnow_naive() - timedelta(hours=hours)

    base = select(
        func.count(Telemetry.id),
        func.min(Telemetry.soil_moisture),
        func.max(Telemetry.soil_moisture),
        func.avg(Telemetry.soil_moisture),
        func.avg(Telemetry.temperature),
        func.avg(Telemetry.air_humidity),
    ).where(Telemetry.received_at >= since)

    if device_id:
        base = base.where(Telemetry.device_id == device_id)

    count, smin, smax, savg, tavg, havg = db.execute(base).one()

    q_irrig = select(func.count(Telemetry.id)).where(
        Telemetry.received_at >= since,
        Telemetry.prediction == "irrigate",
    )
    q_pump = select(func.count(Telemetry.id)).where(
        Telemetry.received_at >= since,
        Telemetry.pump_status == "on",
    )
    if device_id:
        q_irrig = q_irrig.where(Telemetry.device_id == device_id)
        q_pump = q_pump.where(Telemetry.device_id == device_id)

    return {
        "window_hours": hours,
        "samples": count or 0,
        "soil_moisture_min": smin,
        "soil_moisture_max": smax,
        "soil_moisture_avg": savg,
        "temperature_avg": tavg,
        "air_humidity_avg": havg,
        "irrigation_decisions": db.execute(q_irrig).scalar() or 0,
        "pump_on_samples": db.execute(q_pump).scalar() or 0,
    }