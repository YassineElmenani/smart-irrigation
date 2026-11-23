from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# Restrict allowed values to exactly what the TinyML model + pump can output
Prediction = Literal["irrigate", "no_irrigate"]
PumpStatus = Literal["on", "off"]


class TelemetryBase(BaseModel):
    """Fields shared by IN and OUT schemas."""

    device_id: str = Field(..., min_length=1, max_length=64, examples=["esp32-gr2-01"])
    soil_moisture: float = Field(..., ge=0, le=100, description="Humidité du sol (%)")
    temperature: float = Field(..., ge=-40, le=80, description="Température de l'air (°C)")
    air_humidity: float = Field(..., ge=0, le=100, description="Humidité de l'air (%)")
    prediction: Prediction
    pump_status: PumpStatus


class TelemetryCreate(TelemetryBase):
    """Payload the ESP32 POSTs. Timestamp is optional (ESP may have no clock)."""

    timestamp: Optional[datetime] = Field(
        None,
        description="Heure de mesure côté ESP32 (UTC). Laisser vide si pas de NTP.",
    )


class TelemetryOut(TelemetryBase):
    """What the API returns to the dashboard."""

    id: int
    timestamp: Optional[datetime]
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TelemetryStats(BaseModel):
    """Aggregated numbers for /telemetry/stats."""

    window_hours: int
    samples: int
    soil_moisture_min: Optional[float] = None
    soil_moisture_max: Optional[float] = None
    soil_moisture_avg: Optional[float] = None
    temperature_avg: Optional[float] = None
    air_humidity_avg: Optional[float] = None
    irrigation_decisions: int
    pump_on_samples: int