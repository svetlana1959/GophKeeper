"""Account-scoped Dashboard statistics endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from gophkeeper.api.deps import get_account_id, provide
from gophkeeper.api.schemas.stats import (
    ActivityPointResponse,
    StatsActivityResponse,
    StatsOverviewResponse,
    StatsPeriod,
    StatsSecurityResponse,
)
from gophkeeper.services.stats_service import StatsService, StatsWindow

router = APIRouter(prefix="/stats", tags=["stats"])
_stats_service = provide(StatsService)


@router.get("/overview", response_model=StatsOverviewResponse)
async def overview(
    account_id: UUID = Depends(get_account_id),
    service: StatsService = Depends(_stats_service),
) -> StatsOverviewResponse:
    devices = await service.device_stats(account_id)
    # TODO: synchronize privacy-preserving category counters from clients. The
    # zero-knowledge backend cannot infer secret types from opaque ciphertext.
    return StatsOverviewResponse(
        passwords=0,
        bank_cards=0,
        notes=0,
        files=0,
        trusted_devices=devices.trusted,
        revoked_devices=devices.revoked,
        pending_devices=devices.pending,
    )


@router.get("/activity", response_model=StatsActivityResponse)
async def activity(
    period: StatsPeriod = Query(default=StatsPeriod.SEVEN_DAYS),
    account_id: UUID = Depends(get_account_id),
    service: StatsService = Depends(_stats_service),
) -> StatsActivityResponse:
    points = await service.activity(account_id, StatsWindow(period.value))
    return StatsActivityResponse(
        period=period,
        points=[ActivityPointResponse(**vars(point)) for point in points],
    )


@router.get("/security", response_model=StatsSecurityResponse)
async def security(
    account_id: UUID = Depends(get_account_id),
    service: StatsService = Depends(_stats_service),
) -> StatsSecurityResponse:
    devices = await service.device_stats(account_id)
    return StatsSecurityResponse(
        status="warning" if devices.alerts else "good",
        trusted_devices=devices.trusted,
        revoked_devices=devices.revoked,
        pending_devices=devices.pending,
        alerts=devices.alerts,
        # TODO: persist successful account sync events. Device.last_seen_at is
        # authentication metadata and must not be presented as a sync timestamp.
        last_sync_at=None,
    )
