import {
    PROJECTION_DENTITIONS,
    PROJECTION_TARGET_KINDS,
    PROJECTION_VISUAL_PHASES,
    createClinicalChartProjection,
} from '../domain/clinicalChartProjection';
import {
    FINDING_CODES,
    PROCEDURE_CODES,
    TOOTH_LIFECYCLE_CODES,
} from '../domain/clinicalVisualCodes';

const wholeTooth = (toothKey) => ({
    kind: PROJECTION_TARGET_KINDS.TOOTH,
    toothKey,
});

const surface = (toothKey, surfaceCode) => ({
    kind: PROJECTION_TARGET_KINDS.SURFACE,
    toothKey,
    surfaceCode,
});

const root = (toothKey, rootId) => ({
    kind: PROJECTION_TARGET_KINDS.ROOT,
    toothKey,
    rootId,
});

export const MIXED_DENTITION_TOOTH_ORDER = Object.freeze([
    '26', '65', '64', '63', '22', '21',
    '11', '12', '53', '54', '55', '16',
    '36', '75', '74', '73', '32', '31',
    '41', '42', '83', '84', '85', '46',
]);

export const A12_ADULT_DENTITION_FIXTURE = createClinicalChartProjection({
    projectionId: 'a12-adult-dentition',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
});

export const A12_PRIMARY_DENTITION_FIXTURE = createClinicalChartProjection({
    projectionId: 'a12-primary-dentition',
    dentition: PROJECTION_DENTITIONS.PRIMARY,
});

export const A12_MIXED_DENTITION_FIXTURE = createClinicalChartProjection({
    projectionId: 'a12-mixed-dentition',
    dentition: PROJECTION_DENTITIONS.MIXED,
    toothOrder: MIXED_DENTITION_TOOTH_ORDER,
});

export const A12_DISTAL_CARIES_46_FIXTURE = createClinicalChartProjection({
    projectionId: 'a12-distal-caries-46',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        46: {
            findings: [{
                visualId: 'a12-caries-46-distal',
                code: FINDING_CODES.CARIES,
                phase: PROJECTION_VISUAL_PHASES.EXISTING,
                targets: [surface('46', 'D')],
            }],
        },
    },
});

export const A12_MOD_COMPOSITE_46_FIXTURE = createClinicalChartProjection({
    projectionId: 'a12-mod-composite-46',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        46: {
            procedures: [{
                visualId: 'a12-composite-46-mod',
                code: PROCEDURE_CODES.REST_COMPOSITE,
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [
                    surface('46', 'M'),
                    surface('46', 'O'),
                    surface('46', 'D'),
                ],
            }],
        },
    },
});

export const A12_RCT_FIXTURE = createClinicalChartProjection({
    projectionId: 'a12-rct-46',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        46: {
            procedures: [{
                visualId: 'a12-rct-46',
                code: PROCEDURE_CODES.ENDO_RCT,
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [
                    root('46', 'mesial'),
                    root('46', 'distal'),
                ],
            }],
        },
    },
});

export const A12_CROWN_FIXTURE = createClinicalChartProjection({
    projectionId: 'a12-crown-36',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        36: {
            procedures: [{
                visualId: 'a12-crown-36',
                code: PROCEDURE_CODES.PROS_CROWN,
                phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                targets: [wholeTooth('36')],
            }],
        },
    },
});

export const A12_MISSING_TOOTH_FIXTURE = createClinicalChartProjection({
    projectionId: 'a12-missing-38',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        38: {
            lifecycle: TOOTH_LIFECYCLE_CODES.MISSING,
        },
    },
});

export const A12_IMPLANT_FIXTURE = createClinicalChartProjection({
    projectionId: 'a12-implant-23',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        23: {
            lifecycle: TOOTH_LIFECYCLE_CODES.MISSING,
            procedures: [
                {
                    visualId: 'a12-implant-fixture-23',
                    code: PROCEDURE_CODES.IMPLANT_FIXTURE,
                    phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                    targets: [wholeTooth('23')],
                },
                {
                    visualId: 'a12-implant-crown-23',
                    code: PROCEDURE_CODES.IMPLANT_CROWN,
                    phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                    targets: [wholeTooth('23')],
                },
            ],
        },
    },
});

const completedBridgeUnit = (toothKey, visualId) => ({
    visualId,
    code: PROCEDURE_CODES.PROS_BRIDGE,
    phase: PROJECTION_VISUAL_PHASES.COMPLETED,
    targets: [wholeTooth(toothKey)],
});

export const A12_BRIDGE_14_15_16_FIXTURE = createClinicalChartProjection({
    projectionId: 'a12-bridge-14-15-16',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        14: {
            procedures: [completedBridgeUnit('14', 'a12-bridge-abutment-14')],
        },
        15: {
            lifecycle: TOOTH_LIFECYCLE_CODES.MISSING,
            procedures: [completedBridgeUnit('15', 'a12-bridge-pontic-15')],
        },
        16: {
            procedures: [completedBridgeUnit('16', 'a12-bridge-abutment-16')],
        },
    },
});

export const A12_EXISTING_AND_PLANNED_FIXTURE = createClinicalChartProjection({
    projectionId: 'a12-existing-and-planned-46',
    dentition: PROJECTION_DENTITIONS.PERMANENT,
    teeth: {
        46: {
            procedures: [
                {
                    visualId: 'a12-existing-composite-46',
                    code: PROCEDURE_CODES.REST_COMPOSITE,
                    phase: PROJECTION_VISUAL_PHASES.COMPLETED,
                    targets: [surface('46', 'O')],
                },
                {
                    visualId: 'a12-planned-crown-46',
                    code: PROCEDURE_CODES.PROS_CROWN,
                    phase: PROJECTION_VISUAL_PHASES.PLANNED,
                    targets: [wholeTooth('46')],
                },
            ],
        },
    },
});

export const A12_SCENARIO_FIXTURES = Object.freeze({
    adultDentition: A12_ADULT_DENTITION_FIXTURE,
    primaryDentition: A12_PRIMARY_DENTITION_FIXTURE,
    mixedDentition: A12_MIXED_DENTITION_FIXTURE,
    distalCaries46: A12_DISTAL_CARIES_46_FIXTURE,
    modComposite46: A12_MOD_COMPOSITE_46_FIXTURE,
    rct: A12_RCT_FIXTURE,
    crown: A12_CROWN_FIXTURE,
    missingTooth: A12_MISSING_TOOTH_FIXTURE,
    implant: A12_IMPLANT_FIXTURE,
    bridge141516: A12_BRIDGE_14_15_16_FIXTURE,
    existingAndPlanned: A12_EXISTING_AND_PLANNED_FIXTURE,
});
