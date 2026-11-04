"""
DENTIX Commercial Adapter.

Provides strict parsing, normalization, and validation of legacy plan features,
converting unstructured JSON, string arrays, and object dictionaries into a
well-typed capability map while preserving explicit False values and rejecting
unauthorized capability escalation.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.core.commercial_registry import (
    CAPABILITY_REGISTRY,
    CapabilityKey,
    canonicalize_capability_key,
    canonicalize_plan_name,
    is_sellable_capability,
    LAUNCH_PLAN_SPECS,
)

logger = logging.getLogger("smart_clinic.commercial")


@dataclass
class NormalizedFeatures:
    """Typed normalized capabilities for a tenant or plan."""
    capabilities: Dict[str, bool] = field(default_factory=dict)
    unmapped_keys: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    is_valid_config: bool = True


def parse_raw_features(raw: Any) -> Tuple[Dict[str, bool], List[str], List[str], bool]:
    """
    Parse and strictly validate raw features input from DB or API.

    Returns:
        (canonical_map, unmapped_keys, warnings, is_valid)
    """
    canonical_map: Dict[str, bool] = {}
    unmapped_keys: List[str] = []
    warnings: List[str] = []
    is_valid = True

    if raw is None:
        return canonical_map, unmapped_keys, warnings, is_valid

    parsed_obj: Any = raw
    if isinstance(raw, str):
        cleaned = raw.strip()
        if not cleaned:
            return canonical_map, unmapped_keys, warnings, is_valid

        # Attempt JSON parse if structured
        if cleaned.startswith(("{", "[")):
            try:
                parsed_obj = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                warnings.append(f"Malformed JSON in features string: {exc}")
                is_valid = False
                # Fall back to text splitting if not valid JSON
                parsed_obj = [item.strip() for item in cleaned.strip("[]{}").split(",") if item.strip()]
        else:
            # Comma or newline separated text list
            parsed_obj = [item.strip() for item in cleaned.replace("\n", ",").split(",") if item.strip()]

    # Case 1: Array / List of feature keys
    if isinstance(parsed_obj, (list, set, tuple)):
        for item in parsed_obj:
            if not isinstance(item, str):
                warnings.append(f"Ignored non-string array element: {type(item).__name__}")
                continue
            item_clean = item.strip()
            if not item_clean:
                continue

            canon = canonicalize_capability_key(item_clean)
            if canon and canon in CAPABILITY_REGISTRY:
                canonical_map[canon] = True
            else:
                unmapped_keys.append(item_clean)

    # Case 2: Dict / Object of feature keys to booleans
    elif isinstance(parsed_obj, dict):
        for raw_k, raw_v in parsed_obj.items():
            if not isinstance(raw_k, str):
                warnings.append(f"Ignored non-string key: {raw_k}")
                continue
            k_clean = raw_k.strip()

            # Strict Boolean Validation
            # In Python, bool is a subclass of int. We want strict bool (True or False),
            # NOT strings like "true", "false", and NOT arbitrary numbers.
            if isinstance(raw_v, bool):
                bool_val = raw_v
            else:
                # String booleans or invalid types must NOT grant capabilities
                warnings.append(f"Invalid non-boolean value for feature '{k_clean}': {raw_v!r} (type={type(raw_v).__name__})")
                is_valid = False
                bool_val = False

            canon = canonicalize_capability_key(k_clean)
            if canon and canon in CAPABILITY_REGISTRY:
                # Preserve explicit False! If already set to False, don't overwrite with True
                if canon in canonical_map:
                    # If any alias explicitly set False, False wins
                    canonical_map[canon] = canonical_map[canon] and bool_val
                else:
                    canonical_map[canon] = bool_val
            else:
                unmapped_keys.append(k_clean)

    else:
        warnings.append(f"Unrecognized features container type: {type(parsed_obj).__name__}")
        is_valid = False

    return canonical_map, unmapped_keys, warnings, is_valid


def resolve_effective_plan_capabilities(
    plan: Optional[Any],
    commercial_overrides: Optional[Dict[str, bool]] = None,
) -> NormalizedFeatures:
    """
    Resolve authoritative effective capabilities for a tenant given its SubscriptionPlan
    and optional tenant commercial overrides.

    Safety Invariants:
    1. If plan is None: return all capabilities False. Missing plan NEVER grants full access.
    2. Unknown plan display names without configured DB features NEVER grant full access.
    3. Unproven / non-sellable capabilities remain False.
    4. Explicit False in plan or override survives.
    5. Commercial overrides win over plan defaults, but cannot grant non-sellable capabilities.
    """
    result = NormalizedFeatures()

    # Base state: initialize all sellable capabilities
    effective_caps: Dict[str, bool] = {
        key: False for key, defn in CAPABILITY_REGISTRY.items() if defn.is_sellable
    }

    if plan is None:
        result.warnings.append("Tenant has no assigned subscription plan. All commercial capabilities disabled.")
        result.capabilities = effective_caps
        result.is_valid_config = False
        return result

    raw_features = getattr(plan, "features", None)
    plan_name = getattr(plan, "name", None)
    canonical_plan = canonicalize_plan_name(plan_name)

    # 1. Evaluate Plan Features
    if raw_features:
        parsed_caps, unmapped, warnings, is_valid = parse_raw_features(raw_features)
        result.unmapped_keys.extend(unmapped)
        result.warnings.extend(warnings)
        if not is_valid:
            result.is_valid_config = False

        # Apply parsed capabilities to sellable set
        for k, enabled in parsed_caps.items():
            if k in effective_caps:
                effective_caps[k] = enabled
    elif canonical_plan and canonical_plan in LAUNCH_PLAN_SPECS:
        # Plan has no explicit features JSON, but is a recognized launch tier
        # Apply approved default capabilities for this tier
        tier_spec = LAUNCH_PLAN_SPECS[canonical_plan]
        for cap_key in tier_spec.enabled_capabilities:
            if cap_key in effective_caps:
                effective_caps[cap_key] = True
    else:
        # Unknown plan name AND no explicit features in DB
        result.warnings.append(f"Plan '{plan_name}' is unrecognized and has no explicit feature configuration.")
        result.is_valid_config = False

    # 2. AI Feature Specific Checks
    # Check is_ai_enabled and ai_daily_limit from SubscriptionPlan model if present
    is_ai_enabled = getattr(plan, "is_ai_enabled", None)
    ai_daily_limit = getattr(plan, "ai_daily_limit", None)
    if is_ai_enabled is False or ai_daily_limit == 0:
        # Explicitly disabled AI at plan level
        effective_caps[CapabilityKey.AI_INSIGHTS.value] = False

    # 3. Apply Tenant Commercial Overrides
    if commercial_overrides and isinstance(commercial_overrides, dict):
        for override_k, override_v in commercial_overrides.items():
            if not isinstance(override_k, str):
                continue
            canon = canonicalize_capability_key(override_k)
            if not canon or canon not in effective_caps:
                result.unmapped_keys.append(override_k)
                continue

            if isinstance(override_v, bool):
                # Only sellable capabilities can be enabled by commercial override
                if is_sellable_capability(canon):
                    effective_caps[canon] = override_v
                else:
                    result.warnings.append(f"Commercial override cannot enable non-sellable capability '{canon}'.")
            else:
                result.warnings.append(f"Ignored non-boolean commercial override for '{override_k}': {override_v!r}")

    # Ensure non-sellable capabilities are strictly False
    for key, defn in CAPABILITY_REGISTRY.items():
        if not defn.is_sellable:
            effective_caps[key] = False

    result.capabilities = effective_caps
    return result
