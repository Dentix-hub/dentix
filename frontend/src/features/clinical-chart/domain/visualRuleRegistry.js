import {
    PROJECTION_TARGET_KINDS,
    PROJECTION_VISUAL_PHASES,
} from './clinicalChartProjection';
import {
    FINDING_CODES,
    PROCEDURE_CODES,
    TOOTH_LIFECYCLE_CODES,
} from './clinicalVisualCodes';

export { FINDING_CODES, PROCEDURE_CODES, TOOTH_LIFECYCLE_CODES } from './clinicalVisualCodes';

export const VISUAL_LAYER_ROLES = Object.freeze({
    BASE_ANATOMY: 'base-anatomy',
    LIFECYCLE: 'lifecycle',
    FINDINGS: 'findings',
    EXISTING_COMPLETED_WORK: 'existing-completed-work',
    PLANNED_ACTIVE_WORK: 'planned-active-work',
    SELECTION_FOCUS: 'selection-focus',
});

export const VISUAL_LAYER_SEQUENCE = Object.freeze([
    VISUAL_LAYER_ROLES.BASE_ANATOMY,
    VISUAL_LAYER_ROLES.LIFECYCLE,
    VISUAL_LAYER_ROLES.FINDINGS,
    VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK,
    VISUAL_LAYER_ROLES.PLANNED_ACTIVE_WORK,
    VISUAL_LAYER_ROLES.SELECTION_FOCUS,
]);

const freezeRule = ({ category, code, layerRole, effect, targetKinds, presentation }) => Object.freeze({
    category,
    code,
    layerRole,
    layerIndex: VISUAL_LAYER_SEQUENCE.indexOf(layerRole),
    effect,
    targetKinds: Object.freeze(targetKinds),
    presentation: Object.freeze(presentation),
});

const LIFECYCLE_RULES = Object.freeze({
    PRESENT: freezeRule({
        category: 'lifecycle',
        code: TOOTH_LIFECYCLE_CODES.PRESENT,
        layerRole: VISUAL_LAYER_ROLES.LIFECYCLE,
        effect: 'present',
        targetKinds: [PROJECTION_TARGET_KINDS.TOOTH],
        presentation: { baseOpacity: 1 },
    }),
    MISSING: freezeRule({
        category: 'lifecycle',
        code: TOOTH_LIFECYCLE_CODES.MISSING,
        layerRole: VISUAL_LAYER_ROLES.LIFECYCLE,
        effect: 'missing',
        targetKinds: [PROJECTION_TARGET_KINDS.TOOTH],
        presentation: {
            baseOpacity: 0.18,
            stroke: '#64748b',
            strokeWidth: 1.8,
            strokeDasharray: '3 2',
        },
    }),
    EXTRACTED: freezeRule({
        category: 'lifecycle',
        code: TOOTH_LIFECYCLE_CODES.EXTRACTED,
        layerRole: VISUAL_LAYER_ROLES.LIFECYCLE,
        effect: 'extracted',
        targetKinds: [PROJECTION_TARGET_KINDS.TOOTH],
        presentation: {
            baseOpacity: 0.14,
            stroke: '#475569',
            strokeWidth: 2.2,
        },
    }),
    IMPACTED: freezeRule({
        category: 'lifecycle',
        code: TOOTH_LIFECYCLE_CODES.IMPACTED,
        layerRole: VISUAL_LAYER_ROLES.LIFECYCLE,
        effect: 'impacted',
        targetKinds: [PROJECTION_TARGET_KINDS.TOOTH],
        presentation: {
            baseOpacity: 0.62,
            fill: '#eef2ff',
            fillOpacity: 0.35,
            stroke: '#6366f1',
            strokeWidth: 1.8,
            strokeDasharray: '4 2',
        },
    }),
    UNERUPTED: freezeRule({
        category: 'lifecycle',
        code: TOOTH_LIFECYCLE_CODES.UNERUPTED,
        layerRole: VISUAL_LAYER_ROLES.LIFECYCLE,
        effect: 'unerupted',
        targetKinds: [PROJECTION_TARGET_KINDS.TOOTH],
        presentation: {
            baseOpacity: 0.42,
            fill: '#f0f9ff',
            fillOpacity: 0.3,
            stroke: '#0284c7',
            strokeWidth: 1.6,
            strokeDasharray: '2 2',
        },
    }),
});

const FINDING_RULES = Object.freeze({
    CARIES: freezeRule({
        category: 'finding',
        code: FINDING_CODES.CARIES,
        layerRole: VISUAL_LAYER_ROLES.FINDINGS,
        effect: 'surface-caries',
        targetKinds: [PROJECTION_TARGET_KINDS.SURFACE, PROJECTION_TARGET_KINDS.TOOTH],
        presentation: {
            fill: '#b91c1c',
            fillOpacity: 0.86,
            stroke: '#7f1d1d',
            strokeWidth: 1.15,
        },
    }),
    FRACTURE: freezeRule({
        category: 'finding',
        code: FINDING_CODES.FRACTURE,
        layerRole: VISUAL_LAYER_ROLES.FINDINGS,
        effect: 'fracture-line',
        targetKinds: [PROJECTION_TARGET_KINDS.TOOTH, PROJECTION_TARGET_KINDS.SURFACE],
        presentation: {
            stroke: '#dc2626',
            strokeWidth: 2.2,
        },
    }),
    PAIN: freezeRule({
        category: 'finding',
        code: FINDING_CODES.PAIN,
        layerRole: VISUAL_LAYER_ROLES.FINDINGS,
        effect: 'pain-marker',
        targetKinds: [
            PROJECTION_TARGET_KINDS.TOOTH,
            PROJECTION_TARGET_KINDS.ROOT,
            PROJECTION_TARGET_KINDS.CANAL,
        ],
        presentation: {
            fill: '#f97316',
            stroke: '#c2410c',
            strokeWidth: 1.5,
        },
    }),
});

const PROCEDURE_RULES = Object.freeze({
    REST_COMPOSITE: freezeRule({
        category: 'procedure',
        code: PROCEDURE_CODES.REST_COMPOSITE,
        layerRole: VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK,
        effect: 'surface-restoration',
        targetKinds: [PROJECTION_TARGET_KINDS.SURFACE],
        presentation: {
            fill: '#2563eb',
            fillOpacity: 0.92,
            stroke: '#1d4ed8',
            strokeWidth: 1.2,
        },
    }),
    ENDO_RCT: freezeRule({
        category: 'procedure',
        code: PROCEDURE_CODES.ENDO_RCT,
        layerRole: VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK,
        effect: 'endodontic-therapy',
        targetKinds: [
            PROJECTION_TARGET_KINDS.TOOTH,
            PROJECTION_TARGET_KINDS.ROOT,
            PROJECTION_TARGET_KINDS.CANAL,
        ],
        presentation: {
            fill: '#ede9fe',
            fillOpacity: 0.72,
            stroke: '#7c3aed',
            strokeWidth: 2.1,
        },
    }),
    PROS_CROWN: freezeRule({
        category: 'procedure',
        code: PROCEDURE_CODES.PROS_CROWN,
        layerRole: VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK,
        effect: 'prosthetic-crown',
        targetKinds: [PROJECTION_TARGET_KINDS.TOOTH],
        presentation: {
            fill: '#fde68a',
            fillOpacity: 0.82,
            stroke: '#b7791f',
            strokeWidth: 2,
        },
    }),
    PROS_BRIDGE: freezeRule({
        category: 'procedure',
        code: PROCEDURE_CODES.PROS_BRIDGE,
        layerRole: VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK,
        effect: 'bridge-unit',
        targetKinds: [PROJECTION_TARGET_KINDS.TOOTH],
        presentation: {
            fill: '#fef3c7',
            fillOpacity: 0.8,
            stroke: '#a16207',
            strokeWidth: 2,
        },
    }),
    IMPLANT_FIXTURE: freezeRule({
        category: 'procedure',
        code: PROCEDURE_CODES.IMPLANT_FIXTURE,
        layerRole: VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK,
        effect: 'implant-fixture',
        targetKinds: [PROJECTION_TARGET_KINDS.TOOTH, PROJECTION_TARGET_KINDS.ROOT],
        presentation: {
            fill: '#ccfbf1',
            fillOpacity: 0.96,
            stroke: '#0f766e',
            strokeWidth: 1.7,
        },
    }),
    IMPLANT_CROWN: freezeRule({
        category: 'procedure',
        code: PROCEDURE_CODES.IMPLANT_CROWN,
        layerRole: VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK,
        effect: 'implant-crown',
        targetKinds: [PROJECTION_TARGET_KINDS.TOOTH],
        presentation: {
            fill: '#99f6e4',
            fillOpacity: 0.76,
            stroke: '#0f766e',
            strokeWidth: 2,
        },
    }),
    SURG_EXTRACTION: freezeRule({
        category: 'procedure',
        code: PROCEDURE_CODES.SURG_EXTRACTION,
        layerRole: VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK,
        effect: 'surgical-extraction',
        targetKinds: [PROJECTION_TARGET_KINDS.TOOTH],
        presentation: {
            stroke: '#dc2626',
            strokeWidth: 2.4,
        },
    }),
});

export const VISUAL_RULE_REGISTRY = Object.freeze({
    lifecycle: LIFECYCLE_RULES,
    finding: FINDING_RULES,
    procedure: PROCEDURE_RULES,
});

export const getVisualRule = (category, code) => (
    VISUAL_RULE_REGISTRY[category]?.[String(code).toUpperCase()] ?? null
);

const resolveProcedureLayer = (phase) => (
    [PROJECTION_VISUAL_PHASES.PLANNED, PROJECTION_VISUAL_PHASES.ACTIVE].includes(phase)
        ? VISUAL_LAYER_ROLES.PLANNED_ACTIVE_WORK
        : VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK
);

const resolvePresentation = (rule, phase) => {
    const isPlanned = phase === PROJECTION_VISUAL_PHASES.PLANNED;
    const isActive = phase === PROJECTION_VISUAL_PHASES.ACTIVE;
    const isCompletedExtraction = rule.code === PROCEDURE_CODES.SURG_EXTRACTION
        && phase === PROJECTION_VISUAL_PHASES.COMPLETED;

    return Object.freeze({
        ...rule.presentation,
        ...(isPlanned ? {
            fillOpacity: Math.min(rule.presentation.fillOpacity ?? 0.4, 0.38),
            strokeDasharray: '4 2',
        } : {}),
        ...(isActive ? {
            strokeDasharray: '2.5 1.5',
        } : {}),
        ...(isCompletedExtraction ? {
            stroke: '#64748b',
        } : {}),
    });
};

const createInstruction = ({ rule, sourceId, phase, target, order }) => {
    const layerRole = rule.category === 'procedure'
        ? resolveProcedureLayer(phase)
        : rule.layerRole;

    return Object.freeze({
        instructionId: `${sourceId}:${target.kind}:${target.surfaceCode ?? target.rootId ?? 'whole'}`,
        sourceId,
        category: rule.category,
        code: rule.code,
        phase,
        effect: rule.effect,
        target,
        layerRole,
        layerIndex: VISUAL_LAYER_SEQUENCE.indexOf(layerRole),
        order,
        presentation: resolvePresentation(rule, phase),
    });
};

const resolveEntryInstructions = (category, entries, startOrder) => entries.flatMap((entry, entryIndex) => {
    const rule = getVisualRule(category, entry.code);
    if (!rule) return [];
    return entry.targets
        .filter((target) => rule.targetKinds.includes(target.kind))
        .map((target, targetIndex) => createInstruction({
            rule,
            sourceId: entry.visualId,
            phase: entry.phase,
            target,
            order: startOrder + (entryIndex * 100) + targetIndex,
        }));
});

const createInteractionInstruction = (toothKey, effect, target, order) => Object.freeze({
    instructionId: `interaction:${toothKey}:${effect}:${order}`,
    sourceId: `interaction:${toothKey}`,
    category: 'interaction',
    code: effect.toUpperCase(),
    phase: null,
    effect,
    target,
    layerRole: VISUAL_LAYER_ROLES.SELECTION_FOCUS,
    layerIndex: VISUAL_LAYER_SEQUENCE.indexOf(VISUAL_LAYER_ROLES.SELECTION_FOCUS),
    order,
    presentation: Object.freeze(effect === 'disabled'
        ? { baseOpacity: 0.42, stroke: '#94a3b8' }
        : { fill: '#dbeafe', fillOpacity: 0.5, stroke: '#2563eb', strokeWidth: 1.5 }),
});

export const resolveToothVisualInstructions = (toothState) => {
    const normalizedState = {
        toothKey: String(toothState.toothKey),
        lifecycle: toothState.lifecycle ?? TOOTH_LIFECYCLE_CODES.PRESENT,
        findings: toothState.findings ?? [],
        procedures: toothState.procedures ?? [],
        selection: toothState.selection ?? { isSelected: false, targets: [] },
        disabled: toothState.disabled ?? false,
    };
    const instructions = [];
    const lifecycleRule = getVisualRule('lifecycle', normalizedState.lifecycle);

    if (lifecycleRule) {
        instructions.push(createInstruction({
            rule: lifecycleRule,
            sourceId: `lifecycle:${normalizedState.toothKey}`,
            phase: null,
            target: Object.freeze({ kind: PROJECTION_TARGET_KINDS.TOOTH, toothKey: normalizedState.toothKey }),
            order: 0,
        }));
    }

    instructions.push(...resolveEntryInstructions('finding', normalizedState.findings, 1000));
    instructions.push(...resolveEntryInstructions('procedure', normalizedState.procedures, 2000));

    if (normalizedState.selection.isSelected) {
        const targets = normalizedState.selection.targets.length > 0
            ? normalizedState.selection.targets
            : [{ kind: PROJECTION_TARGET_KINDS.TOOTH, toothKey: normalizedState.toothKey }];
        targets.forEach((target, index) => instructions.push(createInteractionInstruction(
            normalizedState.toothKey,
            'selected',
            target,
            3000 + index,
        )));
    }
    if (normalizedState.disabled) {
        instructions.push(createInteractionInstruction(
            normalizedState.toothKey,
            'disabled',
            Object.freeze({ kind: PROJECTION_TARGET_KINDS.TOOTH, toothKey: normalizedState.toothKey }),
            4000,
        ));
    }

    const sortedInstructions = instructions.sort((left, right) => (
        (left.layerIndex - right.layerIndex) || (left.order - right.order)
    ));
    const byLayer = Object.fromEntries(VISUAL_LAYER_SEQUENCE.map((layerRole) => [
        layerRole,
        Object.freeze(sortedInstructions.filter((instruction) => instruction.layerRole === layerRole)),
    ]));

    return Object.freeze({
        toothKey: normalizedState.toothKey,
        instructions: Object.freeze(sortedInstructions),
        byLayer: Object.freeze(byLayer),
    });
};

export const resolveClinicalChartVisuals = (projection) => Object.freeze(
    Object.fromEntries(Object.entries(projection.teeth ?? {}).map(([toothKey, toothState]) => [
        toothKey,
        resolveToothVisualInstructions({ toothKey, ...toothState }),
    ])),
);
