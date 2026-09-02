export {
    CLINICAL_CHART_PROJECTION_VERSION,
    PROJECTION_DENTITIONS,
    PROJECTION_TARGET_KINDS,
    PROJECTION_VISUAL_PHASES,
    createClinicalChartProjection,
    createProjectionTarget,
    createToothVisualState,
} from './clinicalChartProjection';
export {
    FINDING_CODES,
    PROCEDURE_CODES,
    TOOTH_LIFECYCLE_CODES,
    VISUAL_LAYER_ROLES,
    VISUAL_LAYER_SEQUENCE,
    VISUAL_RULE_REGISTRY,
    getVisualRule,
    resolveClinicalChartVisuals,
    resolveToothVisualInstructions,
} from './visualRuleRegistry';
export {
    DENTAL_ANATOMY_REGISTRY,
    DENTITIONS,
    PERMANENT_TOOTH_KEYS,
    PRIMARY_TOOTH_KEYS,
    TOOTH_TYPES,
    getDentalAnatomy,
} from './dentalAnatomyRegistry';
export {
    CHART_NOTATION_MODES,
    NOTATION_MODE_LABELS,
    fdiToUniversal,
    formatToothLabel,
} from './toothNotation';

