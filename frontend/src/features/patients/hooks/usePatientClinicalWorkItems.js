import { useQuery } from '@tanstack/react-query';
import { getPatientClinicalWorkItems } from '@/api/patients';

export function usePatientClinicalWorkItems(patientId, enabled) {
    return useQuery({
        queryKey: ['patient', String(patientId), 'clinical-work-items'],
        queryFn: async () => {
            const { data } = await getPatientClinicalWorkItems(patientId);
            const items = data?.data ?? data;
            return Array.isArray(items) ? items : [];
        },
        enabled: Boolean(patientId && enabled),
    });
}
