import { palmerToFdi } from '@/utils/toothUtils';

/**
 * Shared treatment payload builder extracted mechanically from `TreatmentModal.handleSave` (U4D #1).
 * Used identically by both `TreatmentModal` and `QuickTreatmentSheet` so that quick chairside saves
 * produce the exact same POST/PUT body as the full modal.
 *
 * @param {Object} treatment - Current treatment state object
 * @param {Object} [context={}] - Context options
 * @param {Array} [context.consumedMaterials=[]] - Consumed material rows (`[{ material_id, quantity, ... }]`)
 * @param {Array} [context.procedures=[]] - Available clinic procedures (`[{ id, name, ... }]`)
 * @param {boolean} [context.isEditing=false] - Whether editing an existing treatment
 * @param {boolean} [context.forceSkipStock=false] - Whether to set `skip_stock_check: true`
 * @returns {Object} Normalized treatment payload ready for `onSave` (`useTreatmentOperations.handleSaveTreatment`)
 */
export function buildTreatmentPayload(
    treatment = {},
    {
        consumedMaterials = [],
        procedures = [],
        isEditing = false,
        forceSkipStock = false,
    } = {},
) {
    const safeProcedures = Array.isArray(procedures) ? procedures : [];

    // Clean and validate consumed materials
    const cleanedMaterials = (consumedMaterials || [])
        .map((m) => ({
            material_id: m.material_id || m.id,
            quantity: Number.isFinite(parseFloat(m.quantity)) ? parseFloat(m.quantity) : 1,
            session_id: m.session_id || null,
            weight_score: Number.isFinite(parseFloat(m.weight_score))
                ? parseFloat(m.weight_score)
                : (Number.isFinite(parseFloat(m.weight)) ? parseFloat(m.weight) : 1.0),
            is_manual_override: m.is_manual_override || false,
            material_type: m.material_type || null,
            category_id: m.category_id || null,
        }))
        .filter((m) => m.quantity > 0 && m.material_id);

    const surfaceList = Array.isArray(treatment.surfaces) && treatment.surfaces.length > 0
        ? treatment.surfaces
        : (treatment.surface ? String(treatment.surface).replace(/[^A-Za-z]/g, '').toUpperCase().split('') : []);
    const surfaceStr = surfaceList.join('') || treatment.surface || null;
    const targetKind = surfaceList.length > 0 ? 'surface' : (treatment.target_kind || 'tooth');

    return {
        ...treatment,
        patient_id: treatment.patient_id,
        doctor_id: treatment.doctor_id,
        tooth_number: palmerToFdi(treatment.tooth_number) || null,
        surface: surfaceStr,
        surfaces: surfaceList.length > 0 ? surfaceList : undefined,
        target_kind: targetKind,
        clinical_work_item_id: !isEditing && treatment.clinical_work_item_id ? treatment.clinical_work_item_id : undefined,
        procedure_id: safeProcedures.find((p) => p.name === treatment.procedure)?.id,
        cost: parseFloat(treatment.cost) || 0,
        discount: parseFloat(treatment.discount) || 0,
        status: treatment.status || 'Done',
        notes: treatment.notes,
        canal_count: !isNaN(parseInt(treatment.canal_count)) ? parseInt(treatment.canal_count, 10) : null,
        sessions: treatment.sessions,
        complications: treatment.complications,
        consumedMaterials: cleanedMaterials,
        skip_stock_check: forceSkipStock,
    };
}
