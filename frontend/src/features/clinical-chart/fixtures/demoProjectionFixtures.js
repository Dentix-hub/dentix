import {
    PROJECTION_DENTITIONS,
    PROJECTION_TARGET_KINDS,
    PROJECTION_VISUAL_PHASES,
    createClinicalChartProjection,
} from '../domain/clinicalChartProjection';

export const ADULT_BASELINE_PROJECTION = createClinicalChartProjection({
    projectionId: 'demo-adult-baseline',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
});

export const TARGET_COVERAGE_PROJECTION = createClinicalChartProjection({
    projectionId: 'demo-target-coverage',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        11: {
            procedures: [{
                visualId: 'procedure-11-rct-active',
                code: 'ENDO_RCT',
                phase: PROJECTION_VISUAL_PHASES.ACTIVE,
                targets: [{
                    kind: PROJECTION_TARGET_KINDS.ROOT,
                    toothKey: '11',
                    rootId: 'single',
                }],
            }],
        },
        14: {
            procedures: [{
                visualId: 'procedure-14-crown-planned',
                code: 'PROS_CROWN',
                phase: PROJECTION_VISUAL_PHASES.PLANNED,
                targets: [{
                    kind: PROJECTION_TARGET_KINDS.TOOTH,
                    toothKey: '14',
                }],
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
                targets: [{
                    kind: PROJECTION_TARGET_KINDS.SURFACE,
                    toothKey: '46',
                    surfaceCode: 'D',
                }],
            }],
            selection: {
                isSelected: true,
                targets: [{
                    kind: PROJECTION_TARGET_KINDS.SURFACE,
                    toothKey: '46',
                    surfaceCode: 'D',
                }],
            },
        },
    },
    selection: {
        kind: PROJECTION_TARGET_KINDS.SURFACE,
        toothKey: '46',
        surfaceCode: 'D',
    },
});

export const DEMO_PROJECTION_FIXTURES = Object.freeze({
    adultBaseline: ADULT_BASELINE_PROJECTION,
    targetCoverage: TARGET_COVERAGE_PROJECTION,
});
