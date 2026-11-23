from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services import telemetry_service

router = APIRouter(prefix="/pump", tags=["Pump"])


@router.get("/status", summary="Current pump state (from last measurement)")
def pump_status(
    device_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    latest = telemetry_service.get_latest(db, device_id=device_id)
    if latest is None:
        return {
            "device_id": device_id,
            "pump_status": "unknown",
            "prediction": None,
            "received_at": None,
        }
    return {
        "device_id": latest.device_id,
        "pump_status": latest.pump_status,
        "prediction": latest.prediction,
        "received_at": latest.received_at,
    }