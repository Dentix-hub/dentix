"""
Workflow Template Service (Care Sessions VNext).
Manages clinic-owned clinical workflow templates, versioning, custom fields,
and retrieval of template blueprints for care sessions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.clinical.workflow_templates import (
    CANONICAL_WORKFLOW_TEMPLATES,
    WorkflowTemplateDefinition,
    get_workflow_registry,
)
from backend.schemas.workflow_template import (
    WorkflowTemplateCreate,
    WorkflowTemplateRead,
    WorkflowTemplateUpdate,
)
from backend.services.feature_service import FeatureFlagService
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES


class WorkflowTemplateService:
    def __init__(self, db: AsyncSession, tenant_id: int, current_user: Optional[models.User] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.current_user = current_user

    async def is_native_writes_enabled(self) -> bool:
        return await FeatureFlagService.is_feature_enabled(
            self.db, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, self.tenant_id
        )

    async def ensure_native_writes_enabled(self) -> None:
        """Fail-closed gate when clinical_vnext_native_writes is OFF (404)."""
        if not await self.is_native_writes_enabled():
            raise HTTPException(
                status_code=404,
                detail="Clinical native writes are disabled",
            )

    async def list_templates(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        List active and latest templates for the clinic.
        Includes customized tenant templates, plus canonical blueprints for procedures
        that have not yet been customized by this clinic.
        """
        # Fetch all tenant templates
        stmt = (
            select(models.WorkflowTemplate)
            .where(models.WorkflowTemplate.tenant_id == self.tenant_id)
            .order_by(models.WorkflowTemplate.template_code, models.WorkflowTemplate.version.desc())
        )
        result = await self.db.execute(stmt)
        tenant_templates = list(result.scalars().all())

        # Group by template_code to find latest version
        tenant_latest: Dict[str, models.WorkflowTemplate] = {}
        for t in tenant_templates:
            if t.template_code not in tenant_latest:
                tenant_latest[t.template_code] = t

        items: List[Dict[str, Any]] = []

        # Add tenant-owned templates
        for code, t in tenant_latest.items():
            if not include_inactive and not t.is_active:
                continue
            items.append({
                "id": t.id,
                "tenant_id": t.tenant_id,
                "template_code": t.template_code,
                "version": t.version,
                "title": t.title,
                "procedure_code": t.definition.get("procedure_code", t.template_code),
                "description": t.description,
                "is_active": t.is_active,
                "definition": t.definition,
                "is_customized": True,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            })

        # Add canonical templates if not customized by this tenant
        for canonical in CANONICAL_WORKFLOW_TEMPLATES:
            if canonical.template_code not in tenant_latest:
                if not include_inactive and not canonical.is_active:
                    continue
                canonical_dict = canonical.to_dict()
                items.append({
                    "id": None,
                    "tenant_id": self.tenant_id,
                    "template_code": canonical.template_code,
                    "version": canonical.version,
                    "title": canonical.title,
                    "procedure_code": canonical.procedure_code,
                    "description": canonical.description,
                    "is_active": canonical.is_active,
                    "definition": {
                        "steps": canonical_dict.get("steps", []),
                        "custom_fields": canonical_dict.get("custom_fields", []),
                    },
                    "is_customized": False,
                    "created_at": None,
                    "updated_at": None,
                })

        return sorted(items, key=lambda x: x["template_code"])

    async def get_template(self, code_or_id: str | int, version: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve a template by integer ID or string code.
        Falls back to canonical blueprint if not customized.
        """
        if isinstance(code_or_id, int) or (isinstance(code_or_id, str) and code_or_id.isdigit()):
            template_id = int(code_or_id)
            stmt = select(models.WorkflowTemplate).where(
                models.WorkflowTemplate.id == template_id,
                models.WorkflowTemplate.tenant_id == self.tenant_id,
            )
            t = (await self.db.execute(stmt)).scalar_one_or_none()
            if t:
                return {
                    "id": t.id,
                    "tenant_id": t.tenant_id,
                    "template_code": t.template_code,
                    "version": t.version,
                    "title": t.title,
                    "procedure_code": t.definition.get("procedure_code", t.template_code),
                    "description": t.description,
                    "is_active": t.is_active,
                    "definition": t.definition,
                    "is_customized": True,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at,
                }

        # Lookup by template_code
        code = str(code_or_id).strip().upper()
        stmt = (
            select(models.WorkflowTemplate)
            .where(
                models.WorkflowTemplate.tenant_id == self.tenant_id,
                models.WorkflowTemplate.template_code == code,
            )
        )
        if version is not None:
            stmt = stmt.where(models.WorkflowTemplate.version == version)
        else:
            stmt = stmt.order_by(models.WorkflowTemplate.version.desc())

        t = (await self.db.execute(stmt)).scalars().first()
        if t:
            return {
                "id": t.id,
                "tenant_id": t.tenant_id,
                "template_code": t.template_code,
                "version": t.version,
                "title": t.title,
                "procedure_code": t.definition.get("procedure_code", t.template_code),
                "description": t.description,
                "is_active": t.is_active,
                "definition": t.definition,
                "is_customized": True,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            }

        # Fallback to canonical registry
        registry = get_workflow_registry()
        try:
            if version is not None:
                canonical = registry.get_template(code, version)
            else:
                canonical = registry.get_latest_template(code)
            canonical_dict = canonical.to_dict()
            return {
                "id": None,
                "tenant_id": self.tenant_id,
                "template_code": canonical.template_code,
                "version": canonical.version,
                "title": canonical.title,
                "procedure_code": canonical.procedure_code,
                "description": canonical.description,
                "is_active": canonical.is_active,
                "definition": {
                    "steps": canonical_dict.get("steps", []),
                    "custom_fields": canonical_dict.get("custom_fields", []),
                },
                "is_customized": False,
                "created_at": None,
                "updated_at": None,
            }
        except Exception:
            raise HTTPException(status_code=404, detail=f"Workflow template '{code_or_id}' not found")

    async def create_template(self, payload: WorkflowTemplateCreate) -> models.WorkflowTemplate:
        """
        Create a new clinic-owned workflow template or new version.
        Guarantees version > 0 and uniqueness of (tenant_id, template_code, version).
        """
        code = payload.template_code.strip().upper()

        # Find current max version for this template_code in the tenant
        stmt = select(func.coalesce(func.max(models.WorkflowTemplate.version), 0)).where(
            models.WorkflowTemplate.tenant_id == self.tenant_id,
            models.WorkflowTemplate.template_code == code,
        )
        max_ver = (await self.db.execute(stmt)).scalar_one()
        next_ver = max_ver + 1

        definition_dict = payload.definition.model_dump()
        definition_dict["procedure_code"] = payload.procedure_code or code

        template = models.WorkflowTemplate(
            tenant_id=self.tenant_id,
            template_code=code,
            version=next_ver,
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            is_active=payload.is_active,
            definition=definition_dict,
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def update_template(self, code_or_id: str | int, payload: WorkflowTemplateUpdate) -> models.WorkflowTemplate:
        """
        Update a clinic template by creating a NEW version.
        Preserves historical immutability so past visits retain their original snapshot.
        """
        current = await self.get_template(code_or_id)
        code = current["template_code"]

        # Determine next version
        stmt = select(func.coalesce(func.max(models.WorkflowTemplate.version), 0)).where(
            models.WorkflowTemplate.tenant_id == self.tenant_id,
            models.WorkflowTemplate.template_code == code,
        )
        max_ver = (await self.db.execute(stmt)).scalar_one()
        next_ver = max(max_ver, current["version"]) + 1

        # Merge definition
        if payload.definition:
            definition_dict = payload.definition.model_dump()
        else:
            definition_dict = dict(current.get("definition") or {})

        proc_code = payload.procedure_code or current.get("procedure_code") or code
        definition_dict["procedure_code"] = proc_code

        new_template = models.WorkflowTemplate(
            tenant_id=self.tenant_id,
            template_code=code,
            version=next_ver,
            title=payload.title.strip() if payload.title else current["title"],
            description=payload.description.strip() if payload.description is not None else current.get("description"),
            is_active=payload.is_active if payload.is_active is not None else current.get("is_active", True),
            definition=definition_dict,
        )
        self.db.add(new_template)
        await self.db.flush()
        return new_template

    async def set_active_status(self, template_id: int, is_active: bool) -> models.WorkflowTemplate:
        """Activate or deactivate a template version."""
        stmt = select(models.WorkflowTemplate).where(
            models.WorkflowTemplate.id == template_id,
            models.WorkflowTemplate.tenant_id == self.tenant_id,
        )
        template = (await self.db.execute(stmt)).scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="Workflow template not found")
        template.is_active = is_active
        await self.db.flush()
        return template

    async def get_active_template_for_procedure(self, procedure_code: str) -> Optional[Dict[str, Any]]:
        """
        Helper used by CareSessionService to resolve the active template snapshot
        when associating a procedure with a care session.
        """
        if not procedure_code:
            return None
        code = procedure_code.strip().upper()

        stmt = (
            select(models.WorkflowTemplate)
            .where(models.WorkflowTemplate.tenant_id == self.tenant_id)
            .order_by(models.WorkflowTemplate.version.desc())
        )
        result = await self.db.execute(stmt)
        tenant_templates = list(result.scalars().all())

        tenant_latest: Dict[str, models.WorkflowTemplate] = {}
        for t in tenant_templates:
            if t.template_code not in tenant_latest:
                tenant_latest[t.template_code] = t

        matching = []
        for t in tenant_latest.values():
            proc_c = (t.definition.get("procedure_code") or t.template_code or "").strip().upper()
            if proc_c == code or t.template_code == code:
                priority = 1 if (t.definition.get("procedure_code") or "").strip().upper() == code else 2
                matching.append((priority, t))

        if matching:
            matching.sort(key=lambda x: (x[0], -(x[1].id or 0)))
            t = matching[0][1]
            if not t.is_active:
                return None
            return {
                "template_code": t.template_code,
                "version": t.version,
                "title": t.title,
                "procedure_code": t.definition.get("procedure_code", t.template_code),
                "steps": t.definition.get("steps", []),
                "custom_fields": t.definition.get("custom_fields", []),
            }

        # Fallback to canonical
        registry = get_workflow_registry()
        try:
            canonical = registry.get_latest_template(code)
            if canonical.is_active:
                canonical_dict = canonical.to_dict()
                return {
                    "template_code": canonical.template_code,
                    "version": canonical.version,
                    "title": canonical.title,
                    "procedure_code": canonical.procedure_code,
                    "steps": canonical_dict.get("steps", []),
                    "custom_fields": canonical_dict.get("custom_fields", []),
                }
        except Exception:
            pass

        return None

    async def is_template_deactivated(self, procedure_or_template_code: str) -> bool:
        """
        Check if a template matching the procedure or template code is explicitly deactivated for this clinic.
        """
        if not procedure_or_template_code:
            return False
        code = procedure_or_template_code.strip().upper()

        stmt = (
            select(models.WorkflowTemplate)
            .where(models.WorkflowTemplate.tenant_id == self.tenant_id)
            .order_by(models.WorkflowTemplate.version.desc())
        )
        result = await self.db.execute(stmt)
        tenant_templates = list(result.scalars().all())

        tenant_latest: Dict[str, models.WorkflowTemplate] = {}
        for t in tenant_templates:
            if t.template_code not in tenant_latest:
                tenant_latest[t.template_code] = t

        matching = []
        for t in tenant_latest.values():
            proc_c = (t.definition.get("procedure_code") or t.template_code or "").strip().upper()
            if proc_c == code or t.template_code == code:
                priority = 1 if (t.definition.get("procedure_code") or "").strip().upper() == code else 2
                matching.append((priority, t))

        if matching:
            matching.sort(key=lambda x: (x[0], -(x[1].id or 0)))
            return not bool(matching[0][1].is_active)

        return False
