import {
    createClinicalChartProjection,
    PROJECTION_DENTITIONS,
    PROJECTION_TARGET_KINDS,
    PROJECTION_VISUAL_PHASES,
} from '../domain/clinicalChartProjection';
import {
    FINDING_CODES,
    PROCEDURE_CODES,
    TOOTH_LIFECYCLE_CODES,
} from '../domain/clinicalVisualCodes';
import {
    DENTAL_ANATOMY_REGISTRY,
    PERMANENT_TOOTH_KEYS,
    PRIMARY_TOOTH_KEYS,
} from '../domain/dentalAnatomyRegistry';
import { DEFAULT_CHART_NOTATION_MODE } from '../domain/chartNotation';
import {
    CHART_INTERACTION_MODES,
    createClinicalChartRendererInput,
} from '../rendering/ClinicalChartRendererAdapter';

const ALLOWED_FINDINGS = new Set(Object.values(FINDING_CODES));
const ALLOWED_PROCEDURES = new Set(Object.values(PROCEDURE_CODES));
const ALLOWED_LIFECYCLES = new Set(Object.values(TOOTH_LIFECYCLE_CODES));

/**
 * Maps a single visual target safely to the renderer contract.
 */
const mapTarget = (target, defaultToothKey) => {
    const kind = Object.values(PROJECTION_TARGET_KINDS).includes(target?.kind)
        ? target.kind
        : PROJECTION_TARGET_KINDS.TOOTH;
    const toothKey = String(target?.tooth_key || target?.toothKey || defaultToothKey);

    const base = { kind, toothKey };
    if (kind === PROJECTION_TARGET_KINDS.SURFACE && (target?.surface_code || target?.surfaceCode)) {
        base.surfaceCode = String(target.surface_code || target.surfaceCode).toUpperCase();
    }
    if ((kind === PROJECTION_TARGET_KINDS.ROOT || kind === PROJECTION_TARGET_KINDS.CANAL) && (target?.root_id || target?.rootId)) {
        base.rootId = String(target.root_id || target.rootId);
    }
    if (kind === PROJECTION_TARGET_KINDS.CANAL && (target?.canal_id || target?.canalId)) {
        base.canalId = String(target.canal_id || target.canalId);
    }
    return base;
};

/**
 * Maps visual entries (findings or procedures) from the backend snapshot to renderer schema v1.
 * Filters out unsupported clinical codes (e.g. PROS_DENTURE) from visual rendering
 * so the renderer remains stable and unpolluted. Unsupported codes stay in warnings.
 */
const mapVisualEntries = (entries, allowedCodes, defaultPhase, toothKey) => {
    if (!Array.isArray(entries)) return [];
    const valid = [];

    entries.forEach((entry, idx) => {
        const code = String(entry.code || '').toUpperCase();
        if (!allowedCodes.has(code)) return;

        const phase = Object.values(PROJECTION_VISUAL_PHASES).includes(entry.phase)
            ? entry.phase
            : defaultPhase;

        const rawTargets = Array.isArray(entry.targets) && entry.targets.length > 0
            ? entry.targets
            : [{ kind: 'tooth', tooth_key: toothKey }];

        const targets = rawTargets
            .filter((t) => String(t.tooth_key || t.toothKey || toothKey) === toothKey)
            .map((t) => mapTarget(t, toothKey));

        if (targets.length === 0) return;

        valid.push({
            visualId: String(entry.visual_id || entry.visualId || `${toothKey}-${code}-${idx}`),
            code,
            phase,
            targets,
            annotations: [],
        });
    });

    return valid;
};

/**
 * Thin frontend adapter translating the backend Clinical Workspace Snapshot
 * into renderer schema version 1 and DentalChartSVG-compatible state.
 *
 * @param {object} snapshot Backend ClinicalWorkspaceSnapshot payload
 * @param {object} options Configuration options
 * @returns {object} Adapter output
 */
export const adaptWorkspaceSnapshotToRenderer = (snapshot, options = {}) => {
    const {
        chartId = 'clinical-chart',
        isPediatric = false,
        notationMode = DEFAULT_CHART_NOTATION_MODE,
        showRoots = true,
        selection = null,
        onToothClick,
        onSurfaceClick,
    } = options;

    const rawTeeth = snapshot?.teeth || {};
    const hasPrimaryData = PRIMARY_TOOTH_KEYS.some((k) => (
        rawTeeth[k] && (
            (rawTeeth[k].findings && rawTeeth[k].findings.length > 0)
            || (rawTeeth[k].procedures && rawTeeth[k].procedures.length > 0)
            || (rawTeeth[k].lifecycle && rawTeeth[k].lifecycle !== 'PRESENT')
        )
    ));
    const hasPermanentData = PERMANENT_TOOTH_KEYS.some((k) => (
        rawTeeth[k] && (
            (rawTeeth[k].findings && rawTeeth[k].findings.length > 0)
            || (rawTeeth[k].procedures && rawTeeth[k].procedures.length > 0)
            || (rawTeeth[k].lifecycle && rawTeeth[k].lifecycle !== 'PRESENT')
        )
    ));

    let dentition = PROJECTION_DENTITIONS.PERMANENT;
    if (isPediatric) {
        dentition = PROJECTION_DENTITIONS.PRIMARY;
    } else if (hasPrimaryData && hasPermanentData) {
        dentition = PROJECTION_DENTITIONS.MIXED;
    }

    const toothOrder = dentition === PROJECTION_DENTITIONS.PRIMARY
        ? [...PRIMARY_TOOTH_KEYS]
        : (dentition === PROJECTION_DENTITIONS.MIXED
            ? [...PERMANENT_TOOTH_KEYS, ...PRIMARY_TOOTH_KEYS]
            : [...PERMANENT_TOOTH_KEYS]);

    const teeth = {};
    const legacyTeethStatus = {};

    toothOrder.forEach((toothKey) => {
        const raw = rawTeeth[toothKey] || {};
        const rawLifecycle = String(raw.lifecycle || 'PRESENT').toUpperCase();
        const lifecycle = ALLOWED_LIFECYCLES.has(rawLifecycle)
            ? rawLifecycle
            : TOOTH_LIFECYCLE_CODES.PRESENT;

        const findings = mapVisualEntries(
            raw.findings,
            ALLOWED_FINDINGS,
            PROJECTION_VISUAL_PHASES.EXISTING,
            toothKey,
        );

        const procedures = mapVisualEntries(
            raw.procedures,
            ALLOWED_PROCEDURES,
            PROJECTION_VISUAL_PHASES.COMPLETED,
            toothKey,
        );

        const isSelected = selection?.toothKey === toothKey;
        const selectionTargets = isSelected && selection?.kind && selection.kind !== 'tooth'
            ? [mapTarget(selection, toothKey)]
            : [];

        teeth[toothKey] = {
            toothKey,
            lifecycle,
            findings,
            procedures,
            selection: {
                isSelected,
                targets: selectionTargets,
            },
            disabled: false,
            annotations: [],
        };

        let toothCondition = raw.condition || null;
        if (!toothCondition && lifecycle && lifecycle !== 'PRESENT') {
            toothCondition = lifecycle === 'MISSING' ? 'Missing' : lifecycle;
        }

        legacyTeethStatus[toothKey] = {
            tooth_number: parseInt(toothKey, 10) || toothKey,
            condition: toothCondition,
            notes: raw.notes || '',
        };
    });

    const projection = createClinicalChartProjection({
        projectionId: String(snapshot?.projection_id || `projection-${chartId}`),
        dentition,
        toothOrder: dentition === PROJECTION_DENTITIONS.MIXED ? toothOrder : undefined,
        teeth,
        selection: selection ? mapTarget(selection, selection.toothKey) : null,
        anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
    });

    const isReadOnly = Boolean(options.readOnly);

    const rendererInput = createClinicalChartRendererInput({
        chartId,
        anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
        dentition,
        visualState: {
            ...projection,
            teeth: projection.teeth,
            selection: projection.selection,
        },
        notationMode,
        interactionMode: isReadOnly ? CHART_INTERACTION_MODES.READ_ONLY : CHART_INTERACTION_MODES.EDIT,
        layers: {
            roots: Boolean(showRoots),
            surfaces: false,
        },
        callbacks: {
            onIntent: options.onIntent,
            onToothSelected: (intent) => {
                onToothClick?.(intent.target?.toothKey, 'fdi');
            },
            onSurfaceSelected: (intent) => {
                onSurfaceClick?.(intent.target);
            },
        },
    });

    const coverage = snapshot?.coverage || {
        teeth: 'UNCOVERED',
        treatments: 'UNCOVERED',
        sessions: 'UNCOVERED',
    };
    const readMode = snapshot?.read_mode || 'LEGACY_ONLY';
    const warnings = snapshot?.warnings || [];

    const hasFallbackWarning = warnings.some((w) => w.code === 'FALLBACK_DATA_ACTIVE');
    const isFallback = hasFallbackWarning
        || Object.values(coverage).some((s) => s === 'UNCOVERED' || s === 'PARTIAL');
    const isPartial = Object.values(coverage).some((s) => s === 'PARTIAL');

    const totalWorkItems = Array.isArray(snapshot?.work_items) ? snapshot.work_items.length : 0;
    const hasAnyToothFindings = Object.values(teeth).some((t) => t.findings.length > 0 || t.procedures.length > 0 || t.lifecycle !== 'PRESENT');
    const isEmpty = !snapshot || (!hasAnyToothFindings && totalWorkItems === 0);

    return Object.freeze({
        rendererInput,
        projection,
        teethStatus: legacyTeethStatus,
        coverage,
        readMode,
        warnings,
        isFallback,
        isPartial,
        isEmpty,
        dentition,
    });
};
