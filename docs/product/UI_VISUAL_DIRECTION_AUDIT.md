# Dentix Visual Direction Audit — Plan 02 Phase 2

Baseline: `staging` @ `da83541cc3a320db92cc428dbb0d9815cf229534`  
Target direction: **Dentix Clinical Workspace**

## Executive finding

The current visual system is coherent enough to recognize, but it overuses translucency, blur, large radii, decorative gradients, large shadows and continuous motion. This makes dense clinical and financial workflows feel more like a promotional dashboard than a high-frequency clinical workspace. The problem is systemic: the old `frontend/DESIGN.md`, root CSS tokens and several shared primitives reinforce the same treatment.

Plan 02 should not globally flatten the product. It should first make content surfaces, hierarchy, interaction states and overlays predictable, then reduce decoration on representative screens while retaining branding and clinically useful semantic color.

## Current direction by dimension

### 1. Gradients

Current evidence:
- Global background uses large blurred sky/teal/slate color fields.
- `GlobalBanner` and several raw form actions use multi-color gradients.
- Empty/error/loading surfaces use gradient fills.

Assessment: **OVERUSED FOR WORKSPACE UI**.

Target:
- Keep gradients only where they communicate brand/system-level status and remain visually quiet.
- Do not use gradients as a default CTA, card, empty-state or page-background requirement.

### 2. Glass / blur / translucency

Current evidence:
- `--surface` is translucent in light and dark themes.
- `.glass-card` and `Card.jsx` actively apply backdrop blur.
- Toasts and command palette use translucent content surfaces + blur.
- Old `frontend/DESIGN.md` explicitly defines the experience around glassmorphism.

Assessment: **PRIMARY SYSTEMIC RISK**.

Target:
- Opaque content surfaces by default.
- Backdrop blur may be used on a backdrop or rare shell chrome, not as the default content-panel treatment.
- Popup/dialog/select/menu/date-picker content must never depend on background art for readability.

### 3. Shadows / elevation

Current evidence:
- `shadow-xl`/`shadow-2xl` appear in shared command palette, empty state, modal-like workflows and stat cards.
- CTA buttons frequently add colored glow shadows.

Assessment: **TOO LOUD AND NON-SEMANTIC**.

Target:
- Quiet documented elevation levels.
- Border + subtle shadow should carry most hierarchy.
- Strong elevation reserved for transient overlays that must separate from the workspace.

### 4. Radius

Current evidence:
- `rounded-xl`, `rounded-2xl`, `rounded-3xl`, arbitrary `[2.5rem]`, `[3rem]`, `[100px]` coexist.
- Old design guidance calls 1.5rem the default for major cards.

Assessment: **TOO LARGE / TOO ARBITRARY**.

Target:
- Small documented radius scale.
- Controls, cards and overlays should use named tiers rather than arbitrary values.
- Pills/full circles only where the shape has meaning.

### 5. Card density and cardification

Current evidence:
- Generic `Card` wraps content with surface/blur/radius.
- Stat/empty/loading/table sections frequently create additional nested cards.

Assessment: **OVER-CARDIFIED**.

Target:
- Use section boundaries, typography, spacing and rules before another container.
- Reserve cards for meaningful grouping/elevation, not every subsection.

### 6. Motion

Current evidence:
- Active-scale/ripple buttons, hover lift/rotate stat cards, bouncing banners, ping/pulse loaders, floating empty states and multiple custom modal transitions.

Assessment: **FUNCTIONAL + DECORATIVE MOTION ARE MIXED**.

Target:
- Functional motion only: state transition, spatial continuity, disclosure and loading feedback.
- Shared fast/standard/emphasized durations.
- `prefers-reduced-motion` respected by shared primitives.
- Avoid infinite decoration unless it communicates active loading/status.

### 7. Typography

Current evidence:
- Cairo and Inter are configured.
- Many primitives use bold/extrabold/black and uppercase/tracking-widest even for secondary metadata.

Assessment: **WEIGHT/HIERARCHY INFLATION**.

Target:
- Explicit page/section/body/label/caption/numeric/table roles.
- Use heavy weight for hierarchy, not as the default for every label and metadata line.
- Preserve Arabic/English legibility and numeric scanability.

### 8. Semantic color

Current evidence:
- Shared Badge/Alert contain success/warning/danger/info-like concepts.
- Other surfaces choose indigo/blue/teal/emerald/red decoratively.
- StatCard exposes decorative color names rather than metric meaning.

Assessment: **PARTIAL SEMANTICS, INCONSISTENT APPLICATION**.

Target:
- Primary for action/selection, not generic decoration.
- Success/warning/danger/info used for meaning.
- Selected/focus/disabled tokens become explicit.
- Clinical status colors require documented meaning at the feature layer.

### 9. Spacing and density

Current evidence:
- Shared primitives often default to p-6/p-8 and large vertical empty-state space.
- Finance/clinical tables need denser scan patterns than marketing-like cards.

Assessment: **TOO GENEROUS FOR HIGH-FREQUENCY DATA WORK**.

Target:
- Canonical spacing rhythm.
- Dense but breathable tables/forms.
- Compact controls available without one-off classes.

### 10. Hierarchy and navigation

Current evidence:
- `PageHeader` provides a useful common heading/action pattern.
- Tabs, cards and dashboards compete via shadows, accent blocks and motion.

Assessment: **FOUNDATION EXISTS; VISUAL PRIORITY NEEDS CALMING**.

Target:
- Page title → primary action → filters/secondary nav → content hierarchy must be obvious without decorative effects.
- Active navigation states should be calm and persistent, not glow-heavy.

## Representative primitives to harden before broad rollout

1. Button / IconButton
2. Input / Select / PatientSelect / DateTimePicker
3. Card / StatCard / PageHeader
4. Modal / ConfirmDialog / Tooltip / Toast / CommandPalette
5. DataTable / AdvancedTable / TabGroup
6. EmptyState / LoadingSpinner / Skeleton / Alert

## Visual change safety rules

- Do not flip all `bg-surface` consumers from translucent to opaque until representative screens and overlay regression are covered.
- Do not remove all blur globally; distinguish backdrop blur from content-surface blur.
- Do not shrink all radii with a search/replace; migrate through named token tiers.
- Do not remove motion without preserving loading/state feedback.
- Do not change semantic status colors to satisfy aesthetic uniformity.
- Do not update screenshots merely to make CI green; review the reason for every intentional baseline change.

## Phase 2 conclusion

The old glass-centric visual identity is now **supporting/historical direction**, not the target design contract. The replacement direction is a calmer clinical workspace: opaque content, restrained elevation, smaller radii, stronger typographic hierarchy, semantic color, denser data surfaces, functional motion and deliberate responsive/RTL behavior.