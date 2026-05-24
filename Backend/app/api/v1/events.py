from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from app.core.deps import (
    get_current_member,
    get_ingestion_service,
    get_org_from_api_key,
    require_role,
)
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from app.core.permissions import Role
from app.models.api_key import ApiKey
from app.models.organization import OrganizationMember
from app.schemas.event import EventBatchCreate, EventCreate, EventIngestResponse, EventResponse
from app.services.ingestion_service import IngestionService
from app.repositories.event_repository import EventRepository
from app.utils.pagination import PaginationParams
from app.utils.response import PaginationMeta, success_response

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stream")
async def list_recent_events(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    params: PaginationParams = Depends(),
    member: OrganizationMember = Depends(require_role(Role.VIEWER)),
):
    repo = EventRepository(session)
    result = await repo.list_by_org(member.organization_id, params)
    meta = PaginationMeta(
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )
    items = [
        EventResponse(
            id=e.id,
            event_name=e.event_name,
            occurred_at=e.occurred_at,
            received_at=e.received_at,
            properties=e.properties,
            user_id=e.user_id,
            session_id=e.session_id,
            source=e.source,
        ).model_dump()
        for e in result.items
    ]
    return success_response(items, meta=meta, correlation_id=getattr(request.state, "correlation_id", None))


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
