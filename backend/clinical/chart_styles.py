"""Canonical procedure chart style definitions and palette keys.

Strictly follows A2 (templates) and A3 (12-color palette) from UX Stabilization Brief U4.
"""

from typing import Final, Literal

ChartStyleTemplate = Literal[
    "REST_COMPOSITE",
    "ENDO_RCT",
    "PROS_CROWN",
    "PROS_BRIDGE",
    "IMPLANT_FIXTURE",
    "IMPLANT_CROWN",
    "SURG_EXTRACTION",
    "MARKER",
    "NONE",
]

ChartStyleColorKey = Literal[
    "blue",
    "teal",
    "green",
    "lime",
    "amber",
    "orange",
    "purple",
    "indigo",
    "pink",
    "cyan",
    "slate",
    "brown",
]

CHART_STYLE_TEMPLATES: Final[tuple[str, ...]] = (
    "REST_COMPOSITE",
    "ENDO_RCT",
    "PROS_CROWN",
    "PROS_BRIDGE",
    "IMPLANT_FIXTURE",
    "IMPLANT_CROWN",
    "SURG_EXTRACTION",
    "MARKER",
    "NONE",
)

RENDERABLE_TEMPLATES: Final[tuple[str, ...]] = (
    "REST_COMPOSITE",
    "ENDO_RCT",
    "PROS_CROWN",
    "PROS_BRIDGE",
    "IMPLANT_FIXTURE",
    "IMPLANT_CROWN",
    "SURG_EXTRACTION",
)

CHART_STYLE_COLOR_KEYS: Final[tuple[str, ...]] = (
    "blue",
    "teal",
    "green",
    "lime",
    "amber",
    "orange",
    "purple",
    "indigo",
    "pink",
    "cyan",
    "slate",
    "brown",
)
