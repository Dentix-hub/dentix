import {
    DENTAL_ANATOMY_REGISTRY,
    DENTITIONS,
    PERMANENT_TOOTH_KEYS,
    PRIMARY_TOOTH_KEYS,
} from './dentalAnatomyRegistry';

export const CLINICAL_CHART_PROJECTION_VERSION = 1;

export const PROJECTION_DENTITIONS = Object.freeze({
    ...DENTITIONS,
    MIXED: 'mixed',
});

export const PROJECTION_TARGET_KINDS = Object.freeze({
    TOOTH: 'tooth',
    SURFACE: 'surface',
    ROOT: 'root',
    CANAL: 'canal',
});

export const PROJECTION_VISUAL_PHASES = Object.freeze({
    EXISTING: 'existing',
    PLANNED: 'planned',
    ACTIVE: 'active',
    COMPLETED: 'completed',
});

const PROJECTION_SURFACE_CODE_PATTERN = /^(M|D|O|I|B|L|P)$/;

const assertRecord = (name, value) => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        throw new TypeError(`${name} must be an object`);
    }
};

const requireString = (name, value) => {
    if (typeof value !== 'string' || value.trim() === '') {
        throw new TypeError(`${name} must be a non-empty string`);
    }
    return value.trim();
};

const requireArray = (name, value) => {
    if (!Array.isArray(value)) throw new TypeError(`${name} must be an array`);
    return value;
};

const optionalBoolean = (name, value, fallback = false) => {
    if (value == null) return fallback;
    if (typeof value !== 'boolean') throw new TypeError(`${name} must be a boolean`);
    return value;
};

const assertEnumValue = (name, value, allowedValues) => {
    if (!allowedValues.includes(value)) {
        throw new TypeError(`${name} must be one of: ${allowedValues.join(', ')}`);
    }
};

const normalizeToothKey = (toothKey, anatomyDefinition) => {
    const normalizedKey = String(toothKey);
    if (!anatomyDefinition[normalizedKey]) {
        throw new RangeError(`Unknown tooth key: ${normalizedKey}`);
    }
    return normalizedKey;
};

const assertRootId = (toothKey, rootId, anatomyDefinition) => {
    const normalizedRootId = requireString('target.rootId', rootId);
    const anatomy = anatomyDefinition[toothKey];
    if (!anatomy.rootOutlineRefs.some((root) => root.rootId === normalizedRootId)) {
        throw new RangeError(`Unknown root ${normalizedRootId} for tooth ${toothKey}`);
    }
    return normalizedRootId;
};

/**
 * A serializable visual target. `canalId: null` is intentional: the current
 * anatomy provides root-owned canal placeholders without claiming a final
 * clinical canal taxonomy.
 *
 * @typedef {object} ProjectionTarget
 * @property {'tooth'|'surface'|'root'|'canal'} kind
 * @property {string} toothKey Stable FDI identity.
 * @property {string} [surfaceCode]
 * @property {string} [rootId]
 * @property {string|null} [canalId]
 */

/** @returns {Readonly<ProjectionTarget>} */
export const createProjectionTarget = (target, anatomyDefinition = DENTAL_ANATOMY_REGISTRY) => {
    assertRecord('target', target);
    const kind = requireString('target.kind', target.kind);
    assertEnumValue('target.kind', kind, Object.values(PROJECTION_TARGET_KINDS));
    const toothKey = normalizeToothKey(target.toothKey, anatomyDefinition);

    if (kind === PROJECTION_TARGET_KINDS.SURFACE) {
        const surfaceCode = requireString('target.surfaceCode', target.surfaceCode).toUpperCase();
        if (!PROJECTION_SURFACE_CODE_PATTERN.test(surfaceCode)) {
            throw new RangeError(`Unsupported surface code: ${surfaceCode}`);
        }
        return Object.freeze({
            kind,
            toothKey,
            surfaceCode,
        });
    }

    if (kind === PROJECTION_TARGET_KINDS.ROOT) {
        return Object.freeze({
            kind,
            toothKey,
            rootId: assertRootId(toothKey, target.rootId, anatomyDefinition),
        });
    }

    if (kind === PROJECTION_TARGET_KINDS.CANAL) {
        return Object.freeze({
            kind,
            toothKey,
            rootId: assertRootId(toothKey, target.rootId, anatomyDefinition),
            canalId: target.canalId == null
                ? null
                : requireString('target.canalId', target.canalId),
        });
    }

    return Object.freeze({ kind, toothKey });
};

const createAnnotation = (annotation, fallbackId, anatomyDefinition) => {
    assertRecord('annotation', annotation);
    return Object.freeze({
        annotationId: requireString('annotation.annotationId', annotation.annotationId ?? fallbackId),
        text: requireString('annotation.text', annotation.text),
        target: annotation.target
            ? createProjectionTarget(annotation.target, anatomyDefinition)
            : null,
    });
};

const createVisualEntry = ({
    entry,
    entryType,
    fallbackId,
    toothKey,
    anatomyDefinition,
}) => {
    assertRecord(entryType, entry);
    const phase = entry.phase ?? (entryType === 'finding'
        ? PROJECTION_VISUAL_PHASES.EXISTING
        : PROJECTION_VISUAL_PHASES.COMPLETED);
    assertEnumValue(`${entryType}.phase`, phase, Object.values(PROJECTION_VISUAL_PHASES));

    const targets = requireArray(`${entryType}.targets`, entry.targets ?? [{
        kind: PROJECTION_TARGET_KINDS.TOOTH,
        toothKey,
    }]).map((target) => createProjectionTarget(target, anatomyDefinition));

    if (targets.length === 0) throw new TypeError(`${entryType}.targets must not be empty`);
    if (targets.some((target) => target.toothKey !== toothKey)) {
        throw new RangeError(`${entryType} targets must belong to tooth ${toothKey}`);
    }

    const annotations = requireArray(`${entryType}.annotations`, entry.annotations ?? [])
        .map((annotation, index) => createAnnotation(
            annotation,
            `${fallbackId}:annotation:${index + 1}`,
            anatomyDefinition,
        ));
    if (annotations.some((annotation) => (
        annotation.target && annotation.target.toothKey !== toothKey
    ))) {
        throw new RangeError(`${entryType} annotation targets must belong to tooth ${toothKey}`);
    }

    return Object.freeze({
        visualId: requireString(`${entryType}.visualId`, entry.visualId ?? fallbackId),
        code: requireString(`${entryType}.code`, entry.code),
        phase,
        targets: Object.freeze(targets),
        annotations: Object.freeze(annotations),
    });
};

/**
 * Per-tooth projection shape consumed by later visual rules.
 *
 * @typedef {object} ToothVisualState
 * @property {string} toothKey Stable FDI identity.
 * @property {string} lifecycle Semantic tooth lifecycle code.
 * @property {ReadonlyArray<object>} findings
 * @property {ReadonlyArray<object>} procedures
 * @property {{isSelected: boolean, targets: ReadonlyArray<ProjectionTarget>}} selection
 * @property {boolean} disabled
 * @property {ReadonlyArray<object>} annotations
 */

/** @returns {Readonly<ToothVisualState>} */
export const createToothVisualState = (
    state,
    anatomyDefinition = DENTAL_ANATOMY_REGISTRY,
) => {
    assertRecord('tooth visual state', state);
    const toothKey = normalizeToothKey(state.toothKey, anatomyDefinition);
    const findings = requireArray('findings', state.findings ?? []).map((entry, index) => (
        createVisualEntry({
            entry,
            entryType: 'finding',
            fallbackId: `finding:${toothKey}:${index + 1}`,
            toothKey,
            anatomyDefinition,
        })
    ));
    const procedures = requireArray('procedures', state.procedures ?? []).map((entry, index) => (
        createVisualEntry({
            entry,
            entryType: 'procedure',
            fallbackId: `procedure:${toothKey}:${index + 1}`,
            toothKey,
            anatomyDefinition,
        })
    ));
    const rawSelection = state.selection ?? {};
    assertRecord('selection', rawSelection);
    const selectionTargets = requireArray('selection.targets', rawSelection.targets ?? [])
        .map((target) => createProjectionTarget(target, anatomyDefinition));
    if (selectionTargets.some((target) => target.toothKey !== toothKey)) {
        throw new RangeError(`selection targets must belong to tooth ${toothKey}`);
    }
    const annotations = requireArray('annotations', state.annotations ?? [])
        .map((annotation, index) => createAnnotation(
            annotation,
            `tooth:${toothKey}:annotation:${index + 1}`,
            anatomyDefinition,
        ));
    if (annotations.some((annotation) => (
        annotation.target && annotation.target.toothKey !== toothKey
    ))) {
        throw new RangeError(`annotation targets must belong to tooth ${toothKey}`);
    }

    return Object.freeze({
        toothKey,
        lifecycle: requireString('lifecycle', state.lifecycle ?? 'PRESENT'),
        findings: Object.freeze(findings),
        procedures: Object.freeze(procedures),
        selection: Object.freeze({
            isSelected: optionalBoolean('selection.isSelected', rawSelection.isSelected),
            targets: Object.freeze(selectionTargets),
        }),
        disabled: optionalBoolean('disabled', state.disabled),
        annotations: Object.freeze(annotations),
    });
};

const defaultToothOrder = (dentition) => {
    if (dentition === PROJECTION_DENTITIONS.PERMANENT) return PERMANENT_TOOTH_KEYS;
    if (dentition === PROJECTION_DENTITIONS.PRIMARY) return PRIMARY_TOOTH_KEYS;
    return [];
};

const assertDentitionMatch = (toothKey, dentition, anatomyDefinition) => {
    if (dentition === PROJECTION_DENTITIONS.MIXED) return;
    if (anatomyDefinition[toothKey].dentition !== dentition) {
        throw new RangeError(`Tooth ${toothKey} does not belong to ${dentition} dentition`);
    }
};

/**
 * Frontend-only, serializable chart projection. This is an adapter DTO for the
 * odontogram demo and must not be promoted to the canonical backend schema.
 *
 * @typedef {object} ClinicalChartProjection
 * @property {1} schemaVersion
 * @property {string} projectionId
 * @property {'permanent'|'primary'|'mixed'} dentition
 * @property {ReadonlyArray<string>} toothOrder Explicit FDI layout order.
 * @property {Readonly<Record<string, ToothVisualState>>} teeth
 * @property {ProjectionTarget|null} selection
 */

/** @returns {Readonly<ClinicalChartProjection>} */
export const createClinicalChartProjection = ({
    projectionId,
    dentition = PROJECTION_DENTITIONS.PERMANENT,
    toothOrder,
    teeth = {},
    selection = null,
    anatomyDefinition = DENTAL_ANATOMY_REGISTRY,
}) => {
    assertRecord('anatomyDefinition', anatomyDefinition);
    assertRecord('teeth', teeth);
    assertEnumValue('dentition', dentition, Object.values(PROJECTION_DENTITIONS));
    if (dentition === PROJECTION_DENTITIONS.MIXED && toothOrder == null) {
        throw new TypeError('mixed dentition requires an explicit toothOrder');
    }

    const normalizedOrder = requireArray(
        'toothOrder',
        toothOrder ?? defaultToothOrder(dentition),
    ).map((toothKey) => normalizeToothKey(toothKey, anatomyDefinition));
    if (new Set(normalizedOrder).size !== normalizedOrder.length) {
        throw new RangeError('toothOrder must not contain duplicate tooth keys');
    }
    normalizedOrder.forEach((toothKey) => assertDentitionMatch(
        toothKey,
        dentition,
        anatomyDefinition,
    ));

    const unknownStateKey = Object.keys(teeth).find((toothKey) => !normalizedOrder.includes(toothKey));
    if (unknownStateKey) {
        throw new RangeError(`Tooth state ${unknownStateKey} is not present in toothOrder`);
    }

    const normalizedTeeth = Object.fromEntries(normalizedOrder.map((toothKey) => [
        toothKey,
        createToothVisualState({ ...teeth[toothKey], toothKey }, anatomyDefinition),
    ]));
    const normalizedSelection = selection
        ? createProjectionTarget(selection, anatomyDefinition)
        : null;
    if (normalizedSelection && !normalizedOrder.includes(normalizedSelection.toothKey)) {
        throw new RangeError(`Selected tooth ${normalizedSelection.toothKey} is not present in toothOrder`);
    }

    return Object.freeze({
        schemaVersion: CLINICAL_CHART_PROJECTION_VERSION,
        projectionId: requireString('projectionId', projectionId),
        dentition,
        toothOrder: Object.freeze([...normalizedOrder]),
        teeth: Object.freeze(normalizedTeeth),
        selection: normalizedSelection,
    });
};
