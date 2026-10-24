import { fdiToPalmer } from '@/utils/toothUtils';

/**
 * Shared prefill builder for chart-driven treatment sheet opens (U3.2).
 * Normalizes tooth notation, surfaces, target kind, procedure names,
 * and clinical linking metadata without mutating base objects.
 *
 * @param {Object} options
 * @param {Object} [options.baseTreatment={}] - Initial treatment skeleton (from getInitialTreatment)
 * @param {string} [options.source='manual'] - Entry source identifier ('quick_launcher' | 'plan_item' | 'chart_selection' | 'tooth_picker' | 'manual')
 * @param {number|string|null} [options.toothKey=null] - FDI tooth number or key (e.g. '16', 16)
 * @param {string|null} [options.palmerTooth=null] - Pre-formatted Palmer tooth string (e.g. 'UR6')
 * @param {string[]|null} [options.surfaces=[]] - Array of tooth surface codes (e.g. ['M', 'O'])
 * @param {string|null} [options.surface=''] - Surface string (e.g. 'MO')
 * @param {string|null} [options.targetKind=null] - 'tooth' | 'surface' | 'quadrant' | 'arch' | 'mouth'
 * @param {string} [options.procedureName=''] - Procedure name to prefill
 * @param {number|null} [options.clinicalWorkItemId=null] - ClinicalWorkItem ID to link (U2.1)
 * @param {string} [options.planTitle=''] - Clinical plan title for display
 * @param {number|null} [options.planId=null] - Clinical plan ID
 * @param {string} [options.workItemCode=''] - Work item canonical procedure code
 * @param {number|null} [options.defaultPriceListId=null] - Patient's active price list ID
 * @returns {Object} Normalized prefill object ready for QuickTreatmentSheet
 */
export function buildTreatmentPrefill({
    baseTreatment = {},
    source = 'manual',
    toothKey = null,
    palmerTooth = null,
    surfaces = [],
    surface = '',
    targetKind = null,
    procedureName = '',
    clinicalWorkItemId = null,
    planTitle = '',
    planId = null,
    workItemCode = '',
    defaultPriceListId = null,
    selectedTeeth = [],
    selectedSurfacesByTooth = {},
} = {}) {
    // 1. Resolve tooth number in Palmer notation for treatment sheet
    let resolvedPalmer = palmerTooth || '';
    if (!resolvedPalmer && toothKey !== null && toothKey !== undefined && toothKey !== '') {
        const parsedFdi = Number.parseInt(toothKey, 10);
        if (!Number.isNaN(parsedFdi)) {
            resolvedPalmer = fdiToPalmer(parsedFdi) || String(toothKey);
        } else {
            resolvedPalmer = String(toothKey);
        }
    }

    // 2. Resolve surfaces array and string representation
    let resolvedSurfaces = [];
    if (Array.isArray(surfaces) && surfaces.length > 0) {
        resolvedSurfaces = [...surfaces];
    } else if (surface && typeof surface === 'string') {
        resolvedSurfaces = surface.replace(/[^A-Za-z]/g, '').toUpperCase().split('');
    }

    const surfaceStr = resolvedSurfaces.join('');

    // 3. Resolve target_kind ('surface' if surfaces exist, else 'tooth' or provided targetKind)
    const resolvedTargetKind = targetKind || (resolvedSurfaces.length > 0 ? 'surface' : 'tooth');

    return {
        ...baseTreatment,
        tooth_number: resolvedPalmer || baseTreatment.tooth_number || '',
        procedure: procedureName || baseTreatment.procedure || '',
        surface: surfaceStr,
        surfaces: resolvedSurfaces,
        target_kind: resolvedTargetKind,
        selectedTeeth: Array.isArray(selectedTeeth) && selectedTeeth.length > 0 ? selectedTeeth : (resolvedPalmer ? [resolvedPalmer] : (toothKey ? [String(toothKey)] : [])),
        selectedSurfacesByTooth: selectedSurfacesByTooth || {},
        default_price_list_id: defaultPriceListId ?? baseTreatment.default_price_list_id ?? null,
        prefill_source: source,
        ...(clinicalWorkItemId ? { clinical_work_item_id: clinicalWorkItemId } : {}),
        ...(planTitle ? { plan_title: planTitle } : {}),
        ...(planId ? { plan_id: planId } : {}),
        ...(workItemCode ? { work_item_code: workItemCode } : {}),
    };
}
