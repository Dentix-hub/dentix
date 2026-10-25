import { renderHook, act } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTreatmentOperations } from './useTreatmentOperations';
import { queryKeys } from '@/lib/queryClient';
import { toast } from '@/shared/ui';

const mockCreateTreatment = vi.fn();
const mockUpdateTreatment = vi.fn();
const mockUpdateToothStatus = vi.fn();
const mockCreateLabOrder = vi.fn();

vi.mock('@/api', () => ({
    createTreatment: (...args) => mockCreateTreatment(...args),
    updateTreatment: (...args) => mockUpdateTreatment(...args),
    updateToothStatus: (...args) => mockUpdateToothStatus(...args),
    createLabOrder: (...args) => mockCreateLabOrder(...args),
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
        info: vi.fn(),
    },
}));

describe('useTreatmentOperations', () => {
    let queryClient;
    let refetchHistory;
    let refetchTeeth;
    let refetchWorkspace;
    let setIsTreatmentSheetOpen;
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
        setIsTreatmentSheetOpen = vi.fn();
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
                    setIsTreatmentSheetOpen,
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
                explicit_tooth_condition: 'Healthy',
            });
        });

        expect(mockCreateTreatment).toHaveBeenCalledTimes(1);
        expect(mockUpdateToothStatus).toHaveBeenCalledTimes(1);
        expect(refetchHistory).toHaveBeenCalledTimes(1);
        expect(refetchWorkspace).toHaveBeenCalledTimes(1);
        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
            queryKey: queryKeys.patientClinicalWorkspace(101),
        });
        expect(setIsTreatmentSheetOpen).toHaveBeenCalledWith(false);
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
                    setIsTreatmentSheetOpen,
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
        expect(setIsTreatmentSheetOpen).toHaveBeenCalledWith(false);
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
                    setIsTreatmentSheetOpen,
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

    it('strips prefill_source from create and update payloads', async () => {
        mockCreateTreatment.mockResolvedValue({ id: 33 });

        const { result } = renderHook(
            () =>
                useTreatmentOperations({
                    patientId: 101,
                    refetchHistory,
                    refetchTeeth,
                    refetchWorkspace,
                    setIsTreatmentSheetOpen,
                    setEditingTreatmentId,
                    editingTreatmentId: null,
                    selectedToothCondition: null,
                }),
            { wrapper: createWrapper() }
        );

        await act(async () => {
            await result.current.handleSaveTreatment({
                procedure: 'Composite Filling',
                tooth_number: null,
                cost: 150,
                prefill_source: 'quick_launcher',
            });
        });

        expect(mockCreateTreatment).toHaveBeenCalledTimes(1);
        const sentPayload = mockCreateTreatment.mock.calls[0][0];
        expect(sentPayload).not.toHaveProperty('prefill_source');
        expect(sentPayload.procedure).toBe('Composite Filling');
        expect(sentPayload.cost).toBe(150);
    });

    it('does not re-send Decayed when saving a filling on a Decayed tooth through the quick sheet', async () => {
        mockCreateTreatment.mockResolvedValue({ id: 12 });

        const { result } = renderHook(
            () =>
                useTreatmentOperations({
                    patientId: 101,
                    refetchHistory,
                    refetchTeeth,
                    refetchWorkspace,
                    setIsTreatmentSheetOpen,
                    setEditingTreatmentId,
                    editingTreatmentId: null,
                    selectedToothCondition: 'Decayed',
                }),
            { wrapper: createWrapper() }
        );

        await act(async () => {
            // Quick sheet save payload has tooth_number, but NO explicit_tooth_condition
            await result.current.handleSaveTreatment({
                procedure: 'Composite Filling',
                tooth_number: 'UR6',
                cost: 150,
            });
        });

        expect(mockCreateTreatment).toHaveBeenCalledTimes(1);
        expect(mockUpdateToothStatus).not.toHaveBeenCalled();
    });

    it('suppresses toast and refetch when skipToast and skipRefetch options are true', async () => {
        mockCreateTreatment.mockResolvedValue({ id: 50 });

        const { result } = renderHook(
            () =>
                useTreatmentOperations({
                    patientId: 101,
                    refetchHistory,
                    refetchTeeth,
                    refetchWorkspace,
                    setIsTreatmentSheetOpen,
                    setEditingTreatmentId,
                    editingTreatmentId: null,
                    selectedToothCondition: null,
                }),
            { wrapper: createWrapper() }
        );

        await act(async () => {
            await result.current.handleSaveTreatment(
                { procedure: 'Composite', tooth_number: '16', cost: 100 },
                { skipToast: true, skipRefetch: true }
            );
        });

        expect(mockCreateTreatment).toHaveBeenCalledTimes(1);
        expect(refetchHistory).not.toHaveBeenCalled();
        expect(refetchWorkspace).not.toHaveBeenCalled();
    });

    it('refetches clinical data on refetchOnly call', async () => {
        const { result } = renderHook(
            () =>
                useTreatmentOperations({
                    patientId: 101,
                    refetchHistory,
                    refetchTeeth,
                    refetchWorkspace,
                    setIsTreatmentSheetOpen,
                    setEditingTreatmentId,
                    editingTreatmentId: null,
                    selectedToothCondition: null,
                }),
            { wrapper: createWrapper() }
        );

        await act(async () => {
            await result.current.handleSaveTreatment(null, { refetchOnly: true });
        });

        expect(mockCreateTreatment).not.toHaveBeenCalled();
        expect(refetchHistory).toHaveBeenCalledTimes(1);
        expect(refetchWorkspace).toHaveBeenCalledTimes(1);
    });

    it('lab order failure shows error toast and does not roll back treatment', async () => {
        mockCreateTreatment.mockResolvedValue({ id: 99, procedure: 'Crown' });
        mockCreateLabOrder.mockRejectedValue(new Error('Lab service unavailable'));

        const { result } = renderHook(
            () =>
                useTreatmentOperations({
                    patientId: 101,
                    refetchHistory,
                    refetchTeeth,
                    refetchWorkspace,
                    setIsTreatmentSheetOpen,
                    setEditingTreatmentId,
                    editingTreatmentId: null,
                    selectedToothCondition: null,
                }),
            { wrapper: createWrapper() }
        );

        let saved = null;
        await act(async () => {
            saved = await result.current.handleSaveTreatment({
                procedure: 'Crown',
                tooth_number: '16',
                cost: 1200,
                lab_order: {
                    laboratory_id: 5,
                    shade: 'A2',
                    material: 'Zirconia',
                    cost: 300,
                },
            });
        });

        expect(mockCreateTreatment).toHaveBeenCalledTimes(1);
        expect(mockCreateLabOrder).toHaveBeenCalledWith(expect.objectContaining({
            patient_id: 101,
            treatment_id: 99,
            laboratory_id: 5,
            work_type: 'Crown',
            tooth_number: '16',
            shade: 'A2',
            material: 'Zirconia',
            cost: 300,
        }));
        expect(saved).toEqual({ id: 99, procedure: 'Crown' });
        expect(toast.error).toHaveBeenCalledWith('patient_details.alerts.treatment_saved_lab_failed');
        expect(toast.success).not.toHaveBeenCalled();
        expect(setIsTreatmentSheetOpen).toHaveBeenCalledWith(false);
        expect(refetchHistory).toHaveBeenCalledTimes(1);
    });

    it('existing-order response (is_existing: true) shows info message', async () => {
        mockCreateTreatment.mockResolvedValue({ id: 99, procedure: 'Crown' });
        mockCreateLabOrder.mockResolvedValue({ data: { id: 201, is_existing: true } });

        const { result } = renderHook(
            () =>
                useTreatmentOperations({
                    patientId: 101,
                    refetchHistory,
                    refetchTeeth,
                    refetchWorkspace,
                    setIsTreatmentSheetOpen,
                    setEditingTreatmentId,
                    editingTreatmentId: null,
                    selectedToothCondition: null,
                }),
            { wrapper: createWrapper() }
        );

        await act(async () => {
            await result.current.handleSaveTreatment({
                procedure: 'Crown',
                tooth_number: '16',
                cost: 1200,
                lab_order: {
                    laboratory_id: 5,
                },
            });
        });

        expect(mockCreateTreatment).toHaveBeenCalledTimes(1);
        expect(mockCreateLabOrder).toHaveBeenCalledTimes(1);
        expect(toast.info).toHaveBeenCalledWith('patient_details.alerts.lab_order_already_exists');
        expect(toast.success).toHaveBeenCalledWith('patient_details.alerts.treatment_save_success');
        expect(toast.error).not.toHaveBeenCalled();
    });

    it('normal success shows no extra message (only success toast)', async () => {
        mockCreateTreatment.mockResolvedValue({ id: 99, procedure: 'Crown' });
        mockCreateLabOrder.mockResolvedValue({ data: { id: 202, is_existing: false } });

        const { result } = renderHook(
            () =>
                useTreatmentOperations({
                    patientId: 101,
                    refetchHistory,
                    refetchTeeth,
                    refetchWorkspace,
                    setIsTreatmentSheetOpen,
                    setEditingTreatmentId,
                    editingTreatmentId: null,
                    selectedToothCondition: null,
                }),
            { wrapper: createWrapper() }
        );

        await act(async () => {
            await result.current.handleSaveTreatment({
                procedure: 'Crown',
                tooth_number: '16',
                cost: 1200,
                lab_order: {
                    laboratory_id: 5,
                },
            });
        });

        expect(mockCreateTreatment).toHaveBeenCalledTimes(1);
        expect(mockCreateLabOrder).toHaveBeenCalledTimes(1);
        expect(toast.info).not.toHaveBeenCalled();
        expect(toast.error).not.toHaveBeenCalled();
        expect(toast.success).toHaveBeenCalledWith('patient_details.alerts.treatment_save_success');
    });
});
