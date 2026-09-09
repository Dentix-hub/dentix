"""
Pydantic schemas for Clinical Workspace Snapshot (Issue #205).

Defines read-only versioned workspace models exposed by the patient-scoped
clinical workspace snapshot endpoint. Exposes no financial data and no
mutation authority.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class ClinicalWorkspaceWarning(BaseModel):
    """Explicit warning, ambiguity, or unsupported clinical code diagnostic."""
    code: str
    message: str
    source_kind: Optional[str] = None
    source_id: Optional[Union[int, str]] = None
    raw_value: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class WorkspaceTarget(BaseModel):
    """Anatomical target for a clinical entry (tooth, surface, root, canal)."""
    kind: str  # tooth, surface, root, canal
    tooth_key: str  # FDI tooth key (e.g. '11', '46')
    surface_code: Optional[str] = None
    root_id: Optional[str] = None
    canal_id: Optional[str] = None


class WorkspaceVisualEntry(BaseModel):
    """Visual entry representing an active/completed finding or procedure."""
    visual_id: str
    entry_type: str  # 'finding' | 'procedure'
    code: str  # Canonical FindingCode or ProcedureCode
    phase: str  # 'existing' | 'planned' | 'active' | 'completed'
    targets: List[WorkspaceTarget] = Field(default_factory=list)
    occurred_at: Optional[datetime] = None
    recorded_at: Optional[datetime] = None
    provenance: str = "native"  # 'native' | 'legacy_fallback'
    temporal_certainty: str = "EXACT"  # 'EXACT' | 'ESTIMATED' | 'UNKNOWN'


class WorkspaceToothSummary(BaseModel):
    """Per-tooth clinical summary across FDI anatomical teeth."""
    tooth_key: str
    lifecycle: str = "PRESENT"  # PRESENT | MISSING | EXTRACTED | IMPACTED | UNERUPTED
    condition: Optional[str] = None  # Neutral when no clinical evidence recorded
    findings: List[WorkspaceVisualEntry] = Field(default_factory=list)
    procedures: List[WorkspaceVisualEntry] = Field(default_factory=list)
    provenance: str = "native"  # 'native' | 'legacy_fallback'
    temporal_certainty: str = "EXACT"  # 'EXACT' | 'UNKNOWN'
    notes: Optional[str] = None


class WorkspaceWorkItemSummary(BaseModel):
    """Work item summary exposing clinical status without financial attributes."""
    id: Union[int, str]
    kind: str  # 'procedure' | 'finding'
    code: str
    status: str  # 'proposed' | 'planned' | 'active' | 'completed' | 'cancelled'
    notes: Optional[str] = None
    targets: List[WorkspaceTarget] = Field(default_factory=list)
    provenance: str = "native"  # 'native' | 'legacy_fallback'
    occurred_at: Optional[datetime] = None
    recorded_at: Optional[datetime] = None
    temporal_certainty: str = "EXACT"  # 'EXACT' | 'UNKNOWN'
    is_renderer_supported: bool = True


class ClinicalWorkspaceSnapshot(BaseModel):
    """
    Versioned patient-scoped clinical workspace snapshot.
    Exposes no finance and no mutation authority.
    """
    projection_id: str
    schema_version: int = 1
    patient_id: int
    generated_at: datetime
    effective_at: datetime
    read_mode: Literal["LEGACY_ONLY", "SHADOW", "VNEXT_PRIMARY"] = "LEGACY_ONLY"
    coverage: Dict[str, str] = Field(default_factory=dict)  # domain -> UNCOVERED|PARTIAL|COMPLETE
    warnings: List[ClinicalWorkspaceWarning] = Field(default_factory=list)
    teeth: Dict[str, WorkspaceToothSummary] = Field(default_factory=dict)
    work_items: List[WorkspaceWorkItemSummary] = Field(default_factory=list)
