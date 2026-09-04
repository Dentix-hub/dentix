import { PROCEDURE_LIFECYCLE, PROCEDURE_TYPE } from './toothTypes';

export const PROCEDURE_VISUALS = Object.freeze({
    [PROCEDURE_TYPE.CARIES]: Object.freeze({
        label: 'Caries',
        color: '#9f2637',
        darkColor: '#651524',
        highlight: '#d95b6a',
    }),
    [PROCEDURE_TYPE.COMPOSITE]: Object.freeze({
        label: 'Composite restoration',
        color: '#2f6fa8',
        darkColor: '#1f4f7a',
        highlight: '#9dc8ea',
    }),
    [PROCEDURE_TYPE.AMALGAM]: Object.freeze({
        label: 'Amalgam restoration',
        color: '#73808d',
        darkColor: '#3f4b57',
        highlight: '#d5dbe0',
    }),
    [PROCEDURE_TYPE.RCT]: Object.freeze({
        label: 'Root canal treatment',
        color: '#6e4aa3',
        darkColor: '#4b2e78',
        highlight: '#c6afe9',
    }),
    [PROCEDURE_TYPE.CROWN]: Object.freeze({
        label: 'Crown',
        color: '#b8822e',
        darkColor: '#76501b',
        highlight: '#f4dea0',
    }),
    [PROCEDURE_TYPE.IMPLANT]: Object.freeze({
        label: 'Implant crown',
        color: '#2f7f7a',
        darkColor: '#1e5754',
        highlight: '#9ad0ca',
    }),
    [PROCEDURE_TYPE.BRIDGE]: Object.freeze({
        label: 'Bridge',
        color: '#a7683c',
        darkColor: '#6f4024',
        highlight: '#e6c09d',
    }),
    [PROCEDURE_TYPE.MISSING]: Object.freeze({
        label: 'Missing tooth',
        color: '#667585',
        darkColor: '#3e4a56',
        highlight: '#cbd2d9',
    }),
});

export const PROCEDURE_LAYER_ORDER = Object.freeze([
    PROCEDURE_TYPE.IMPLANT,
    PROCEDURE_TYPE.RCT,
    PROCEDURE_TYPE.CARIES,
    PROCEDURE_TYPE.COMPOSITE,
    PROCEDURE_TYPE.AMALGAM,
    PROCEDURE_TYPE.CROWN,
    PROCEDURE_TYPE.BRIDGE,
    PROCEDURE_TYPE.MISSING,
]);

export function getLifecycleVisual(lifecycle) {
    switch (lifecycle) {
        case PROCEDURE_LIFECYCLE.PLANNED:
            return Object.freeze({ opacity: 0.46, strokeDasharray: '5 3', strokeWidth: 1.8 });
        case PROCEDURE_LIFECYCLE.IN_PROGRESS:
            return Object.freeze({ opacity: 0.78, strokeDasharray: '8 2', strokeWidth: 2 });
        case PROCEDURE_LIFECYCLE.EXISTING:
            return Object.freeze({ opacity: 0.9, strokeDasharray: undefined, strokeWidth: 1.6 });
        default:
            return Object.freeze({ opacity: 1, strokeDasharray: undefined, strokeWidth: 1.6 });
    }
}

export function getProcedure(state, type) {
    return state.procedures.find((procedure) => procedure.type === type) || null;
}

export function getSurfaceProcedures(state) {
    return state.procedures.filter((procedure) => [
        PROCEDURE_TYPE.CARIES,
        PROCEDURE_TYPE.COMPOSITE,
        PROCEDURE_TYPE.AMALGAM,
    ].includes(procedure.type));
}

export function describeClinicalState(state) {
    if (!state.procedures.length) return 'Healthy';

    return state.procedures
        .map((procedure) => {
            const visual = PROCEDURE_VISUALS[procedure.type];
            const surfaces = procedure.surfaces.length ? ` ${procedure.surfaces.join('')}` : '';
            const lifecycle = procedure.lifecycle === PROCEDURE_LIFECYCLE.PLANNED ? ' planned' : '';
            return `${visual?.label || procedure.type}${surfaces}${lifecycle}`;
        })
        .join(', ');
}

