"""Dashboard statistics response DTOs."""

from datetime import date as Date
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class StatsPeriod(StrEnum):
    """Supported time windows for dashboard activity."""

    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"


class StatsOverviewResponse(BaseModel):
    passwords: int = Field(description="Mock count of password entries.")
    bank_cards: int = Field(description="Mock count of bank card entries.")
    notes: int = Field(description="Mock count of secure notes.")
    files: int = Field(description="Mock count of encrypted files.")
    trusted_devices: int = Field(description="Number of trusted devices.")
    revoked_devices: int = Field(description="Number of revoked devices.")


class ActivityPointResponse(BaseModel):
    date: Date = Field(description="UTC calendar date represented by this point.")
    created: int = Field(description="Mock number of entries created on this date.")
    updated: int = Field(description="Mock number of entries updated on this date.")
    deleted: int = Field(description="Mock number of entries deleted on this date.")


class StatsActivityResponse(BaseModel):
    period: StatsPeriod = Field(description="Time window represented by the activity points.")
    points: list[ActivityPointResponse] = Field(
        description="Daily activity points in chronological order."
    )


class StatsSecurityResponse(BaseModel):
    status: Literal["good"] = Field(description="Mock aggregate security status.")
    trusted_devices: int = Field(description="Number of trusted devices.")
    revoked_devices: int = Field(description="Number of revoked devices.")
    alerts: int = Field(description="Number of active security alerts.")
    last_sync_at: datetime = Field(description="UTC timestamp of the latest mock synchronization.")
