/**
 * Canonical clinical catalog definitions mirroring backend/clinical/catalog.py
 * Closes G8-M08 (Favorites), G8-M09 (Recents), G8-M10 (Search), G8-M11 (Smart Defaults)
 */

export const CANONICAL_PROCEDURES = [
    {
        code: 'REST_COMPOSITE',
        name: 'Composite Restoration',
        nameAr: 'حشوة كمبوزيت',
        category: 'restorative',
        kind: 'procedure',
        allowed_target_kinds: ['surface'],
        description: 'Direct composite resin restoration placed on specific tooth surfaces.',
    },
    {
        code: 'ENDO_RCT',
        name: 'Root Canal Treatment',
        nameAr: 'علاج جذور',
        category: 'endodontic',
        kind: 'procedure',
        allowed_target_kinds: ['tooth', 'root', 'canal'],
        description: 'Complete root canal treatment encompassing tooth, root, and canal anatomical targets.',
    },
    {
        code: 'PROS_CROWN',
        name: 'Crown Restoration',
        nameAr: 'تركيب تاج / طربوش',
        category: 'prosthodontic',
        kind: 'procedure',
        allowed_target_kinds: ['tooth'],
        requires_lab: true,
        description: 'Fixed single extra-coronal crown restoration targeting an individual tooth.',
    },
    {
        code: 'PROS_BRIDGE',
        name: 'Fixed Bridge',
        nameAr: 'جسر ثابت',
        category: 'prosthodontic',
        kind: 'procedure',
        allowed_target_kinds: ['tooth'],
        requires_lab: true,
        description: 'Fixed multi-unit partial denture (bridge) spanning multiple tooth targets.',
    },
    {
        code: 'IMPLANT_FIXTURE',
        name: 'Implant Fixture',
        nameAr: 'غرسة زراعة',
        category: 'implantology',
        kind: 'procedure',
        allowed_target_kinds: ['tooth', 'root'],
        description: 'Endosseous dental implant fixture placed in tooth/root anatomical site.',
    },
    {
        code: 'IMPLANT_CROWN',
        name: 'Implant Crown',
        nameAr: 'تاج فوق الزرعة',
        category: 'implantology',
        kind: 'procedure',
        allowed_target_kinds: ['tooth'],
        requires_lab: true,
        description: 'Implant-supported prosthetic crown restoration targeting tooth position.',
    },
    {
        code: 'SURG_EXTRACTION',
        name: 'Surgical Extraction',
        nameAr: 'خلع جراحي / بسيط',
        category: 'oral-surgery',
        kind: 'procedure',
        allowed_target_kinds: ['tooth'],
        description: 'Surgical or non-surgical exodontia of a specific tooth.',
    },
    {
        code: 'PROS_DENTURE',
        name: 'Removable Denture',
        nameAr: 'طقم أسنان متحرك',
        category: 'prosthodontic',
        kind: 'procedure',
        allowed_target_kinds: ['tooth'],
        requires_lab: true,
        description: 'Removable partial or complete denture spanning multiple teeth.',
    },
];

export const CANONICAL_PROCEDURES_BY_CODE = new Map(
    CANONICAL_PROCEDURES.map((p) => [p.code, p])
);

export const CANONICAL_FINDINGS = [
    {
        code: 'CARIES',
        name: 'Dental Caries',
        nameAr: 'تسوس أسنان',
        category: 'finding',
        kind: 'finding',
        allowed_target_kinds: ['tooth', 'surface'],
        description: 'Dental caries lesion localized to a tooth or specific surface(s).',
    },
    {
        code: 'FRACTURE',
        name: 'Tooth Fracture',
        nameAr: 'كسر بالسن',
        category: 'finding',
        kind: 'finding',
        allowed_target_kinds: ['tooth', 'surface'],
        description: 'Structural fracture involving crown tooth structure or specific surfaces.',
    },
    {
        code: 'PAIN',
        name: 'Dental Pain / Odontalgia',
        nameAr: 'ألم بالسن',
        category: 'finding',
        kind: 'finding',
        allowed_target_kinds: ['tooth', 'root', 'canal'],
        description: 'Symptomatic dental pain or sensitivity localized to tooth, root, or canal.',
    },
];

export const ALL_CANONICAL_ACTIONS = [...CANONICAL_PROCEDURES, ...CANONICAL_FINDINGS];

export const DEFAULT_FAVORITE_CODES = [
    'CARIES',
    'FRACTURE',
    'PAIN',
];

/**
 * Check if an FDI tooth key represents an anterior tooth (positions 1, 2, 3)
 */
export function isAnteriorTooth(toothKey) {
    if (!toothKey) return false;
    const str = String(toothKey).trim();
    const toothNum = parseInt(str.slice(-1), 10);
    return [1, 2, 3].includes(toothNum);
}

/**
 * Check if an FDI tooth key represents a posterior tooth (positions 4, 5, 6, 7, 8)
 */
export function isPosteriorTooth(toothKey) {
    if (!toothKey) return false;
    const str = String(toothKey).trim();
    const toothNum = parseInt(str.slice(-1), 10);
    return [4, 5, 6, 7, 8].includes(toothNum);
}

/**
 * Derive smart target kind and surfaces from catalog definition (allowed_target_kinds)
 * Decision D5 / PD03 (G8-M11)
 *
 * Rules:
 * 1. If allowed_target_kinds contains 'tooth' and NOT 'surface':
 *    target_kind defaults to 'tooth' (no surface required; applies in 1 click).
 * 2. If 'surface' in allowed_target_kinds (e.g. REST_COMPOSITE, CARIES, FRACTURE):
 *    - If user already clicked surfaces on tooth (S08), reuse those surfaces (target_kind='surface').
 *    - If no surface was clicked yet, defaults to 'O' on posterior teeth (4-8) and 'I' on anterior teeth (1-3).
 */
export function getSmartTargetKindAndSurfaces(definition, toothKey, existingSurfaces = []) {
    const allowed = definition?.allowed_target_kinds || ['tooth'];
    const hasSurface = allowed.includes('surface');
    const hasTooth = allowed.includes('tooth');

    // Case 1: Allows tooth and NOT surface -> whole-tooth
    if (hasTooth && !hasSurface) {
        return {
            targetKind: 'tooth',
            surfaces: [],
            defaultSurface: null,
            requiresSurfacePrompt: false,
        };
    }

    // Case 2: Surface-capable (REST_COMPOSITE, CARIES, FRACTURE)
    if (hasSurface) {
        if (Array.isArray(existingSurfaces) && existingSurfaces.length > 0) {
            return {
                targetKind: 'surface',
                surfaces: [...existingSurfaces],
                defaultSurface: null,
                requiresSurfacePrompt: false,
            };
        }

        // No surfaces selected yet -> determine smart default based on tooth position
        const defaultSurface = isAnteriorTooth(toothKey) ? 'I' : 'O';
        return {
            targetKind: 'surface',
            surfaces: [defaultSurface],
            defaultSurface,
            requiresSurfacePrompt: true,
        };
    }

    // Fallback
    return {
        targetKind: 'tooth',
        surfaces: [],
        defaultSurface: null,
        requiresSurfacePrompt: false,
    };
}

/**
 * G12-M04: Lab Required Procedure Codes
 */
export const LAB_REQUIRED_PROCEDURE_CODES = [
    'PROS_CROWN',
    'PROS_BRIDGE',
    'IMPLANT_CROWN',
    'PROS_DENTURE',
];

/**
 * Check whether a procedure code requires dental laboratory fabrication (G12-M04).
 */
export function isLabRequiredProcedure(procedureCode) {
    if (!procedureCode) return false;
    const clean = String(procedureCode).trim().toUpperCase();
    return LAB_REQUIRED_PROCEDURE_CODES.includes(clean);
}

/**
 * G12-M05: Lab-Ready Step Codes
 */
export const LAB_READY_STEP_CODES = [
    'preparation',
    'abutment_preparation',
    'impression_scan',
    'impression',
    'jaw_relation',
    'try_in',
    'lab',
];

/**
 * Check whether a workflow step code signals laboratory handoff readiness (G12-M05).
 */
export function isLabReadyStep(stepCode) {
    if (!stepCode) return false;
    const clean = String(stepCode).trim().toLowerCase();
    return LAB_READY_STEP_CODES.includes(clean);
}

/**
 * Standardize raw LabOrder.status into work item lab status per Decision D4 (G12-M10).
 * - 'completed' -> 'lab_ready'
 * - all other strings or falsy -> 'unmapped' (neutral)
 */
export function mapLabOrderStatus(status) {
    if (!status) return 'unmapped';
    const clean = String(status).trim().toLowerCase();
    if (clean === 'completed') return 'lab_ready';
    return 'unmapped';
}


