export const TOOTH_ARCH = Object.freeze({
    MAXILLARY: 'maxillary',
    MANDIBULAR: 'mandibular',
});

export const TOOTH_KIND = Object.freeze({
    INCISOR: 'incisor',
    CANINE: 'canine',
    PREMOLAR: 'premolar',
    MOLAR: 'molar',
});

export const PROCEDURE_TYPE = Object.freeze({
    CARIES: 'caries',
    COMPOSITE: 'composite',
    AMALGAM: 'amalgam',
    RCT: 'rct',
    CROWN: 'crown',
    IMPLANT: 'implant',
    MISSING: 'missing',
    BRIDGE: 'bridge',
    FRACTURE: 'fracture',
});

export const PROCEDURE_LIFECYCLE = Object.freeze({
    EXISTING: 'existing',
    PLANNED: 'planned',
    IN_PROGRESS: 'in_progress',
    COMPLETED: 'completed',
});

const ADULT_QUADRANTS = new Set([1, 2, 3, 4]);
const PRIMARY_QUADRANTS = new Set([5, 6, 7, 8]);
const VALID_LIFECYCLES = new Set(Object.values(PROCEDURE_LIFECYCLE));
const VALID_PROCEDURES = new Set(Object.values(PROCEDURE_TYPE));
const VALID_SURFACES = new Set(['M', 'D', 'O', 'I', 'B', 'L']);

function resolveKind(position, isPrimary) {
    if (position <= 2) return TOOTH_KIND.INCISOR;
    if (position === 3) return TOOTH_KIND.CANINE;
    if (!isPrimary && position <= 5) return TOOTH_KIND.PREMOLAR;
    return TOOTH_KIND.MOLAR;
}

export function parseFdiTooth(value) {
    const normalized = String(value ?? '').trim();
    if (!/^\d{2}$/.test(normalized)) {
        throw new Error(`Invalid FDI tooth number: ${value}`);
    }

    const fdi = Number(normalized);
    const quadrant = Math.trunc(fdi / 10);
    const position = fdi % 10;
    const isPrimary = PRIMARY_QUADRANTS.has(quadrant);
    const isAdult = ADULT_QUADRANTS.has(quadrant);
    const maxPosition = isPrimary ? 5 : 8;

    if ((!isAdult && !isPrimary) || position < 1 || position > maxPosition) {
        throw new Error(`Invalid FDI tooth number: ${value}`);
    }

    const arch = [1, 2, 5, 6].includes(quadrant)
        ? TOOTH_ARCH.MAXILLARY
        : TOOTH_ARCH.MANDIBULAR;
    const side = [1, 4, 5, 8].includes(quadrant) ? 'right' : 'left';
    const kind = resolveKind(position, isPrimary);

    return Object.freeze({
        fdi,
        quadrant,
        position,
        arch,
        side,
        kind,
        dentition: isPrimary ? 'primary' : 'permanent',
        occlusalSurface: kind === TOOTH_KIND.INCISOR || kind === TOOTH_KIND.CANINE ? 'I' : 'O',
        templateKey: `${arch}-${kind}`,
    });
}

export function normalizeSurface(surface, tooth) {
    const normalized = String(surface || '').trim().toUpperCase();
    if (!VALID_SURFACES.has(normalized)) return null;

    if (normalized === 'O' && tooth.occlusalSurface === 'I') return 'I';
    if (normalized === 'I' && tooth.occlusalSurface === 'O') return 'O';
    return normalized;
}

function normalizeProcedure(procedure, tooth) {
    const type = String(procedure?.type || '').trim().toLowerCase();
    if (!VALID_PROCEDURES.has(type)) return null;

    const lifecycle = VALID_LIFECYCLES.has(procedure.lifecycle)
        ? procedure.lifecycle
        : PROCEDURE_LIFECYCLE.COMPLETED;
    const surfaces = [...new Set((procedure.surfaces || [])
        .map((surface) => normalizeSurface(surface, tooth))
        .filter(Boolean))];

    return Object.freeze({
        type,
        lifecycle,
        surfaces,
        role: procedure.role || null,
    });
}

const LEGACY_CONDITION_MAP = Object.freeze({
    decayed: PROCEDURE_TYPE.CARIES,
    caries: PROCEDURE_TYPE.CARIES,
    filled: PROCEDURE_TYPE.COMPOSITE,
    filling: PROCEDURE_TYPE.COMPOSITE,
    restored: PROCEDURE_TYPE.COMPOSITE,
    rootcanal: PROCEDURE_TYPE.RCT,
    rct: PROCEDURE_TYPE.RCT,
    endo: PROCEDURE_TYPE.RCT,
    crown: PROCEDURE_TYPE.CROWN,
    crowned: PROCEDURE_TYPE.CROWN,
    missing: PROCEDURE_TYPE.MISSING,
    extracted: PROCEDURE_TYPE.MISSING,
});

export function normalizeLegacyToothStatus(status, fdi) {
    const tooth = parseFdiTooth(fdi);
    const condition = String(status?.condition || '').toLowerCase().replace(/[^a-z]/g, '');
    const type = LEGACY_CONDITION_MAP[condition];

    if (!type) return Object.freeze({ procedures: [] });

    const surfaceProcedure = [PROCEDURE_TYPE.CARIES, PROCEDURE_TYPE.COMPOSITE].includes(type);
    return Object.freeze({
        procedures: [Object.freeze({
            type,
            lifecycle: PROCEDURE_LIFECYCLE.EXISTING,
            surfaces: surfaceProcedure ? [tooth.occlusalSurface] : [],
            role: null,
        })],
    });
}

export function normalizeClinicalToothState(state, fdi) {
    const tooth = parseFdiTooth(fdi);
    const source = Array.isArray(state?.procedures)
        ? state.procedures
        : normalizeLegacyToothStatus(state, fdi).procedures;

    return Object.freeze({
        procedures: source
            .map((procedure) => normalizeProcedure(procedure, tooth))
            .filter(Boolean),
        bridgeRole: state?.bridgeRole || null,
    });
}
