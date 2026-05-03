import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import {
    getPatient,
    getPatientTeeth,
    getPatientTreatments,
    getPatientPayments,
    getAttachments
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
