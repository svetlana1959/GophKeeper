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
    passwords: int = Field(description="Client-provided password count; zero until available.")
    bank_cards: int = Field(description="Client-provided card count; zero until available.")
    notes: int = Field(description="Client-provided note count; zero until available.")
    files: int = Field(description="Client-provided file count; zero until available.")
    trusted_devices: int = Field(description="Number of active trusted devices.")
    revoked_devices: int = Field(description="Number of revoked devices.")
    pending_devices: int = Field(description="Number of devices awaiting approval.")


class ActivityPointResponse(BaseModel):
    date: Date = Field(description="UTC calendar date represented by this point.")
    created: int = Field(description="Latest secret states first persisted on this UTC date.")
    updated: int = Field(description="Latest non-deleted mutations on this UTC date.")
    deleted: int = Field(description="Latest tombstones persisted on this UTC date.")


class StatsActivityResponse(BaseModel):
    period: StatsPeriod = Field(description="Time window represented by the activity points.")
    points: list[ActivityPointResponse] = Field(
        description="Daily latest-mutation points in chronological order."
    )


class StatsSecurityResponse(BaseModel):
    status: Literal["good", "warning"] = Field(
        description="Warning when revoked or pending devices exist; good otherwise."
    )
    trusted_devices: int = Field(description="Number of active trusted devices.")
    revoked_devices: int = Field(description="Number of revoked devices.")
    pending_devices: int = Field(description="Number of devices awaiting approval.")
    alerts: int = Field(description="Known device lifecycle risks (revoked plus pending).")
    last_sync_at: datetime | None = Field(
        description="Latest successful account sync, or null until such events are persisted."
    )
