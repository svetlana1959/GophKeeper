"""Temporary mock endpoints for the Dashboard statistics UI."""

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Query

from gophkeeper.api.schemas.stats import (
    ActivityPointResponse,
    StatsActivityResponse,
    StatsOverviewResponse,
    StatsPeriod,
    StatsSecurityResponse,
)

router = APIRouter(prefix="/stats", tags=["stats"])


# TODO: Category statistics must eventually come from the client or separately
# synchronized encrypted metadata. The zero-knowledge backend cannot inspect
# ciphertext to determine whether a secret is a password, bank card, note, or file.
_MOCK_OVERVIEW = StatsOverviewResponse(
    passwords=71,
    bank_cards=4,
    notes=35,
    files=13,
    trusted_devices=4,
    revoked_devices=0,
)

_MOCK_LAST_DATE = date(2026, 7, 13)


def _mock_activity_points(days: int) -> list[ActivityPointResponse]:
    """Build a deterministic fixture ending on the mock Dashboard date."""
    start = _MOCK_LAST_DATE - timedelta(days=days - 1)
    return [
        ActivityPointResponse(
            date=start + timedelta(days=index),
            created=(index * 4 + 3) % 6,
            updated=(index * 2 + 2) % 7,
            deleted=index % 3,
        )
        for index in range(days)
    ]


_MOCK_ACTIVITY = {
    StatsPeriod.SEVEN_DAYS: _mock_activity_points(7),
    StatsPeriod.THIRTY_DAYS: _mock_activity_points(30),
    StatsPeriod.NINETY_DAYS: _mock_activity_points(90),
}

_MOCK_SECURITY = StatsSecurityResponse(
    status="good",
    trusted_devices=4,
    revoked_devices=0,
    alerts=0,
    last_sync_at=datetime(2026, 7, 13, 21, 30, tzinfo=UTC),
)


@router.get(
    "/overview",
    response_model=StatsOverviewResponse,
    summary="Get Dashboard overview statistics",
    description=(
        "Return temporary static counts for the Dashboard overview. "
        "No secret ciphertext is inspected."
    ),
)
async def overview() -> StatsOverviewResponse:
    return _MOCK_OVERVIEW


@router.get(
    "/activity",
    response_model=StatsActivityResponse,
    summary="Get Dashboard activity series",
    description="Return a temporary static daily series for the selected Dashboard period.",
)
async def activity(
    period: StatsPeriod = Query(
        default=StatsPeriod.SEVEN_DAYS,
        description="Activity window: 7d, 30d, or 90d.",
    ),
) -> StatsActivityResponse:
    return StatsActivityResponse(period=period, points=_MOCK_ACTIVITY[period])


@router.get(
    "/security",
    response_model=StatsSecurityResponse,
    summary="Get Dashboard security summary",
    description="Return temporary static device, alert, and synchronization statistics.",
)
async def security() -> StatsSecurityResponse:
    return _MOCK_SECURITY
