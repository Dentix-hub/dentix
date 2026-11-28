import { queryKeys } from '@/lib/queryClient';
import { financeKeys } from '@/features/finance/queryKeys';

/**
 * Centrally invalidates all clinical-related queries for a given patient.
 * Ensures odontogram, clinical workspace, treatment plans, plan overlays,
 * care sessions, teeth statuses, billing/lab caches, finance summaries,
 * and inventory caches stay strictly consistent after any clinical mutation.
 *
 * @param {import('@tanstack/react-query').QueryClient} queryClient
 * @param {string|number} patientId
 */
export const invalidatePatientClinicalQueries = (queryClient, patientId) => {
    if (!queryClient || !patientId) return;

    const pid = String(patientId);
    const pidNum = Number(patientId);
    const hasNumericPid = !Number.isNaN(pidNum) && pidNum !== pid;

    // 1. Clinical Workspace (odontogram projection)
    queryClient.invalidateQueries({ queryKey: queryKeys.patientClinicalWorkspace(pid) });
    if (hasNumericPid) {
        queryClient.invalidateQueries({ queryKey: queryKeys.patientClinicalWorkspace(pidNum) });
    }

    // 2. Clinical Treatment Plans & candidates
    queryClient.invalidateQueries({ queryKey: queryKeys.patientClinicalPlans(pid) });
    if (hasNumericPid) {
        queryClient.invalidateQueries({ queryKey: queryKeys.patientClinicalPlans(pidNum) });
    }
    queryClient.invalidateQueries({ queryKey: ['patient', pid, 'clinical-plans'] });
    queryClient.invalidateQueries({ queryKey: ['patient', pidNum, 'clinical-plans'] });

    // 3. Care Sessions (active, resumable, list)
    queryClient.invalidateQueries({ queryKey: ['patient', pid, 'care-sessions'] });
    queryClient.invalidateQueries({ queryKey: ['patient', pidNum, 'care-sessions'] });

    // 4. Treatments history, clinical work items, lab orders, & payments
    queryClient.invalidateQueries({ queryKey: queryKeys.patientTreatments(pid) });
    if (hasNumericPid) {
        queryClient.invalidateQueries({ queryKey: queryKeys.patientTreatments(pidNum) });
    }
    queryClient.invalidateQueries({ queryKey: ['patient', pid, 'clinical-work-items'] });
    if (hasNumericPid) {
        queryClient.invalidateQueries({ queryKey: ['patient', pidNum, 'clinical-work-items'] });
    }
    queryClient.invalidateQueries({ queryKey: ['patient', pid, 'lab-orders'] });
    if (hasNumericPid) {
        queryClient.invalidateQueries({ queryKey: ['patient', pidNum, 'lab-orders'] });
    }
    queryClient.invalidateQueries({ queryKey: ['patient', pid, 'payments'] });
    if (hasNumericPid) {
        queryClient.invalidateQueries({ queryKey: ['patient', pidNum, 'payments'] });
    }

    // 5. Patient Teeth status
    queryClient.invalidateQueries({ queryKey: queryKeys.patientTeeth(pid) });
    if (hasNumericPid) {
        queryClient.invalidateQueries({ queryKey: queryKeys.patientTeeth(pidNum) });
    }

    // 6. Plan overlay query / cache if any
    queryClient.invalidateQueries({ queryKey: ['patientPlanOverlay', pid] });
    queryClient.invalidateQueries({ queryKey: ['patientPlanOverlay', pidNum] });

    // 7. Finance & Dashboard & Inventory caches
    queryClient.invalidateQueries({ queryKey: financeKeys.all });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
    queryClient.invalidateQueries({ queryKey: ['inventory-stock'] });
    queryClient.invalidateQueries({ queryKey: ['active-sessions'] });
    queryClient.invalidateQueries({ queryKey: ['material-stock'] });
};

/**
 * Invalidates all cached patient clinical queries across any patient when a
 * clinic-wide setting (such as procedure chart appearance styles) changes.
 *
 * @param {import('@tanstack/react-query').QueryClient} queryClient
 */
export const invalidateAllPatientsClinicalQueries = (queryClient) => {
    if (!queryClient) return;
    queryClient.invalidateQueries({
        predicate: (query) => {
            const key = query.queryKey;
            if (!Array.isArray(key) || key[0] !== 'patient') return false;
            return [
                'clinical-workspace',
                'clinical-work-items',
                'clinical-plans',
                'care-sessions',
                'treatments',
                'teeth',
            ].includes(key[2]);
        },
    });
    queryClient.invalidateQueries({ queryKey: ['patientPlanOverlay'] });
};
