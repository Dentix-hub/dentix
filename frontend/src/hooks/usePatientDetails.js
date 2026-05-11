import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import {
    getPatient,
    getPatientTeeth,
    getPatientTreatments,
    getPatientPayments,
    getAttachments,
    createPayment,
    deletePayment
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
            queryClient.invalidateQueries({ queryKey: ['dashboardStats'] });
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
            queryClient.invalidateQueries({ queryKey: ['dashboardStats'] });
        },
    });
}

/**
 * Hook for patient attachments - loads only on files tab
 */
export function usePatientAttachments(patientId, enabled = true) {
    return useQuery({
        queryKey: ['patient', patientId, 'attachments'],
        queryFn: async () => {
            const res = await getAttachments(patientId);
            return res.data || [];
        },
        enabled: !!patientId && enabled,
        staleTime: 30 * 1000,
    });
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

