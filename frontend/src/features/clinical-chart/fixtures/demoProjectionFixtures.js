import {
    PROJECTION_DENTITIONS,
    PROJECTION_TARGET_KINDS,
    PROJECTION_VISUAL_PHASES,
    createClinicalChartProjection,
} from '../domain/clinicalChartProjection';

const wholeTooth = (toothKey) => ({
    kind: PROJECTION_TARGET_KINDS.TOOTH,
    toothKey: String(toothKey),
});

const surface = (toothKey, surfaceCode) => ({
    kind: PROJECTION_TARGET_KINDS.SURFACE,
    toothKey: String(toothKey),
    surfaceCode,
});

const root = (toothKey, rootId = 'single') => ({
    kind: PROJECTION_TARGET_KINDS.ROOT,
    toothKey: String(toothKey),
    rootId,
});

// A12-M01: Full 32 permanent adult teeth
export const ADULT_DENTITION_FIXTURE = createClinicalChartProjection({
    projectionId: 'demo-adult-dentition',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
});

export const ADULT_BASELINE_PROJECTION = ADULT_DENTITION_FIXTURE;

// A12-M02: Full 20 primary pediatric teeth
export const PRIMARY_DENTITION_FIXTURE = createClinicalChartProjection({
    projectionId: 'demo-primary-dentition',
    dentition: PROJECTION_DENTITIONS.PRIMARY,
});

// A12-M03: Mixed dentition (combination of permanent molars/incisors and primary canines/molars)
export const MIXED_DENTITION_TOOTH_ORDER = Object.freeze([
    // Maxillary: 16, 55, 54, 53, 12, 11 | 21, 22, 63, 64, 65, 26
    '16', '55', '54', '53', '12', '11', '21', '22', '63', '64', '65', '26',
    // Mandibular: 46, 85, 84, 83, 42, 41 | 31, 32, 73, 74, 75, 36
    '46', '85', '84', '83', '42', '41', '31', '32', '73', '74', '75', '36',
]);

export const MIXED_DENTITION_FIXTURE = createClinicalChartProjection({
    projectionId: 'demo-mixed-dentition',
    dentition: PROJECTION_DENTITIONS.MIXED,
    toothOrder: MIXED_DENTITION_TOOTH_ORDER,
});

// A12-M04: Local occlusal and proximal caries
export const CARIES_ON_SURFACE_FIXTURE = createClinicalChartProjection({
    projectionId: 'demo-caries-on-surface',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        46: {
            findings: [{
                visualId: 'finding-46-occlusal-caries',
                code: 'CARIES',
                phase: PROJECTION_VISUAL_PHASES.EXISTING,
                targets: [surface('46', 'O')],
            }],
        },
        16: {
            findings: [{
                visualId: 'finding-16-mesial-caries',
                code: 'CARIES',
                phase: PROJECTION_VISUAL_PHASES.EXISTING,
                targets: [surface('16', 'M')],
            }],
        },
        21: {
            findings: [{
                visualId: 'finding-21-distal-caries',
                code: 'CARIES',
                phase: PROJECTION_VISUAL_PHASES.EXISTING,
                targets: [surface('21', 'D')],
            }],
        },
    },
});

// A12-M05: Multi-surface MOD restoration
export const MOD_RESTORATION_FIXTURE = createClinicalChartProjection({
    projectionId: 'demo-mod-restoration',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        46: {
            procedures: [{
                visualId: 'procedure-46-mod-composite',
                code: 'REST_COMPOSITE',
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [surface('46', 'M'), surface('46', 'O'), surface('46', 'D')],
            }],
        },
        26: {
            procedures: [{
                visualId: 'procedure-26-mo-composite',
                code: 'REST_COMPOSITE',
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [surface('26', 'M'), surface('26', 'O')],
            }],
        },
    },
});

// A12-M06: Root canal therapy (RCT) with obturated canals
export const RCT_FIXTURE = createClinicalChartProjection({
    projectionId: 'demo-rct',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        11: {
            procedures: [{
                visualId: 'procedure-11-rct-completed',
                code: 'ENDO_RCT',
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [root('11', 'single')],
            }],
        },
        36: {
            procedures: [{
                visualId: 'procedure-36-rct-active',
                code: 'ENDO_RCT',
                phase: PROJECTION_VISUAL_PHASES.ACTIVE,
                targets: [root('36', 'mesial'), root('36', 'distal')],
            }],
        },
    },
});

// A12-M07: Full crown prosthetics
export const CROWN_FIXTURE = createClinicalChartProjection({
    projectionId: 'demo-crown',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        14: {
            procedures: [{
                visualId: 'procedure-14-crown-completed',
                code: 'PROS_CROWN',
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [wholeTooth('14')],
            }],
        },
        21: {
            procedures: [{
                visualId: 'procedure-21-crown-planned',
                code: 'PROS_CROWN',
                phase: PROJECTION_VISUAL_PHASES.PLANNED,
                targets: [wholeTooth('21')],
            }],
        },
    },
});

// A12-M08: Fixed partial denture (Bridge)
export const BRIDGE_FIXTURE = createClinicalChartProjection({
    projectionId: 'demo-bridge',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        21: {
            procedures: [{
                visualId: 'procedure-21-bridge-abutment',
                code: 'PROS_CROWN',
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [wholeTooth('21')],
            }],
        },
        22: {
            lifecycle: 'MISSING',
            procedures: [{
                visualId: 'procedure-22-bridge-pontic',
                code: 'PROS_BRIDGE',
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [wholeTooth('22')],
            }],
        },
        23: {
            procedures: [{
                visualId: 'procedure-23-bridge-abutment',
                code: 'PROS_CROWN',
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [wholeTooth('23')],
            }],
        },
    },
});

// A12-M09: Dental Implant (fixture + crown)
export const IMPLANT_FIXTURE = createClinicalChartProjection({
    projectionId: 'demo-implant',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        36: {
            lifecycle: 'MISSING',
            procedures: [
                {
                    visualId: 'procedure-36-implant-fixture',
                    code: 'IMPLANT_FIXTURE',
                    phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                    targets: [wholeTooth('36')],
                },
                {
                    visualId: 'procedure-36-implant-crown',
                    code: 'IMPLANT_CROWN',
                    phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                    targets: [wholeTooth('36')],
                },
            ],
        },
    },
});

// A12-M10: Planned Extraction
export const EXTRACTION_PLANNED_FIXTURE = createClinicalChartProjection({
    projectionId: 'demo-extraction-planned',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        38: {
            procedures: [{
                visualId: 'procedure-38-extract-planned',
                code: 'SURG_EXTRACTION',
                phase: PROJECTION_VISUAL_PHASES.PLANNED,
                targets: [wholeTooth('38')],
            }],
        },
    },
});

// A12-M11: Completed Extraction / Missing tooth
export const EXTRACTION_COMPLETED_FIXTURE = createClinicalChartProjection({
    projectionId: 'demo-extraction-completed',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        18: {
            lifecycle: 'MISSING',
        },
        28: {
            lifecycle: 'EXTRACTED',
            procedures: [{
                visualId: 'procedure-28-extract-completed',
                code: 'SURG_EXTRACTION',
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [wholeTooth('28')],
            }],
        },
    },
});

// Target Coverage demo projection combining multiple findings & procedures
export const TARGET_COVERAGE_PROJECTION = createClinicalChartProjection({
    projectionId: 'demo-target-coverage',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        11: {
            procedures: [{
                visualId: 'procedure-11-rct-active',
                code: 'ENDO_RCT',
                phase: PROJECTION_VISUAL_PHASES.ACTIVE,
                targets: [root('11', 'single')],
            }],
        },
        14: {
            procedures: [{
                visualId: 'procedure-14-crown-planned',
                code: 'PROS_CROWN',
                phase: PROJECTION_VISUAL_PHASES.PLANNED,
                targets: [wholeTooth('14')],
            }],
        },
        16: {
            findings: [{
                visualId: 'finding-16-pain',
                code: 'PAIN',
                targets: [{
                    kind: PROJECTION_TARGET_KINDS.CANAL,
                    toothKey: '16',
                    rootId: 'mesiobuccal',
                    canalId: null,
                }],
            }],
        },
        18: {
            disabled: true,
            annotations: [{
                annotationId: 'annotation-18-review',
                text: 'Demo-only disabled state',
            }],
        },
        46: {
            findings: [{
                visualId: 'finding-46-distal-caries',
                code: 'CARIES',
                phase: PROJECTION_VISUAL_PHASES.EXISTING,
                targets: [surface('46', 'D')],
            }],
            selection: {
                isSelected: true,
                targets: [surface('46', 'D')],
            },
        },
    },
    selection: {
        kind: PROJECTION_TARGET_KINDS.SURFACE,
        toothKey: '46',
        surfaceCode: 'D',
    },
});

export const CLINICAL_DEMO_FIXTURES = Object.freeze({
    adultDentition: ADULT_DENTITION_FIXTURE,
    primaryDentition: PRIMARY_DENTITION_FIXTURE,
    mixedDentition: MIXED_DENTITION_FIXTURE,
    cariesOnSurface: CARIES_ON_SURFACE_FIXTURE,
    modRestoration: MOD_RESTORATION_FIXTURE,
    rct: RCT_FIXTURE,
    crown: CROWN_FIXTURE,
    bridge: BRIDGE_FIXTURE,
    implant: IMPLANT_FIXTURE,
    extractionPlanned: EXTRACTION_PLANNED_FIXTURE,
    extractionCompleted: EXTRACTION_COMPLETED_FIXTURE,
});

export const DEMO_PROJECTION_FIXTURES = Object.freeze({
    adultBaseline: ADULT_BASELINE_PROJECTION,
    targetCoverage: TARGET_COVERAGE_PROJECTION,
});
