"""
Clinical Rollout Service (G16-M01, G16-M02, G16-M08, G16-M10).

Provides atomic tenant-level rollout controls, read-only VNext mode enforcement,
and instant rollback to LEGACY_ONLY.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Literal, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.services.feature_service import FeatureFlagService
from backend.services.clinical_workspace_service import (
    FEATURE_FLAG_CLINICAL_SHADOW,
    FEATURE_FLAG_CLINICAL_PRIMARY,
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
)
from backend.services.clinical_charge_service import (
    FEATURE_FLAG_CLINICAL_FINANCE_READ,
)
from backend.utils.audit_logger import log_admin_action

logger = logging.getLogger(__name__)

ALL_CLINICAL_ROLLOUT_FLAGS = (
    FEATURE_FLAG_CLINICAL_SHADOW,
    FEATURE_FLAG_CLINICAL_PRIMARY,
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
    FEATURE_FLAG_CLINICAL_FINANCE_READ,
)

FLAG_DESCRIPTIONS = {
    FEATURE_FLAG_CLINICAL_SHADOW: "Enables shadow clinical workspace read mode",
    FEATURE_FLAG_CLINICAL_PRIMARY: "Enables primary clinical workspace read mode",
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES: "Enables direct standalone writes to native clinical tables",
    FEATURE_FLAG_CLINICAL_FINANCE_READ: "Enables VNext clinical charges read and reception actions",
}


class ClinicalRolloutService:
    """Manages tenant clinical rollout modes, flag toggles, and atomic rollback."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _ensure_flag_registered(self, key: str) -> None:
        """Ensure the global FeatureFlag record exists before setting a tenant override."""
        stmt = select(models.FeatureFlag).where(models.FeatureFlag.key == key)
        flag = (await self.db.execute(stmt)).scalar_one_or_none()
        if not flag:
            flag = models.FeatureFlag(
                key=key,
                description=FLAG_DESCRIPTIONS.get(key, f"Clinical flag {key}"),
                is_global_enabled=False,
                rollout_percentage=0,
            )
            self.db.add(flag)
            await self.db.flush()

    async def _get_tenant_or_404(self, tenant_id: int) -> models.Tenant:
        """Fetch tenant or raise 404."""
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
        tenant = (await self.db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
        return tenant

    async def _read_flags_state(self, tenant_id: int) -> Dict[str, bool]:
        """Read all relevant rollout flags for a tenant."""
        states = {}
        for key in ALL_CLINICAL_ROLLOUT_FLAGS:
            states[key] = await FeatureFlagService.is_feature_enabled(self.db, key, tenant_id)
        return states

    def _resolve_mode_from_flags(self, flags: Dict[str, bool]) -> Literal["LEGACY_ONLY", "SHADOW", "VNEXT_PRIMARY"]:
        """Determine clinical workspace read mode from flag states."""
        if flags.get(FEATURE_FLAG_CLINICAL_SHADOW):
            return "SHADOW"
        if flags.get(FEATURE_FLAG_CLINICAL_PRIMARY):
            return "VNEXT_PRIMARY"
        return "LEGACY_ONLY"

    async def get_rollout_status(self, tenant_id: int) -> schemas.TenantClinicalRolloutStatus:
        """
        Get current rollout status for a tenant (G16-M01, G16-M02).
        Strictly read-only; zero database writes.
        """
        tenant = await self._get_tenant_or_404(tenant_id)
        flags = await self._read_flags_state(tenant_id)
        mode = self._resolve_mode_from_flags(flags)

        return schemas.TenantClinicalRolloutStatus(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            rollout_mode=mode,
            native_writes_enabled=flags.get(FEATURE_FLAG_CLINICAL_NATIVE_WRITES, False),
            finance_read_enabled=flags.get(FEATURE_FLAG_CLINICAL_FINANCE_READ, False),
            feature_flags=flags,
            updated_at=datetime.now(timezone.utc),
        )

    async def _apply_flag_overrides(
        self,
        tenant_id: int,
        target_flags: Dict[str, bool],
    ) -> None:
        """Apply a batch of tenant flag overrides in a single atomic transaction."""
        for key, enabled in target_flags.items():
            await self._ensure_flag_registered(key)
            stmt = select(models.TenantFeature).where(
                models.TenantFeature.tenant_id == tenant_id,
                models.TenantFeature.feature_key == key,
            )
            override = (await self.db.execute(stmt)).scalar_one_or_none()
            if override:
                override.is_enabled = enabled
            else:
                override = models.TenantFeature(
                    tenant_id=tenant_id,
                    feature_key=key,
                    is_enabled=enabled,
                )
                self.db.add(override)
        await self.db.flush()

    async def rollback_tenant(
        self,
        tenant_id: int,
        admin_user: Optional[models.User] = None,
    ) -> schemas.TenantClinicalRolloutResponse:
        """
        Atomically rollback a tenant to LEGACY_ONLY mode (G16-M08).
        Disables clinical_vnext_native_writes, clinical_vnext_primary,
        clinical_vnext_shadow, and clinical_vnext_finance_read in a single transaction.
        """
        await self._get_tenant_or_404(tenant_id)
        before_flags = await self._read_flags_state(tenant_id)
        previous_mode = self._resolve_mode_from_flags(before_flags)

        rollback_flags = {
            FEATURE_FLAG_CLINICAL_SHADOW: False,
            FEATURE_FLAG_CLINICAL_PRIMARY: False,
            FEATURE_FLAG_CLINICAL_NATIVE_WRITES: False,
            FEATURE_FLAG_CLINICAL_FINANCE_READ: False,
        }

        await self._apply_flag_overrides(tenant_id, rollback_flags)

        if admin_user:
            log_admin_action(
                db=self.db,
                admin_user=admin_user,
                action="clinical_rollout_rollback",
                entity_type="tenant",
                entity_id=tenant_id,
                tenant_id=tenant_id,
                details=f"Rolled back tenant {tenant_id} from {previous_mode} to LEGACY_ONLY",
            )

        await self.db.commit()

        after_flags = await self._read_flags_state(tenant_id)
        logger.info(
            "Rolled back tenant %s from %s to LEGACY_ONLY (flags: %s)",
            tenant_id,
            previous_mode,
            after_flags,
        )

        return schemas.TenantClinicalRolloutResponse(
            success=True,
            tenant_id=tenant_id,
            message="Tenant successfully rolled back to LEGACY_ONLY mode.",
            previous_mode=previous_mode,
            current_mode="LEGACY_ONLY",
            native_writes_enabled=False,
            flags=after_flags,
            updated_at=datetime.now(timezone.utc),
        )

    async def set_tenant_rollout_mode(
        self,
        tenant_id: int,
        target_mode: schemas.ClinicalRolloutTargetMode,
        admin_user: Optional[models.User] = None,
    ) -> schemas.TenantClinicalRolloutResponse:
        """
        Set a tenant's rollout mode atomically (G16-M01, G16-M02, G16-M08).
        Available modes:
        - LEGACY_ONLY: shadow=False, primary=False, native_writes=False
        - SHADOW: shadow=True, primary=False, native_writes=False
        - VNEXT_PRIMARY_READ_ONLY: shadow=False, primary=True, native_writes=False
        - VNEXT_PRIMARY_READ_WRITE: shadow=False, primary=True, native_writes=True
        """
        await self._get_tenant_or_404(tenant_id)
        before_flags = await self._read_flags_state(tenant_id)
        previous_mode = self._resolve_mode_from_flags(before_flags)

        if target_mode == "LEGACY_ONLY":
            target_flags = {
                FEATURE_FLAG_CLINICAL_SHADOW: False,
                FEATURE_FLAG_CLINICAL_PRIMARY: False,
                FEATURE_FLAG_CLINICAL_NATIVE_WRITES: False,
            }
            resolved_current = "LEGACY_ONLY"
            native_writes = False
        elif target_mode == "SHADOW":
            target_flags = {
                FEATURE_FLAG_CLINICAL_SHADOW: True,
                FEATURE_FLAG_CLINICAL_PRIMARY: False,
                FEATURE_FLAG_CLINICAL_NATIVE_WRITES: False,
            }
            resolved_current = "SHADOW"
            native_writes = False
        elif target_mode == "VNEXT_PRIMARY_READ_ONLY":
            target_flags = {
                FEATURE_FLAG_CLINICAL_SHADOW: False,
                FEATURE_FLAG_CLINICAL_PRIMARY: True,
                FEATURE_FLAG_CLINICAL_NATIVE_WRITES: False,
            }
            resolved_current = "VNEXT_PRIMARY"
            native_writes = False
        elif target_mode == "VNEXT_PRIMARY_READ_WRITE":
            target_flags = {
                FEATURE_FLAG_CLINICAL_SHADOW: False,
                FEATURE_FLAG_CLINICAL_PRIMARY: True,
                FEATURE_FLAG_CLINICAL_NATIVE_WRITES: True,
            }
            resolved_current = "VNEXT_PRIMARY"
            native_writes = True
        else:
            raise HTTPException(status_code=400, detail=f"Invalid target mode: {target_mode}")

        await self._apply_flag_overrides(tenant_id, target_flags)

        if admin_user:
            log_admin_action(
                db=self.db,
                admin_user=admin_user,
                action="clinical_rollout_set_mode",
                entity_type="tenant",
                entity_id=tenant_id,
                tenant_id=tenant_id,
                details=f"Changed rollout mode for tenant {tenant_id} from {previous_mode} to {target_mode}",
            )

        await self.db.commit()

        after_flags = await self._read_flags_state(tenant_id)
        logger.info(
            "Changed rollout mode for tenant %s from %s to %s (flags: %s)",
            tenant_id,
            previous_mode,
            target_mode,
            after_flags,
        )

        return schemas.TenantClinicalRolloutResponse(
            success=True,
            tenant_id=tenant_id,
            message=f"Tenant rollout mode successfully set to {target_mode}.",
            previous_mode=previous_mode,
            current_mode=resolved_current,
            native_writes_enabled=native_writes,
            flags=after_flags,
            updated_at=datetime.now(timezone.utc),
        )
