import { renderHook, act } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTreatmentOperations } from './useTreatmentOperations';
import { queryKeys } from '@/lib/queryClient';

const mockCreateTreatment = vi.fn();
const mockUpdateTreatment = vi.fn();
const mockUpdateToothStatus = vi.fn();

vi.mock('@/api', () => ({
    createTreatment: (...args) => mockCreateTreatment(...args),
    updateTreatment: (...args) => mockUpdateTreatment(...args),
    updateToothStatus: (...args) => mockUpdateToothStatus(...args),
}));

vi.mock('@/utils/logger', () => ({
    default: {
        log: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
    },
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
    }),
}));

vi.mock('@/shared/ui', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

describe('useTreatmentOperations', () => {
    let queryClient;
    let refetchHistory;
    let refetchTeeth;
    let refetchWorkspace;
    let setIsTreatmentModalOpen;
    let setEditingTreatmentId;

    const createWrapper = () => {
        const Wrapper = ({ children }) => (
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        );
        Wrapper.displayName = 'QueryClientWrapper';
        return Wrapper;
    };

    beforeEach(() => {
        vi.clearAllMocks();
        queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false } },
        });
        vi.spyOn(queryClient, 'invalidateQueries');
        refetchHistory = vi.fn().mockResolvedValue({});
        refetchTeeth = vi.fn().mockResolvedValue({});
        refetchWorkspace = vi.fn().mockResolvedValue({});
        setIsTreatmentModalOpen = vi.fn();
        setEditingTreatmentId = vi.fn();
    });

    it('refetches workspace and invalidates clinical workspace query on treatment save with tooth number', async () => {
        mockCreateTreatment.mockResolvedValue({ id: 10 });
        mockUpdateToothStatus.mockResolvedValue({});

        const { result } = renderHook(
            () =>
                useTreatmentOperations({
                    patientId: 101,
                    refetchHistory,
                    refetchTeeth,
                    refetchWorkspace,
                    setIsTreatmentModalOpen,
                    setEditingTreatmentId,
                    editingTreatmentId: null,
                    selectedToothCondition: 'Healthy',
                }),
            { wrapper: createWrapper() }
        );

        await act(async () => {
            await result.current.handleSaveTreatment({
                procedure: 'Scaling',
                tooth_number: 'UR6',
                cost: 100,
            });
        });

        expect(mockCreateTreatment).toHaveBeenCalledTimes(1);
        expect(mockUpdateToothStatus).toHaveBeenCalledTimes(1);
        expect(refetchHistory).toHaveBeenCalledTimes(1);
        expect(refetchWorkspace).toHaveBeenCalledTimes(1);
        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: queryKeys.patientClinicalWorkspace(101),
        });
        expect(setIsTreatmentModalOpen).toHaveBeenCalledWith(false);
    });

    it('refetches workspace and invalidates query when saving treatment without tooth (continue without tooth)', async () => {
        mockCreateTreatment.mockResolvedValue({ id: 11 });

        const { result } = renderHook(
            () =>
                useTreatmentOperations({
                    patientId: 101,
                    refetchHistory,
                    refetchTeeth,
                    refetchWorkspace,
                    setIsTreatmentModalOpen,
                    setEditingTreatmentId,
                    editingTreatmentId: null,
                    selectedToothCondition: 'Healthy',
                }),
            { wrapper: createWrapper() }
        );

        await act(async () => {
            await result.current.handleSaveTreatment({
                procedure: 'Consultation',
                tooth_number: null,
                cost: 50,
            });
        });

        expect(mockCreateTreatment).toHaveBeenCalledTimes(1);
        expect(mockUpdateToothStatus).not.toHaveBeenCalled();
        expect(refetchHistory).toHaveBeenCalledTimes(1);
        expect(refetchWorkspace).toHaveBeenCalledTimes(1);
        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: queryKeys.patientClinicalWorkspace(101),
        });
        expect(setIsTreatmentModalOpen).toHaveBeenCalledWith(false);
    });

    it('refetches workspace and invalidates query when updating existing treatment', async () => {
        mockUpdateTreatment.mockResolvedValue({ id: 22 });

        const { result } = renderHook(
            () =>
                useTreatmentOperations({
                    patientId: 101,
                    refetchHistory,
                    refetchTeeth,
                    refetchWorkspace,
                    setIsTreatmentModalOpen,
                    setEditingTreatmentId,
                    editingTreatmentId: 22,
                    selectedToothCondition: 'Healthy',
                }),
            { wrapper: createWrapper() }
        );

        await act(async () => {
            await result.current.handleSaveTreatment({
                procedure: 'Composite Filling',
                tooth_number: null,
                cost: 150,
            });
        });

        expect(mockUpdateTreatment).toHaveBeenCalledWith(22, expect.objectContaining({
            procedure: 'Composite Filling',
            patient_id: 101,
        }));
        expect(refetchHistory).toHaveBeenCalledTimes(1);
        expect(refetchWorkspace).toHaveBeenCalledTimes(1);
        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: queryKeys.patientClinicalWorkspace(101),
        });
        expect(setEditingTreatmentId).toHaveBeenCalledWith(null);
    });
});
