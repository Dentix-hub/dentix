import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { queryKeys } from '@/lib/queryClient';
import {
    getPatient,
    getPatientTeeth,
    getPatientClinicalWorkspace,
    getPatientTreatments,
    getPatientPayments,
    getAttachments,
    createPayment,
    deletePayment,
    getPatientLabOrders,
    getPatientClinicalPlans,
    createPatientClinicalPlan,
    getPatientClinicalPlanCandidates,
    addPatientClinicalPlanPhase,
    updatePatientClinicalPlanPhase,
    reorderPatientClinicalPlanPhases,
    deletePatientClinicalPlanPhase,
    addPatientClinicalPlanItem,
    removePatientClinicalPlanItem,
    transitionPatientClinicalPlan,
    getTenantFeatures,
    getActiveCareSession,
    getResumableCareSessionContext,
    getPatientCareSessions,
    startCareSession,
    finishCareSession,
    transitionCareSession,
    addCareSessionStep,
    updateCareSessionStep,
    applyCareSessionTemplate,
    recordCareObservation,
    getClinicalAttachmentLinks,
    createClinicalAttachmentLink,
    deleteClinicalAttachmentLink,
} from '@/api';


/**
 * Hook for patient core data (basic info) - loads immediately
 */
export function usePatient(patientId) {
    return useQuery({
        queryKey: ['patient', patientId],
        queryFn: async () => {
            const res = await getPatient(patientId);
            return res.data;
        },
        enabled: !!patientId,
        staleTime: 60 * 1000, // 1 minute
    });
}

/**
 * Hook for patient clinical workspace snapshot - loads only when chart tab is active
 */
export function usePatientClinicalWorkspace(patientId, { enabled = true } = {}) {
    return useQuery({
        queryKey: queryKeys.patientClinicalWorkspace(patientId),
        queryFn: async () => {
            const res = await getPatientClinicalWorkspace(patientId);
            return res.data;
        },
        enabled: !!patientId && enabled,
        staleTime: 30 * 1000,
    });
}

/**
 * Hook for patient teeth data - loads for chart tab
 */
export function usePatientTeeth(patientId, enabled = true) {
    return useQuery({
        queryKey: ['patient', patientId, 'teeth'],
        queryFn: async () => {
            const res = await getPatientTeeth(patientId);
            const teethMap = {};
            (res.data || []).forEach(t => { teethMap[t.tooth_number] = t; });
            return teethMap;
        },
        enabled: !!patientId && enabled,
        staleTime: 60 * 1000,
    });
}

/**
 * Hook for patient treatments - loads only on history tab
 */
export function usePatientTreatments(patientId, enabled = true) {
    return useQuery({
        queryKey: ['patient', patientId, 'treatments'],
        queryFn: async () => {
            const res = await getPatientTreatments(patientId);
            return res.data || [];
        },
        enabled: !!patientId && enabled,
        staleTime: 30 * 1000,
    });
}

/**
 * Hook for patient lab orders (G12-M11).
 */
export function usePatientLabOrders(patientId, enabled = true) {
    return useQuery({
        queryKey: ['patient', patientId, 'lab-orders'],
        queryFn: async () => {
            const res = await getPatientLabOrders(patientId);
            return res.data || [];
        },
        enabled: Boolean(patientId && enabled),
        staleTime: 30 * 1000,
    });
}

/**
 * Hook for patient payments - loads only on billing tab
 */
export function usePatientPayments(patientId, enabled = true) {
    return useQuery({
        queryKey: ['patient', patientId, 'payments'],
        queryFn: async () => {
            const res = await getPatientPayments(patientId);
            return res.data || [];
        },
        enabled: !!patientId && enabled,
        staleTime: 30 * 1000,
    });
}

/**
 * Hook for creating a payment with optimistic update
 */
export function useCreatePayment() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: createPayment,
        onMutate: async (newPayment) => {
            const patientId = newPayment.patient_id;
            await queryClient.cancelQueries({ queryKey: ['patient', patientId, 'payments'] });
            const previousPayments = queryClient.getQueryData(['patient', patientId, 'payments']);

            if (previousPayments) {
                queryClient.setQueryData(['patient', patientId, 'payments'], old => [
                    ...old,
                    { ...newPayment, id: 'temp-' + Date.now(), date: new Date().toISOString(), status: 'paid' }
                ]);
            }

            return { previousPayments, patientId };
        },
        onError: (err, newPayment, context) => {
            if (context?.previousPayments) {
                queryClient.setQueryData(['patient', context.patientId, 'payments'], context.previousPayments);
            }
        },
        onSettled: (data, err, variables, context) => {
            queryClient.invalidateQueries({ queryKey: ['patient', context.patientId, 'payments'] });
            queryClient.invalidateQueries({ queryKey: ['patient', context.patientId] });
            queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
        },
    });
}

/**
 * Hook for deleting a payment with optimistic update
 */
export function useDeletePayment() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ paymentId }) => deletePayment(paymentId),
        onMutate: async ({ paymentId, patientId }) => {
            await queryClient.cancelQueries({ queryKey: ['patient', patientId, 'payments'] });
            const previousPayments = queryClient.getQueryData(['patient', patientId, 'payments']);

            if (previousPayments) {
                queryClient.setQueryData(['patient', patientId, 'payments'], old => 
                    old.filter(p => p.id !== paymentId)
                );
            }

            return { previousPayments, patientId };
        },
        onError: (err, variables, context) => {
            if (context?.previousPayments) {
                queryClient.setQueryData(['patient', context.patientId, 'payments'], context.previousPayments);
            }
        },
        onSettled: (data, err, variables, context) => {
            queryClient.invalidateQueries({ queryKey: ['patient', context.patientId, 'payments'] });
            queryClient.invalidateQueries({ queryKey: ['patient', context.patientId] });
            queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
        },
    });
}

export const ATTACHMENT_POLL_INTERVAL_MS = 2500;
export const MAX_ATTACHMENT_POLL_DURATION_MS = 25000;
export const MAX_ATTACHMENT_POLL_ATTEMPTS = 10;

/**
 * Hook for patient attachments - loads only on files tab with bounded polling
 */
export function usePatientAttachments(patientId, enabled = true) {
    const [isPollingStalled, setIsPollingStalled] = useState(false);
    const pendingSinceRef = useRef(null);
    const knownPendingIdsRef = useRef(new Set());

    useEffect(() => {
        pendingSinceRef.current = null;
        knownPendingIdsRef.current = new Set();
        setIsPollingStalled(false);
    }, [patientId]);

    const query = useQuery({
        queryKey: ['patient', patientId, 'attachments'],
        queryFn: async () => {
            const res = await getAttachments(patientId);
            return res.data || [];
        },
        enabled: !!patientId && enabled,
        staleTime: 30 * 1000,
        refetchInterval: (q) => {
            const data = q.state.data;
            if (!Array.isArray(data)) return false;

            const pendingItems = data.filter(
                (att) => att.storage_status === 'pending' || att.storage_status === 'deleting'
            );

            if (pendingItems.length === 0) {
                if (pendingSinceRef.current !== null || knownPendingIdsRef.current.size > 0) {
                    pendingSinceRef.current = null;
                    knownPendingIdsRef.current = new Set();
                    if (isPollingStalled) setIsPollingStalled(false);
                }
                return false;
            }

            const currentPendingIds = new Set(pendingItems.map((att) => att.id));
            const hasNewOperation = [...currentPendingIds].some(
                (id) => !knownPendingIdsRef.current.has(id)
            );

            const now = Date.now();
            if (pendingSinceRef.current === null || hasNewOperation) {
                pendingSinceRef.current = now;
                knownPendingIdsRef.current = currentPendingIds;
                if (isPollingStalled) setIsPollingStalled(false);
            } else {
                knownPendingIdsRef.current = currentPendingIds;
            }

            if (now - pendingSinceRef.current >= MAX_ATTACHMENT_POLL_DURATION_MS) {
                if (!isPollingStalled) setIsPollingStalled(true);
                return false;
            }

            return ATTACHMENT_POLL_INTERVAL_MS;
        },
    });

    const manualRetry = useCallback((...args) => {
        pendingSinceRef.current = Date.now();
        setIsPollingStalled(false);
        return query.refetch(...args);
    }, [query]);

    return {
        ...query,
        refetch: manualRetry,
        manualRetry,
        isPollingStalled,
    };
}

/**
 * Hook to invalidate patient-related queries
 */
export function useInvalidatePatientData() {
    const queryClient = useQueryClient();
    return useCallback((patientId, type) => {
        if (type) {
            queryClient.invalidateQueries({ queryKey: ['patient', patientId, type] });
        } else {
            queryClient.invalidateQueries({ queryKey: ['patient', patientId] });
        }
    }, [queryClient]);
}

/**
 * Hook for patient clinical treatment plans - loads when chart tab is active and feature enabled
 */
export function usePatientClinicalPlans(patientId, { enabled = true } = {}) {
    return useQuery({
        queryKey: queryKeys.patientClinicalPlans(patientId),
        queryFn: async () => {
            const res = await getPatientClinicalPlans(patientId);
            return res.data || [];
        },
        enabled: !!patientId && enabled,
        staleTime: 30 * 1000,
    });
}

/**
 * Hook for creating a patient clinical treatment plan
 */
export function useCreatePatientClinicalPlan() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, data }) => createPatientClinicalPlan(patientId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalPlans(variables.patientId),
            });
        },
    });
}

/**
 * Hook for tenant feature flags
 */
export function useTenantFeatures() {
    return useQuery({
        queryKey: queryKeys.tenantFeatures,
        queryFn: async () => {
            const res = await getTenantFeatures();
            return res.data?.features || [];
        },
        staleTime: 60 * 1000,
    });
}

/**
 * Hook for patient clinical plan candidate work items
 */
export function usePatientClinicalPlanCandidates(patientId, planId, { enabled = true } = {}) {
    return useQuery({
        queryKey: queryKeys.patientClinicalPlanCandidates(patientId, planId),
        queryFn: async () => {
            const res = await getPatientClinicalPlanCandidates(patientId, planId);
            return res.data || [];
        },
        enabled: !!patientId && !!planId && enabled,
        staleTime: 10 * 1000,
    });
}

/**
 * Hook for adding a phase to a treatment plan
 */
export function useAddPatientClinicalPlanPhase() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, planId, data }) => addPatientClinicalPlanPhase(patientId, planId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalPlans(variables.patientId),
            });
        },
    });
}

/**
 * Hook for updating a phase (rename / notes) in a treatment plan
 */
export function useUpdatePatientClinicalPlanPhase() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, planId, phaseId, data }) =>
            updatePatientClinicalPlanPhase(patientId, planId, phaseId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalPlans(variables.patientId),
            });
        },
    });
}

/**
 * Hook for atomically reordering phases in a treatment plan
 */
export function useReorderPatientClinicalPlanPhases() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, planId, phaseIds }) =>
            reorderPatientClinicalPlanPhases(patientId, planId, phaseIds),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalPlans(variables.patientId),
            });
        },
    });
}

/**
 * Hook for deleting a phase from a treatment plan
 */
export function useDeletePatientClinicalPlanPhase() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, planId, phaseId }) =>
            deletePatientClinicalPlanPhase(patientId, planId, phaseId),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalPlans(variables.patientId),
            });
        },
    });
}

/**
 * Hook for adding a procedure/work-item to a treatment plan phase
 */
export function useAddPatientClinicalPlanItem() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, planId, phaseId, data }) =>
            addPatientClinicalPlanItem(patientId, planId, phaseId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalPlans(variables.patientId),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalPlanCandidates(variables.patientId, variables.planId),
            });
        },
    });
}

/**
 * Hook for removing a procedure/work-item from a treatment plan phase
 */
export function useRemovePatientClinicalPlanItem() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, planId, phaseId, itemId }) =>
            removePatientClinicalPlanItem(patientId, planId, phaseId, itemId),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalPlans(variables.patientId),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalPlanCandidates(variables.patientId, variables.planId),
            });
        },
    });
}

/**
 * Hook for transitioning treatment plan status
 */
export function useTransitionPatientClinicalPlan() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, planId, data }) =>
            transitionPatientClinicalPlan(patientId, planId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalPlans(variables.patientId),
            });
        },
    });
}

/**
 * Hook for active patient care session
 */
export function useActiveCareSession(patientId, { enabled = true } = {}) {
    return useQuery({
        queryKey: queryKeys.patientActiveCareSession(patientId),
        queryFn: async () => {
            const res = await getActiveCareSession(patientId);
            return res.data || null;
        },
        enabled: !!patientId && enabled,
        staleTime: 10 * 1000,
        retry: (failureCount, error) => {
            if (error?.response?.status === 404) return false;
            return failureCount < 1;
        },
    });
}

/**
 * Hook for resumable care session context (Slice S21 / G10-M12)
 */
export function useResumableCareSession(patientId, { enabled = true } = {}) {
    return useQuery({
        queryKey: queryKeys.patientResumableCareSession(patientId),
        queryFn: async () => {
            const res = await getResumableCareSessionContext(patientId);
            return res.data || { has_resumable: false, items: [] };
        },
        enabled: !!patientId && enabled,
        staleTime: 10 * 1000,
        retry: (failureCount, error) => {
            if (error?.response?.status === 404) return false;
            return failureCount < 1;
        },
    });
}

/**
 * Hook for listing patient care sessions
 */
export function usePatientCareSessions(patientId, params = {}, { enabled = true } = {}) {
    return useQuery({
        queryKey: queryKeys.patientCareSessions(patientId, params),
        queryFn: async () => {
            const res = await getPatientCareSessions(patientId, params);
            return res.data || [];
        },
        enabled: !!patientId && enabled,
        staleTime: 30 * 1000,
    });
}

/**
 * Hook for starting a care session
 */
export function useStartCareSession() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, data }) => startCareSession(patientId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientActiveCareSession(variables.patientId),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientResumableCareSession(variables.patientId),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientCareSessions(variables.patientId),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalWorkspace(variables.patientId),
            });
        },
    });
}

/**
 * Hook for finishing a care session
 */
export function useFinishCareSession() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, sessionId, data }) => finishCareSession(patientId, sessionId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientActiveCareSession(variables.patientId),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientResumableCareSession(variables.patientId),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientCareSessions(variables.patientId),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientClinicalWorkspace(variables.patientId),
            });
        },
    });
}

/**
 * Hook for transitioning care session status
 */
export function useTransitionCareSession() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, sessionId, data }) => transitionCareSession(patientId, sessionId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientActiveCareSession(variables.patientId),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientResumableCareSession(variables.patientId),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientCareSessions(variables.patientId),
            });
        },
    });
}

/**
 * Hook for adding a step to a care session
 */
export function useAddCareSessionStep() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, sessionId, data }) => addCareSessionStep(patientId, sessionId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientActiveCareSession(variables.patientId),
            });
        },
    });
}

/**
 * Hook for updating a care session step
 */
export function useUpdateCareSessionStep() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, sessionId, stepId, data }) =>
            updateCareSessionStep(patientId, sessionId, stepId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientActiveCareSession(variables.patientId),
            });
        },
    });
}

/**
 * Hook for applying a workflow template to a care session
 */
export function useApplyCareSessionTemplate() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, sessionId, data }) =>
            applyCareSessionTemplate(patientId, sessionId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientActiveCareSession(variables.patientId),
            });
        },
    });
}

/**
 * Hook for recording a care observation
 */
export function useRecordCareObservation() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, sessionId, data }) =>
            recordCareObservation(patientId, sessionId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientActiveCareSession(variables.patientId),
            });
        },
    });
}

/**
 * Hook for listing patient clinical attachment links (Slice S24 / G15-M03..M05, M07..M08)
 */
export function usePatientClinicalAttachmentLinks(patientId, filters = {}, { enabled = true } = {}) {
    return useQuery({
        queryKey: queryKeys.patientClinicalAttachmentLinks(patientId, filters),
        queryFn: async () => {
            const res = await getClinicalAttachmentLinks(patientId, filters);
            return Array.isArray(res.data) ? res.data : (Array.isArray(res) ? res : []);
        },
        enabled: !!patientId && enabled,
        staleTime: 15 * 1000,
    });
}

/**
 * Hook for creating a clinical attachment link
 */
export function useCreateClinicalAttachmentLink() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, data }) => createClinicalAttachmentLink(patientId, data),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: ['patient', variables.patientId, 'clinical-attachment-links'],
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientAttachments(variables.patientId),
            });
        },
    });
}

/**
 * Hook for deleting a clinical attachment link
 */
export function useDeleteClinicalAttachmentLink() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ patientId, linkId }) => deleteClinicalAttachmentLink(patientId, linkId),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({
                queryKey: ['patient', variables.patientId, 'clinical-attachment-links'],
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.patientAttachments(variables.patientId),
            });
        },
    });
}




