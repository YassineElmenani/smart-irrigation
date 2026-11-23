from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.telemetry import TelemetryCreate, TelemetryOut, TelemetryStats
from app.services import telemetry_service

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.post(
    "",
    response_model=TelemetryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Receive one measurement from the ESP32",
)
def create_telemetry(payload: TelemetryCreate, db: Session = Depends(get_db)):
    return telemetry_service.create_telemetry(db, payload)


@router.get("", response_model=list[TelemetryOut], summary="List history")
def list_telemetry(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    device_id: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    return telemetry_service.list_telemetry(
        db,
        device_id=device_id,
        since=since,
        skip=skip,
        limit=limit,
    )


@router.get("/latest", response_model=TelemetryOut, summary="Get newest measurement")
def get_latest(
    device_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    record = telemetry_service.get_latest(db, device_id=device_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No measurement available")
    return record


@router.get("/stats", response_model=TelemetryStats, summary="Aggregated stats")
def get_stats(
    device_id: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    return telemetry_service.get_stats(db, device_id=device_id, hours=hours)