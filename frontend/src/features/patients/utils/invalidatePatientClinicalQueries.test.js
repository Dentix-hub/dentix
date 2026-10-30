import { describe, it, expect, vi } from 'vitest';
import { invalidatePatientClinicalQueries } from './invalidatePatientClinicalQueries';
import { queryKeys } from '@/lib/queryClient';

describe('invalidatePatientClinicalQueries', () => {
    it('does nothing when queryClient or patientId is missing', () => {
        const queryClient = { invalidateQueries: vi.fn() };
        invalidatePatientClinicalQueries(null, 123);
        invalidatePatientClinicalQueries(queryClient, null);
        invalidatePatientClinicalQueries(queryClient, undefined);
        expect(queryClient.invalidateQueries).not.toHaveBeenCalled();
    });

    it('invalidates workspace, plans, care-sessions, treatments, and teeth for numeric patientId', () => {
        const queryClient = { invalidateQueries: vi.fn() };
        invalidatePatientClinicalQueries(queryClient, 42);

        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: queryKeys.patientClinicalWorkspace('42'),
        });
        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: queryKeys.patientClinicalPlans('42'),
        });
        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: ['patient', '42', 'care-sessions'],
        });
        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: queryKeys.patientTreatments('42'),
        });
        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: queryKeys.patientTeeth('42'),
        });
    });

    it('invalidates workspace, plans, care-sessions, treatments, and teeth for string patientId', () => {
        const queryClient = { invalidateQueries: vi.fn() };
        invalidatePatientClinicalQueries(queryClient, '99');

        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: queryKeys.patientClinicalWorkspace('99'),
        });
        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: queryKeys.patientClinicalPlans('99'),
        });
    });
});
