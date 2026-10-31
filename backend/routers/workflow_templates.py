"""
Workflow Templates Router (Care Sessions VNext).
Endpoints for managing clinic-owned clinical workflow templates, custom fields,
and retrieving template definitions.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, success_response
from backend.database import get_async_db
from backend.schemas.workflow_template import (
    WorkflowTemplateCreate,
    WorkflowTemplateRead,
    WorkflowTemplateUpdate,
)
from backend.services.workflow_template_service import WorkflowTemplateService

router = APIRouter(prefix="/workflow-templates", tags=["Workflow Templates"])


class TemplateStatusPayload(BaseModel):
    is_active: bool = Field(..., description="Active status for template")


@router.get(
    "",
    response_model=StandardResponse[List[Dict[str, Any]]],
    summary="List clinic workflow templates",
    description="Retrieve all active and customized clinical workflow templates for the authenticated tenant.",
)
async def list_workflow_templates(
    include_inactive: bool = Query(False, description="Whether to include inactive templates"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = WorkflowTemplateService(db, current_user.tenant_id, current_user)
    await service.ensure_native_writes_enabled()
    templates = await service.list_templates(include_inactive=include_inactive)
    return success_response(
        data=templates,
        message="Workflow templates retrieved successfully",
    )


@router.post(
    "",
    response_model=StandardResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    summary="Create or customize workflow template",
    description="Create a new clinic-owned workflow template or new version with custom fields and ordered steps.",
)
async def create_workflow_template(
    payload: WorkflowTemplateCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = WorkflowTemplateService(db, current_user.tenant_id, current_user)
    await service.ensure_native_writes_enabled()
    tpl = await service.create_template(payload)
    await db.commit()
    await db.refresh(tpl)
    return success_response(
        data={
            "id": tpl.id,
            "tenant_id": tpl.tenant_id,
            "template_code": tpl.template_code,
            "version": tpl.version,
            "title": tpl.title,
            "description": tpl.description,
            "is_active": tpl.is_active,
            "definition": tpl.definition,
            "created_at": tpl.created_at,
            "updated_at": tpl.updated_at,
        },
        message=f"Workflow template '{tpl.template_code}' v{tpl.version} created successfully",
    )


@router.get(
    "/{code_or_id}",
    response_model=StandardResponse[Dict[str, Any]],
    summary="Get workflow template details",
    description="Retrieve full definition, steps, and custom fields for a specific template code or ID.",
)
async def get_workflow_template(
    code_or_id: str,
    version: Optional[int] = Query(None, description="Optional specific version lookup"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = WorkflowTemplateService(db, current_user.tenant_id, current_user)
    await service.ensure_native_writes_enabled()
    template = await service.get_template(code_or_id, version=version)
    return success_response(
        data=template,
        message="Workflow template retrieved successfully",
    )


@router.put(
    "/{code_or_id}",
    response_model=StandardResponse[Dict[str, Any]],
    summary="Update workflow template (creates new version)",
    description="Update a template by creating a new version to preserve historical visit interpretation.",
)
async def update_workflow_template(
    code_or_id: str,
    payload: WorkflowTemplateUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = WorkflowTemplateService(db, current_user.tenant_id, current_user)
    await service.ensure_native_writes_enabled()
    new_tpl = await service.update_template(code_or_id, payload)
    await db.commit()
    await db.refresh(new_tpl)
    return success_response(
        data={
            "id": new_tpl.id,
            "tenant_id": new_tpl.tenant_id,
            "template_code": new_tpl.template_code,
            "version": new_tpl.version,
            "title": new_tpl.title,
            "description": new_tpl.description,
            "is_active": new_tpl.is_active,
            "definition": new_tpl.definition,
            "created_at": new_tpl.created_at,
            "updated_at": new_tpl.updated_at,
        },
        message=f"Workflow template '{new_tpl.template_code}' updated to v{new_tpl.version} successfully",
    )


@router.patch(
    "/{template_id}/status",
    response_model=StandardResponse[Dict[str, Any]],
    summary="Toggle workflow template active status",
    description="Activate or deactivate a clinic workflow template version.",
)
async def set_workflow_template_status(
    template_id: int,
    payload: TemplateStatusPayload,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = WorkflowTemplateService(db, current_user.tenant_id, current_user)
    await service.ensure_native_writes_enabled()
    tpl = await service.set_active_status(template_id, payload.is_active)
    await db.commit()
    await db.refresh(tpl)
    return success_response(
        data={
            "id": tpl.id,
            "template_code": tpl.template_code,
            "version": tpl.version,
            "is_active": tpl.is_active,
        },
        message=f"Template status updated to {'active' if tpl.is_active else 'inactive'}",
    )
