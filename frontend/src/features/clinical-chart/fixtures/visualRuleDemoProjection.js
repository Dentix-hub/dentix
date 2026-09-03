import {
    PROJECTION_DENTITIONS,
    PROJECTION_TARGET_KINDS,
    PROJECTION_VISUAL_PHASES,
    createClinicalChartProjection,
} from '../domain/clinicalChartProjection';

const wholeTooth = (toothKey) => ({
    kind: PROJECTION_TARGET_KINDS.TOOTH,
    toothKey,
});

const surface = (toothKey, surfaceCode) => ({
    kind: PROJECTION_TARGET_KINDS.SURFACE,
    toothKey,
    surfaceCode,
});

export const VISUAL_RULE_DEMO_PROJECTION = createClinicalChartProjection({
    projectionId: 'demo-visual-rule-coverage',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        11: {
            procedures: [{
                code: 'ENDO_RCT',
                phase: PROJECTION_VISUAL_PHASES.ACTIVE,
                targets: [{ kind: 'root', toothKey: '11', rootId: 'single' }],
            }],
        },
        12: { findings: [{ code: 'PAIN', targets: [wholeTooth('12')] }] },
        13: { findings: [{ code: 'FRACTURE', targets: [wholeTooth('13')] }] },
        14: {
            procedures: [{
                code: 'PROS_CROWN',
                phase: PROJECTION_VISUAL_PHASES.PLANNED,
                targets: [wholeTooth('14')],
            }],
        },
        15: { lifecycle: 'UNERUPTED' },
        16: { lifecycle: 'IMPACTED' },
        17: { lifecycle: 'EXTRACTED' },
        18: { lifecycle: 'MISSING' },
        21: {
            procedures: [{ code: 'PROS_CROWN', targets: [wholeTooth('21')] }],
        },
        22: {
            procedures: [{ code: 'PROS_BRIDGE', targets: [wholeTooth('22')] }],
        },
        23: {
            lifecycle: 'MISSING',
            procedures: [
                { code: 'IMPLANT_FIXTURE', targets: [wholeTooth('23')] },
                { code: 'IMPLANT_CROWN', targets: [wholeTooth('23')] },
            ],
        },
        24: {
            procedures: [{
                code: 'SURG_EXTRACTION',
                phase: PROJECTION_VISUAL_PHASES.PLANNED,
                targets: [wholeTooth('24')],
            }],
        },
        25: {
            procedures: [{
                code: 'SURG_EXTRACTION',
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [wholeTooth('25')],
            }],
        },
        44: {
            procedures: [{
                code: 'REST_COMPOSITE',
                targets: [surface('44', 'M'), surface('44', 'O'), surface('44', 'D')],
            }],
        },
        45: {
            procedures: [{
                code: 'REST_COMPOSITE',
                phase: PROJECTION_VISUAL_PHASES.PLANNED,
                targets: [surface('45', 'O')],
            }],
        },
        46: {
            findings: [{
                code: 'CARIES',
                targets: [surface('46', 'D')],
            }],
        },
    },
});
