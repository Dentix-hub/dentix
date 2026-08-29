import {
    DENTAL_ANATOMY_REGISTRY,
    DENTITIONS,
} from '../domain/dentalAnatomyRegistry';
import { toothToNumber } from '@/utils/toothUtils';

export const CHART_NOTATION_MODES = Object.freeze({
    PALMER: 'palmer',
    FDI: 'fdi',
    UNIVERSAL: 'universal',
});

export const CHART_INTERACTION_MODES = Object.freeze({
    READ_ONLY: 'read-only',
    EDIT: 'edit',
});

export const CHART_INTENT_TYPES = Object.freeze({
    TOOTH_SELECTED: 'chart/tooth-selected',
    SURFACE_SELECTED: 'chart/surface-selected',
    ROOT_SELECTED: 'chart/root-selected',
    MULTI_SELECT_CHANGED: 'chart/multi-select-changed',
});

const CALLBACK_BY_INTENT = Object.freeze({
    [CHART_INTENT_TYPES.TOOTH_SELECTED]: 'onToothSelected',
    [CHART_INTENT_TYPES.SURFACE_SELECTED]: 'onSurfaceSelected',
    [CHART_INTENT_TYPES.ROOT_SELECTED]: 'onRootSelected',
    [CHART_INTENT_TYPES.MULTI_SELECT_CHANGED]: 'onMultiSelectChanged',
});

const DEFAULT_VISUAL_STATE = Object.freeze({
    teeth: Object.freeze({}),
    selection: null,
});

const DEFAULT_LAYERS = Object.freeze({
    roots: false,
    surfaces: false,
});

const DEFAULT_CALLBACKS = Object.freeze({});

const assertEnumValue = (name, value, values) => {
    if (!values.includes(value)) {
        throw new TypeError(`${name} must be one of: ${values.join(', ')}`);
    }
};

const assertRecord = (name, value) => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        throw new TypeError(`${name} must be an object`);
    }
};

/**
 * Stable renderer input boundary. The renderer consumes projection-ready visual
 * data only; it never receives repositories, API clients, domain services, or
 * persistence functions.
 *
 * @typedef {object} ClinicalChartRendererInput
 * @property {string} chartId Unique identity for this chart instance.
 * @property {Readonly<Record<string, import('../domain/dentalAnatomyRegistry').DentalAnatomyRecord>>} anatomyDefinition
 * @property {'permanent'|'primary'} dentition
 * @property {{teeth: Readonly<Record<string, object>>, selection: null|object}} visualState
 * @property {'palmer'|'fdi'|'universal'} notationMode
 * @property {'read-only'|'edit'} interactionMode
 * @property {{roots: boolean, surfaces: boolean}} layers
 * @property {{
 *   onIntent?: function,
 *   onToothSelected?: function,
 *   onSurfaceSelected?: function,
 *   onRootSelected?: function,
 *   onMultiSelectChanged?: function
 * }} callbacks
 */

/**
 * Normalizes and validates the public renderer input contract.
 *
 * @param {Partial<ClinicalChartRendererInput> & {chartId: string}} config
 * @returns {Readonly<ClinicalChartRendererInput>}
 */
export const createClinicalChartRendererInput = ({
    chartId,
    anatomyDefinition = DENTAL_ANATOMY_REGISTRY,
    dentition = DENTITIONS.PERMANENT,
    visualState = DEFAULT_VISUAL_STATE,
    notationMode = CHART_NOTATION_MODES.PALMER,
    interactionMode = CHART_INTERACTION_MODES.READ_ONLY,
    layers = DEFAULT_LAYERS,
    callbacks = DEFAULT_CALLBACKS,
}) => {
    if (typeof chartId !== 'string' || chartId.trim() === '') {
        throw new TypeError('chartId must be a non-empty string');
    }
    assertRecord('anatomyDefinition', anatomyDefinition);
    assertRecord('visualState', visualState);
    assertRecord('visualState.teeth', visualState.teeth ?? DEFAULT_VISUAL_STATE.teeth);
    assertRecord('layers', layers);
    assertRecord('callbacks', callbacks);
    assertEnumValue('dentition', dentition, Object.values(DENTITIONS));
    assertEnumValue('notationMode', notationMode, Object.values(CHART_NOTATION_MODES));
    assertEnumValue('interactionMode', interactionMode, Object.values(CHART_INTERACTION_MODES));

    return Object.freeze({
        chartId: chartId.trim(),
        anatomyDefinition,
        dentition,
        visualState: Object.freeze({
            teeth: visualState.teeth ?? DEFAULT_VISUAL_STATE.teeth,
            selection: visualState.selection ?? null,
        }),
        notationMode,
        interactionMode,
        layers: Object.freeze({
            roots: Boolean(layers.roots),
            surfaces: Boolean(layers.surfaces),
        }),
        callbacks,
    });
};

const createTarget = (kind, toothKey, details = {}) => Object.freeze({
    kind,
    toothKey: String(toothKey),
    ...details,
});

const createIntent = (type, chartId, payload) => Object.freeze({
    type,
    chartId,
    ...payload,
});

const assertKnownTooth = (anatomyDefinition, toothKey) => {
    const normalizedKey = String(toothKey);
    if (!anatomyDefinition[normalizedKey]) {
        throw new RangeError(`Unknown tooth key: ${normalizedKey}`);
    }
    return normalizedKey;
};

/**
 * Adapts the renderer contract to the current Dentix odontogram component and
 * exposes persistence-neutral interaction intent creators.
 *
 * @param {ClinicalChartRendererInput} input
 */
export const createClinicalChartRendererAdapter = (input) => {
    const normalizedInput = createClinicalChartRendererInput(input);
    const isReadOnly = normalizedInput.interactionMode === CHART_INTERACTION_MODES.READ_ONLY;

    const dispatch = (intent) => {
        normalizedInput.callbacks.onIntent?.(intent);
        normalizedInput.callbacks[CALLBACK_BY_INTENT[intent.type]]?.(intent);
        return intent;
    };

    const toothSelected = (toothNumber) => {
        const toothKey = assertKnownTooth(normalizedInput.anatomyDefinition, toothToNumber(toothNumber));
        return dispatch(createIntent(CHART_INTENT_TYPES.TOOTH_SELECTED, normalizedInput.chartId, {
            target: createTarget('tooth', toothKey),
        }));
    };

    const surfaceSelected = ({ toothKey, surfaceCode }) => {
        const knownToothKey = assertKnownTooth(normalizedInput.anatomyDefinition, toothKey);
        return dispatch(createIntent(CHART_INTENT_TYPES.SURFACE_SELECTED, normalizedInput.chartId, {
            target: createTarget('surface', knownToothKey, { surfaceCode }),
        }));
    };

    const rootSelected = ({ toothKey, rootId }) => {
        const knownToothKey = assertKnownTooth(normalizedInput.anatomyDefinition, toothKey);
        return dispatch(createIntent(CHART_INTENT_TYPES.ROOT_SELECTED, normalizedInput.chartId, {
            target: createTarget('root', knownToothKey, { rootId }),
        }));
    };

    const multiSelectChanged = (targets) => dispatch(createIntent(
        CHART_INTENT_TYPES.MULTI_SELECT_CHANGED,
        normalizedInput.chartId,
        { targets: Object.freeze([...targets]) },
    ));

    const selectedSurface = normalizedInput.visualState.selection?.kind === 'surface'
        ? normalizedInput.visualState.selection
        : null;

    return Object.freeze({
        input: normalizedInput,
        chartProps: Object.freeze({
            teethStatus: normalizedInput.visualState.teeth,
            onToothClick: isReadOnly ? undefined : toothSelected,
            isPediatric: normalizedInput.dentition === DENTITIONS.PRIMARY,
            showRoots: normalizedInput.layers.roots,
            enableSurfaceSelection: !isReadOnly && normalizedInput.layers.surfaces,
            selectedSurface,
            onSurfaceClick: isReadOnly ? undefined : surfaceSelected,
            readOnly: isReadOnly,
            notationMode: normalizedInput.notationMode,
        }),
        intents: Object.freeze({
            toothSelected,
            surfaceSelected,
            rootSelected,
            multiSelectChanged,
        }),
    });
};
