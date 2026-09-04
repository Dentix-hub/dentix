import { PROCEDURE_TYPE } from './toothTypes';

const PROGRAMMATIC_TYPES = new Set([
    PROCEDURE_TYPE.CARIES,
    PROCEDURE_TYPE.COMPOSITE,
    PROCEDURE_TYPE.AMALGAM,
    PROCEDURE_TYPE.RCT,
    PROCEDURE_TYPE.CROWN,
    PROCEDURE_TYPE.IMPLANT,
    PROCEDURE_TYPE.MISSING,
    PROCEDURE_TYPE.FRACTURE,
]);

export function hasProgrammaticToothEffect({ fdi, type, surfaces = [] }) {
    if (Number(fdi) !== 46 || !PROGRAMMATIC_TYPES.has(type)) return false;
    if ([PROCEDURE_TYPE.CARIES, PROCEDURE_TYPE.COMPOSITE, PROCEDURE_TYPE.AMALGAM].includes(type)) {
        return surfaces.length === 1 && surfaces[0] === 'O';
    }
    return true;
}
