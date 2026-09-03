# Handoff to Gemini — Odontogram Foundation (Phase 1 Reconciled)

> **Status:** 🟢 **READY FOR GEMINI VNEXT (Part I Odontogram Foundation Reconciled & Verified)**  
> **Milestone:** Part I Odontogram Foundation Reconciliation Pass  
> **Target Track:** Gemini Core Track (Part II: Clinical Core, Treatment Plans, Work Items & Integrations)  
> **Reconciliation Branch:** `fix/odontogram-phase1-reconciliation`  
> **Current Staging SHA:** `d7852948f86f795045026dce9248e68d7b7aa4ef`  
> **Original Codex Merge-Base:** `b38636bdd82ec3ebf4ab728d87f13407bcb78d4b`  
> **Original Codex SHA:** `9b2c28f9dee211ba287876c270a7a50f0ae1e45a`

---

## 1. Executive Summary & Architecture Lock

Odontogram Foundation Phase 1 establishes the production-grade visual charting engine for Dentix.
All Phase 1 work from `feature/odontogram-foundation-codex` has been conceptually reconciled onto current `staging`:

- **Preserved Existing Design:** Retained native Dentix SVG identity and crown outlines.
- **Root Geometry Layer:** Added anatomically accurate single, bifurcated (14, 46), and trifurcated (16, 55) roots.
- **Interactive Surface Targets:** Added five accessible clipped polygon targets per tooth (M, D, O/I, B, L/P).
- **Dentition Matrix:** Full runtime support for `permanent`, `primary`, and `mixed` dentitions.
- **Chart Notation Abstraction:** Presentation-only Palmer, FDI, and Universal support derived from canonical FDI identities.
- **Visual Rule Registry:** Declarative mapping from clinical DTO state to stacked SVG render instructions.
- **Anti-Corruption Adapter Boundary:** The chart is strictly decoupled from backend persistence, API clients, and domain entities. It consumes a normalized input contract and emits neutral user-intent events.
- **Bidirectional Safety:** Inner SVG canvas maintains `dir="ltr"` to preserve anatomical quadrant axes under RTL or LTR shells.

---

## 2. Component Inventory & Directory Layout

All Phase 1 modules live in `frontend/src/features/clinical-chart/` and `frontend/src/features/dental/`:

```
frontend/src/features/
├── clinical-chart/
│   ├── components/
│   │   ├── ClinicalChartComparisonCard.jsx   # Isolated comparison card (owns local selection & filters)
│   │   ├── ClinicalChartInspector.jsx        # Read-only tooth & surface inspection panel
│   │   ├── ClinicalChartRenderer.jsx         # Pure stateless renderer consuming adapter input
│   │   ├── ClinicalChartWorkspaceShell.jsx   # Header, language selector (AR/EN), legend
│   │   └── clinicalChartWorkspaceCopy.js     # Bidirectional Arabic/English localization strings
│   ├── domain/
│   │   ├── chartNotation.js                  # Palmer, FDI, Universal presentation notation registry
│   │   ├── clinicalChartProjection.js        # Frontend projection validator & factory (schemaVersion 1)
│   │   ├── clinicalVisualCodes.js            # Canonical lifecycle, finding, and procedure enum codes
│   │   ├── dentalAnatomyRegistry.js          # 52 immutable FDI anatomy records (roots, crowns, anchors)
│   │   ├── toothDisplayMetrics.js            # Proportional metrics and layout anchors
│   │   └── visualRuleRegistry.js             # Visual instruction resolvers (colors, layers, effects)
│   ├── fixtures/
│   │   ├── a12ScenarioFixtures.js            # 11 immutable clinical scenario fixtures
│   │   └── visualRuleDemoProjection.js       # Live comparison projection fixture
│   ├── rendering/
│   │   ├── ClinicalChartRendererAdapter.js   # Public boundary: createClinicalChartRendererInput/Adapter
│   │   ├── ClinicalToothVisualLayers.jsx     # Visual effect layers for crowns and roots
│   │   ├── crownGeometry.js                  # Normalized crown SVG paths
│   │   ├── rootGeometry.js                   # Root geometry and apex/cervical anchors
│   │   ├── surfaceGeometry.js                # 5 clipped polygon surface hit targets per tooth
│   │   └── visualInstructionSelectors.js     # Instruction helper selectors
│   ├── tests/                               # 238 passing unit/integration tests
│   └── ClinicalChartWorkspace.jsx            # Standalone side-by-side comparison workspace
└── dental/
    ├── DentalChartSVG.jsx                    # Hardware-accelerated SVG chart canvas
    └── DentalChartSVG.test.jsx               # SVG integration test suite
```

---

## 3. Renderer Input Boundary (`ClinicalChartRendererInput`)

The renderer adapter entry point is `createClinicalChartRendererInput` from:
`frontend/src/features/clinical-chart/rendering/ClinicalChartRendererAdapter.js`

```typescript
interface ClinicalChartRendererInput {
  chartId: string;
  anatomyDefinition?: Record<string, DentalAnatomyRecord>;
  dentition?: 'permanent' | 'primary' | 'mixed';
  visualState: {
    teeth?: Record<string, ToothVisualState>;
    selection?: ProjectionTarget | null;
    toothOrder?: string[]; // Mandatory for mixed dentition
  };
  notationMode?: 'palmer' | 'fdi' | 'universal';
  interactionMode?: 'read-only' | 'edit';
  layers?: {
    roots?: boolean;
    surfaces?: boolean;
  };
  callbacks?: {
    onIntent?: (intent: ChartIntent) => void;
    onToothSelected?: (intent: ChartIntent) => void;
    onSurfaceSelected?: (intent: ChartIntent) => void;
    onRootSelected?: (intent: ChartIntent) => void;
    onMultiSelectChanged?: (intent: ChartIntent) => void;
  };
}
```

---

## 4. Intent Dispatch Contract (Frontend -> Consumer Flow)

The renderer NEVER performs HTTP requests, mutations, or direct database queries.
When interactive elements are triggered, the adapter dispatches neutral intent objects using the exact canonical constants:

### Exact Intent Constants (`CHART_INTENT_TYPES`)

* `chart/tooth-selected`
* `chart/surface-selected`
* `chart/root-selected`
* `chart/multi-select-changed`

> [!IMPORTANT]
> The intent types use forward-slash notation (`chart/tooth-selected`), NOT colon notation (`chart:tooth-selected`).

### Intent Payload Examples

```javascript
// Surface Selection Intent (e.g. Tooth 46 Occlusal surface clicked)
{
  type: 'chart/surface-selected',
  chartId: 'odontogram-current',
  target: {
    kind: 'surface',
    toothKey: '46',
    surfaceCode: 'O'
  }
}

// Tooth Selection Intent (e.g. Tooth 11 clicked in tooth-selection mode)
{
  type: 'chart/tooth-selected',
  chartId: 'odontogram-current',
  target: {
    kind: 'tooth',
    toothKey: '11'
  }
}

// Root Selection Intent
{
  type: 'chart/root-selected',
  chartId: 'odontogram-current',
  target: {
    kind: 'root',
    toothKey: '46',
    rootId: 'distal'
  }
}

// Multi-Select Changed Intent
{
  type: 'chart/multi-select-changed',
  chartId: 'odontogram-current',
  targets: [
    { kind: 'surface', toothKey: '46', surfaceCode: 'M' },
    { kind: 'surface', toothKey: '46', surfaceCode: 'O' }
  ]
}
```

---

## 5. Supported Dentition Contract

The renderer supports three distinct dentitions:

| Dentition | Key Set | Description |
| :--- | :--- | :--- |
| `permanent` | 32 teeth (11–18, 21–28, 31–38, 41–48) | Standard adult dental arch |
| `primary` | 20 teeth (51–55, 61–65, 71–75, 81–85) | Pediatric deciduous dental arch |
| `mixed` | Explicit order via `visualState.toothOrder` | Mixed adult & pediatric teeth in a single chart instance |

### Mixed Dentition Rules
- `dentition: 'mixed'` requires an explicit `visualState.toothOrder` array of FDI strings (e.g. 24 teeth in `MIXED_DENTITION_TOOTH_ORDER`).
- Must contain no duplicate keys.
- Every key must exist in `DENTAL_ANATOMY_REGISTRY`.
- `DentalChartSVG` renders the explicit mixed layout without falling back to adult permanent layout.

---

## 6. Supported Surface Codes & Geometry Model

The chart provides 5 accessible clipped polygon targets per tooth:

| Surface Code | Label | Region | Arch / Tooth Type Application |
| :---: | :---: | :---: | :--- |
| `M` | Mesial | West / East | Proximal surface toward dental midline |
| `D` | Distal | East / West | Proximal surface away from dental midline |
| `O` | Occlusal | Center | Biting surface of posterior teeth (premolars & molars) |
| `I` | Incisal | Center | Cutting edge of anterior teeth (incisors & canines) |
| `B` | Buccal / Facial | Outer | Surface toward cheeks / lips |
| `L` | Lingual | Inner | Surface toward tongue (**Mandibular arch only**) |
| `P` | Palatal | Inner | Surface toward palate (**Maxillary arch only**) |

### Arch-Specific P/L Behavior
- **Maxillary teeth (upper arch):** Inner surface is strictly Palatal (`P`).
- **Mandibular teeth (lower arch):** Inner surface is strictly Lingual (`L`).
- **Anterior teeth:** Center region is Incisal (`I`).
- **Posterior teeth:** Center region is Occlusal (`O`).

---

## 7. Canonical Visual Codes (Findings & Procedures)

All codes are defined in `clinicalVisualCodes.js` and resolved by `visualRuleRegistry.js`:

### Tooth Lifecycle Codes (`TOOTH_LIFECYCLE_CODES`)
* `PRESENT` — Tooth present in arch (default).
* `MISSING` — Tooth congenitally missing or absent.
* `EXTRACTED` — Tooth previously extracted.
* `IMPACTED` — Tooth impacted.
* `UNERUPTED` — Tooth not yet erupted.

### Finding Codes (`FINDING_CODES`)
* `CARIES` — Crown surface caries lesion (Red fill `#ef4444`).
* `FRACTURE` — Tooth crown fracture (Clipped jagged line).
* `PAIN` — Symptomatic pain marker on crown/root.

### Procedure Codes (`PROCEDURE_CODES`)
* `REST_COMPOSITE` — Tooth-colored composite restoration (Blue `#3b82f6`).
* `ENDO_RCT` — Endodontic root canal therapy (Purple canal fill `#a855f7`).
* `PROS_CROWN` — Prosthetic crown (Gold outline/shading `#eab308`).
* `PROS_BRIDGE` — Fixed prosthetic bridge unit / abutment / pontic.
* `IMPLANT_FIXTURE` — Endosseous implant fixture replacing natural root.
* `IMPLANT_CROWN` — Implant-supported prosthetic crown.
* `SURG_EXTRACTION` — Surgical tooth extraction (diagonal hash overlay).

> [!WARNING]
> Do NOT invent or send non-canonical codes like `IMPL_FIXTURE`, `EXT_PLANNED`, or `PROS_BRIDGE_PONTIC`. Use the exact enum values defined above.

---

## 8. Visual Phases (`PROJECTION_VISUAL_PHASES`)

Visual entries accept four lifecycle phases that determine visual layer styling and z-indexing:

* `existing` — Pre-existing condition or historical work done elsewhere (`#94a3b8`).
* `planned` — Proposed / planned treatment in active plan (Dashed / high-visibility border).
* `active` — Currently in-progress treatment during an active visit.
* `completed` — Completed treatment performed at this clinic (`#10b981` / solid accent).

---

## 9. Frontend Projection DTO Schema

> [!IMPORTANT]
> This schema is a **Frontend Adapter Projection DTO** (`schemaVersion: 1`), NOT the backend database schema. The backend database will store normalized clinical work items, appointments, and treatment plans in PostgreSQL tables. A backend projection service will map those entities into this frontend DTO format for rendering.

```typescript
interface ClinicalChartProjection {
  schemaVersion: 1;
  projectionId: string;
  dentition: 'permanent' | 'primary' | 'mixed';
  toothOrder: string[]; // FDI keys in display order (e.g. 32 adult, 20 primary, 24 mixed)
  teeth: {
    [toothKey: string]: {
      toothKey: string;
      lifecycle: 'PRESENT' | 'MISSING' | 'EXTRACTED' | 'IMPACTED' | 'UNERUPTED';
      findings: Array<{
        visualId: string;
        code: 'CARIES' | 'FRACTURE' | 'PAIN';
        phase: 'existing' | 'planned' | 'active' | 'completed';
        targets: Array<{
          kind: 'tooth' | 'surface' | 'root' | 'canal';
          toothKey: string;
          surfaceCode?: 'M' | 'D' | 'O' | 'I' | 'B' | 'L' | 'P';
          rootId?: 'mesial' | 'distal' | 'palatal' | 'single' | 'mesiobuccal' | 'distobuccal';
          canalId?: string;
        }>;
        annotations?: Array<{ text: string; target?: object }>;
      }>;
      procedures: Array<{
        visualId: string;
        code: 'REST_COMPOSITE' | 'ENDO_RCT' | 'PROS_CROWN' | 'PROS_BRIDGE' | 'IMPLANT_FIXTURE' | 'IMPLANT_CROWN' | 'SURG_EXTRACTION';
        phase: 'existing' | 'planned' | 'active' | 'completed';
        targets: Array<{
          kind: 'tooth' | 'surface' | 'root' | 'canal';
          toothKey: string;
          surfaceCode?: 'M' | 'D' | 'O' | 'I' | 'B' | 'L' | 'P';
          rootId?: 'mesial' | 'distal' | 'palatal' | 'single' | 'mesiobuccal' | 'distobuccal';
          canalId?: string;
        }>;
        annotations?: Array<{ text: string; target?: object }>;
      }>;
      selection: {
        isSelected?: boolean;
        targets: Array<{
          kind: 'tooth' | 'surface' | 'root';
          toothKey: string;
          surfaceCode?: string;
        }>;
      };
      disabled?: boolean;
      annotations?: Array<{ text: string }>;
    };
  };
  selection: {
    kind: 'tooth' | 'surface' | 'root';
    toothKey: string;
    surfaceCode?: string;
    rootId?: string;
  } | null;
}
```

---

## 10. Gemini Integration Guardrails for Part II

When Gemini Core initiates Part II (Clinical Core Backend & Integration):

1. **Follow Layered Architecture:** Router -> Service -> CRUD -> Database flow.
2. **Business Logic in Services:** Never put clinical pricing, tooth conflict detection, or state transitions in routers or frontend components.
3. **Tenant Isolation:** Enforce `tenant_scope.py` or tenant-aware session dependencies on all clinical endpoints.
4. **Preserve Phase 1 Frontend Geometry:** Do not modify `DentalChartSVG.jsx`, `crownGeometry.js`, `rootGeometry.js`, or `surfaceGeometry.js`.
5. **Connect Via React Query:** Frontend views will fetch projections from FastAPI backend endpoints using TanStack React Query (`@tanstack/react-query`) and feed the resulting DTO into `ClinicalChartRendererAdapter`.
6. **Intent Binding:** Wire emitted intents (`chart/surface-selected`, `chart/tooth-selected`) to Treatment Plan drawer / procedure recording actions in Part II.

---

## 11. Hard Stop Declaration

Part I (Odontogram Foundation) is **100% RECONCILED, VERIFIED, AND SEALED**.

```
========================================================================
STATUS: WAITING FOR EXTERNAL REVIEW BEFORE GEMINI PART II
ALL ODONTOGRAM FOUNDATION TASKS VERIFIED (238 / 238 TESTS PASS)
========================================================================
```
