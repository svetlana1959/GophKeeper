"""Enrollment endpoints — invite a device, join with a code."""

from fastapi import APIRouter, Depends, status

from gophkeeper.api.deps import get_principal, provide
from gophkeeper.api.schemas.device import DeviceResponse
from gophkeeper.api.schemas.enroll import CreateInviteResponse, JoinRequest
from gophkeeper.security.principal import DevicePrincipal
from gophkeeper.services.enrollment_service import EnrollmentService

router = APIRouter(prefix="/enroll", tags=["enroll"])


@router.post("/invite", response_model=CreateInviteResponse)
async def create_invite(
    principal: DevicePrincipal = Depends(get_principal),
    service: EnrollmentService = Depends(provide(EnrollmentService)),
) -> CreateInviteResponse:
    invite, code = await service.create_invite(account_id=principal.account_id)
    return CreateInviteResponse(code=code, expires_at=invite.expires_at)


@router.post("/join", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def join(
    body: JoinRequest,
    service: EnrollmentService = Depends(provide(EnrollmentService)),
) -> DeviceResponse:
    device = await service.join(
        code=body.code,
        device_name=body.device_name,
        public_key=body.public_key,
    )
    return DeviceResponse.from_domain(device)
