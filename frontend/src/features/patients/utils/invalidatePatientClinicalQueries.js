import { queryKeys } from '@/lib/queryClient';

/**
 * Centrally invalidates all clinical-related queries for a given patient.
 * Ensures odontogram, clinical workspace, treatment plans, plan overlays,
 * care sessions, teeth statuses, and treatment history stay strictly consistent
 * after any clinical mutation (treatments, findings, procedures, lab handoffs).
 *
 * @param {import('@tanstack/react-query').QueryClient} queryClient
 * @param {string|number} patientId
 */
export const invalidatePatientClinicalQueries = (queryClient, patientId) => {
    if (!queryClient || !patientId) return;

    const pid = String(patientId);
    const pidNum = Number(patientId);

    // 1. Clinical Workspace (odontogram projection)
    queryClient.invalidateQueries({ queryKey: queryKeys.patientClinicalWorkspace(pid) });
    if (!Number.isNaN(pidNum) && pidNum !== pid) {
        queryClient.invalidateQueries({ queryKey: queryKeys.patientClinicalWorkspace(pidNum) });
    }

    // 2. Clinical Treatment Plans & candidates
    queryClient.invalidateQueries({ queryKey: queryKeys.patientClinicalPlans(pid) });
    if (!Number.isNaN(pidNum) && pidNum !== pid) {
        queryClient.invalidateQueries({ queryKey: queryKeys.patientClinicalPlans(pidNum) });
    }
    queryClient.invalidateQueries({ queryKey: ['patient', pid, 'clinical-plans'] });
    queryClient.invalidateQueries({ queryKey: ['patient', pidNum, 'clinical-plans'] });

    // 3. Care Sessions (active, resumable, list)
    queryClient.invalidateQueries({ queryKey: ['patient', pid, 'care-sessions'] });
    queryClient.invalidateQueries({ queryKey: ['patient', pidNum, 'care-sessions'] });

    // 4. Treatments history
    queryClient.invalidateQueries({ queryKey: queryKeys.patientTreatments(pid) });
    if (!Number.isNaN(pidNum) && pidNum !== pid) {
        queryClient.invalidateQueries({ queryKey: queryKeys.patientTreatments(pidNum) });
    }

    // 5. Patient Teeth status
    queryClient.invalidateQueries({ queryKey: queryKeys.patientTeeth(pid) });
    if (!Number.isNaN(pidNum) && pidNum !== pid) {
        queryClient.invalidateQueries({ queryKey: queryKeys.patientTeeth(pidNum) });
    }

    // 6. Plan overlay query / cache if any
    queryClient.invalidateQueries({ queryKey: ['patientPlanOverlay', pid] });
    queryClient.invalidateQueries({ queryKey: ['patientPlanOverlay', pidNum] });
};
