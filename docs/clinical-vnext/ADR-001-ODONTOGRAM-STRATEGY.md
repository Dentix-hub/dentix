# ADR-001 — Odontogram Rendering Strategy

- **Status:** Accepted
- **Decision date:** 2026-08-28
- **Owner approval token:** `APPROVE ODONTOGRAM STRATEGY: C`
- **Approved strategy:** `DENTIX_NATIVE`

## Decision

DENTIX will own the odontogram renderer, interaction state, clinical visual semantics, and test coverage. The approved visual contract is the anatomy in `Gemini_Generated_Image_eldvbteldvbteldv.png` together with the approved procedure-effects specimen stored at:

`frontend/src/features/clinical-chart-v2/assets/procedure-effects-approval-v1.png`

The renderer must preserve the approved semi-realistic anatomy and express procedures as anatomical layers rather than generic badges, dots, or whole-tooth recoloring.

## Owner Clarification — Per-Tooth Asset Families (2026-08-28)

The production anatomy source is the transparent adult dentition atlas stored at
`frontend/src/features/clinical-chart-v2/assets/approved-adult-dentition-transparent-atlas.png`.
It is extracted into 32 independently addressable FDI assets. The original RGB tooth pixels are locked;
cleanup may change only external alpha/background pixels.

The procedure-effects board remains a visual reference and must never replace a tooth in the chart.
Every visible condition or procedure requires anatomy-matched artwork for the exact FDI tooth:

- crown-surface conditions/restorations use transparent overlays aligned to that tooth's own crown and surface;
- endodontic states use chamber/canal artwork aligned to that tooth's own root anatomy;
- crowns, implants, missing teeth, and other anatomy-changing states use dedicated whole-tooth variants;
- bridges and other multi-tooth work use a dedicated grouped asset contract;
- if a dedicated asset is absent, the renderer must fail closed visually and must not fall back to generic procedure artwork.

## Adapter Boundary

```text
DENTIX clinical projection DTO
    -> normalization / legacy adapter
    -> ClinicalToothRenderer
    -> anatomy + procedure + lifecycle + interaction layers
```

Clinical state must not store SVG paths, bitmap coordinates, renderer-specific state, or presentation colors. Renderer events must emit DENTIX-neutral tooth/surface intents and must not call persistence APIs directly.

## Visual Rules

- Caries and restorations follow the affected clinical crown surface; caries must never appear on a root.
- RCT occupies the pulp chamber and actual root canals.
- A crown is a full anatomical crown shell.
- An implant consists of fixture, abutment, and anatomy-matched crown.
- A bridge consists of anatomical abutment crowns, pontic, and connectors.
- Missing teeth preserve alignment using a restrained ghost silhouette and X.
- Procedure meaning uses a stable semantic color plus anatomical geometry.
- Lifecycle uses stroke, dash, and opacity without changing the procedure's semantic color.
- Planned treatment remains hidden by default in the future full chart.

## Licensing and Asset Ownership

No third-party odontogram runtime, Open Dental source, proprietary SVG, or external clinical state model is adopted. The reference images are visual approval artifacts; production rendering code and geometry remain DENTIX-owned. No new dependency is introduced by this decision.

## Known Limitations

- The approved raster boards are visual contracts, not production rendering assets or canonical clinical data.
- Native anatomy and procedure geometry must be verified at full-mouth scale, mobile scale, and high-DPI rendering.
- Primary and mixed dentition remain later plan requirements and are not implied complete by the adult specimen.
- Full surface selection, multi-instance history comparison, and production clinical integration remain gated work.

## Fallback and Exit Strategy

The renderer remains replaceable behind the DENTIX projection/adapter boundary. If native rendering fails defined clinical, accessibility, or performance gates, another renderer may be evaluated without a database migration or clinical-schema rewrite.

## Conditions for Reconsideration

Revisit this ADR only if the native renderer fails a documented acceptance gate, becomes materially unmaintainable, or a legally compatible renderer demonstrates superior anatomy and procedure semantics while preserving the DENTIX adapter boundary.
