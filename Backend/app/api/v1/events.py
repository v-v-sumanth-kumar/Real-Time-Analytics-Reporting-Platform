from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from app.core.deps import (
    get_current_member,
    get_ingestion_service,
    get_org_from_api_key,
    require_role,
)
from app.core.permissions import Role
from app.models.api_key import ApiKey
from app.models.organization import OrganizationMember
from app.schemas.event import EventBatchCreate, EventCreate, EventIngestResponse
from app.services.ingestion_service import IngestionService
from app.utils.response import success_response

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(
    body: EventCreate,
    request: Request,
    api_key: ApiKey = Depends(get_org_from_api_key),
    service: IngestionService = Depends(get_ingestion_service),
):
    ingest_id = await service.enqueue_event(api_key.organization_id, body)
    return success_response(
        EventIngestResponse(accepted=1, ingest_id=ingest_id).model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def ingest_batch(
    body: EventBatchCreate,
    request: Request,
    api_key: ApiKey = Depends(get_org_from_api_key),
    service: IngestionService = Depends(get_ingestion_service),
):
    ingest_id = await service.enqueue_batch(api_key.organization_id, body.events)
    return success_response(
        EventIngestResponse(accepted=len(body.events), ingest_id=ingest_id).model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    member: OrganizationMember = Depends(require_role(Role.ANALYST)),
    service: IngestionService = Depends(get_ingestion_service),
):
    content = await file.read()
    ingest_id = await service.enqueue_csv(member.organization_id, content)
    return success_response(
        EventIngestResponse(accepted=0, ingest_id=ingest_id).model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
