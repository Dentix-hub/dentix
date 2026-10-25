import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import QuickTreatmentSheet from '../components/QuickTreatmentSheet';

const getStockSummary = vi.fn();
const getMaterials = vi.fn();
const getActiveSessions = vi.fn();
const getLaboratories = vi.fn();
const getPatientLabOrders = vi.fn();
const addTreatmentSession = vi.fn();

vi.mock('@/api/inventory', () => ({
    getStockSummary: (...args) => getStockSummary(...args),
    getMaterials: (...args) => getMaterials(...args),
    getActiveSessions: (...args) => getActiveSessions(...args),
}));

vi.mock('@/api', () => ({
    getLaboratories: (...args) => getLaboratories(...args),
    getPatientLabOrders: (...args) => getPatientLabOrders(...args),
    addTreatmentSession: (...args) => addTreatmentSession(...args),
    createLabOrder: vi.fn(),
}));

vi.mock('@/features/inventory/components/EnhancedMaterialConsumption', () => ({
    EnhancedMaterialConsumption: ({ isOpen }) => (isOpen ? <div data-testid="smart-material-dialog">Smart materials</div> : null),
}));

vi.mock('@/features/inventory/MaterialConsumptionPanel', () => ({
    default: () => <div data-testid="material-consumption-panel">Material suggestions</div>,
}));

vi.mock('@/features/inventory/components/TrackSessionModal', () => ({
    default: ({ isOpen, stockItem, material }) => (isOpen ? (
        <div data-testid="track-session-dialog">
            {stockItem?.id}:{material?.name}
        </div>
    ) : null),
}));

vi.mock('@/shared/ui', () => ({
    toast: Object.assign(vi.fn(), {
        error: vi.fn(),
        success: vi.fn(),
        dismiss: vi.fn(),
    }),
}));

const initialData = {
    patient_id: 12,
    doctor_id: 4,
    tooth_number: 'UR1',
    diagnosis: 'Decay',
    procedure: 'Cleaning',
    cost: '100',
    discount: '10',
    status: 'Done',
    notes: 'Clinical note',
    canal_count: '',
    canals: [{ name: '', length: '' }],
    sessions: '',
    complications: '',
    consumedMaterials: [],
    default_price_list_id: null,
};

const procedures = [
    {
        id: 5,
        name: 'Cleaning',
        price: 100,
        suggestedMaterials: [],
    },
    {
        id: 12,
        name: 'Crown PFM',
        category: 'prosthodontic',
        price: 1200,
        suggestedMaterials: [],
    },
];

const mockLabs = [
    { id: 101, name: 'Alpha Dental Lab' },
    { id: 102, name: 'Precision Ceramics' },
];

function renderSheet(overrides = {}) {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
        },
    });

    const props = {
        isOpen: true,
        onClose: vi.fn(),
        onSave: vi.fn().mockResolvedValue(undefined),
        initialData,
        isEditing: false,
        procedures,
        selectedToothCondition: 'Healthy',
        setSelectedToothCondition: vi.fn(),
        ...overrides,
    };

    render(
        <QueryClientProvider client={queryClient}>
            <QuickTreatmentSheet {...props} />
        </QueryClientProvider>
    );

    return props;
}

describe('QuickTreatmentSheet Unified Specification (D1–D4 & F1–F10)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        getStockSummary.mockResolvedValue({ data: [] });
        getMaterials.mockResolvedValue({ data: [] });
        getActiveSessions.mockResolvedValue({ data: [] });
        getLaboratories.mockResolvedValue({ data: mockLabs });
        getPatientLabOrders.mockResolvedValue({ data: [] });
        addTreatmentSession.mockResolvedValue({ data: { id: 1, notes: 'Session 1' } });
    });

    it('1. uses the canonical accessible bottom sheet dialog at max-w-3xl width', () => {
        renderSheet();

        const dialog = screen.getByRole('dialog');
        expect(dialog.className).toContain('bg-surface-elevated');
        expect(dialog.className).toContain('max-w-3xl');
        expect(screen.getByText(/تفاصيل السن رقم #UR1/i)).toBeInTheDocument();
        expect(screen.getByLabelText('التشخيص')).toBeInTheDocument();
        expect(screen.getByLabelText('التكلفة')).toBeInTheDocument();
        expect(screen.getByLabelText('الخصم')).toBeInTheDocument();
        expect(screen.getByLabelText('رقم السن')).toBeInTheDocument();
    });

    it('2. preserves the treatment save payload contract after unification', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        renderSheet({ onSave });

        fireEvent.click(screen.getByRole('button', { name: 'حفظ' }));

        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
            patient_id: 12,
            doctor_id: 4,
            tooth_number: 11,
            procedure: 'Cleaning',
            procedure_id: 5,
            cost: 100,
            discount: 10,
            status: 'Done',
            notes: 'Clinical note',
            consumedMaterials: [],
            skip_stock_check: false,
        }));
    });

    it('3. absorbs confirm-open recovery path (CONFIRM_OPEN_REQUIRED) directly without escalating', async () => {
        const onSave = vi.fn().mockRejectedValue({
            response: {
                data: {
                    detail: {
                        code: 'CONFIRM_OPEN_REQUIRED',
                        stock_item_id: 42,
                        material_info: 'Composite A3',
                    },
                },
            },
        });
        renderSheet({ onSave });

        fireEvent.click(screen.getByRole('button', { name: 'حفظ' }));

        const sessionDialog = await screen.findByTestId('track-session-dialog');
        expect(sessionDialog).toHaveTextContent('42:Composite A3');
    });

    it('4. allows selecting surfaces via interactive buttons and sends them in save payload', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        renderSheet({ onSave });

        const surfaceM = screen.getByRole('button', { name: /تحديد السطح M/i });
        const surfaceO = screen.getByRole('button', { name: /تحديد السطح O/i });
        expect(surfaceM).toHaveAttribute('aria-pressed', 'false');
        expect(surfaceO).toHaveAttribute('aria-pressed', 'false');

        fireEvent.click(surfaceM);
        fireEvent.click(surfaceO);

        expect(surfaceM).toHaveAttribute('aria-pressed', 'true');
        expect(surfaceO).toHaveAttribute('aria-pressed', 'true');

        const surfaceInput = screen.getByLabelText('سطح السن (Surface)');
        expect(surfaceInput).toHaveValue('MO');

        fireEvent.click(screen.getByRole('button', { name: 'حفظ' }));

        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
            surface: 'MO',
            surfaces: ['M', 'O'],
            target_kind: 'surface',
        }));
    });

    it('5. normalizes pre-selected surface initialData and enables clearing surfaces', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        renderSheet({
            onSave,
            initialData: {
                ...initialData,
                surface: 'MOD',
            },
        });

        const surfaceInput = screen.getByLabelText('سطح السن (Surface)');
        expect(surfaceInput).toHaveValue('MOD');

        const surfaceM = screen.getByRole('button', { name: /تحديد السطح M/i });
        expect(surfaceM).toHaveAttribute('aria-pressed', 'true');

        const clearBtn = screen.getByRole('button', { name: 'مسح الأسطح' });
        fireEvent.click(clearBtn);

        expect(surfaceInput).toHaveValue('');
        expect(surfaceM).toHaveAttribute('aria-pressed', 'false');

        fireEvent.click(screen.getByRole('button', { name: 'حفظ' }));

        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
            surface: null,
            surfaces: undefined,
            target_kind: 'tooth',
        }));
    });

    it('6. syncs manual surface input with surface pills', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        renderSheet({ onSave });

        const surfaceInput = screen.getByLabelText('سطح السن (Surface)');
        fireEvent.change(surfaceInput, { target: { value: 'ob' } });

        const surfaceO = screen.getByRole('button', { name: /تحديد السطح O/i });
        const surfaceB = screen.getByRole('button', { name: /تحديد السطح B/i });
        expect(surfaceO).toHaveAttribute('aria-pressed', 'true');
        expect(surfaceB).toHaveAttribute('aria-pressed', 'true');

        fireEvent.click(screen.getByRole('button', { name: 'حفظ' }));

        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
            surface: 'OB',
            surfaces: ['O', 'B'],
            target_kind: 'surface',
        }));
    });

    it('7. renders plan item prefill chip and sends clinical_work_item_id in save payload', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        renderSheet({
            onSave,
            initialData: {
                ...initialData,
                prefill_source: 'plan_item',
                clinical_work_item_id: 88,
                plan_title: 'Phase 1 - Restorative',
                work_item_code: 'D2391',
            },
        });

        expect(screen.getByTestId('clinical-link-item-chip')).toBeInTheDocument();
        expect(screen.getByText(/Phase 1 - Restorative/i)).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'حفظ' }));

        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
            clinical_work_item_id: 88,
        }));
    });

    it('8. displays error banner on CLINICAL_LINK rejection and keeps sheet open', async () => {
        const onSave = vi.fn().mockRejectedValue({
            response: {
                data: {
                    detail: 'CLINICAL_LINK_NOT_OPEN',
                },
            },
        });
        const onClose = vi.fn();
        renderSheet({
            onSave,
            onClose,
            initialData: {
                ...initialData,
                prefill_source: 'plan_item',
                clinical_work_item_id: 88,
            },
        });

        fireEvent.click(screen.getByRole('button', { name: 'حفظ' }));

        const banner = await screen.findByTestId('clinical-link-error-banner');
        expect(banner).toBeInTheDocument();
        expect(banner).toHaveTextContent(/This planned item is already completed or closed/i);
        expect(onClose).not.toHaveBeenCalled();
    });

    it('9. renders context header banner when prefill_source is set for chart-driven opens', () => {
        renderSheet({
            initialData: {
                ...initialData,
                prefill_source: 'quick_launcher',
                procedure: 'Cleaning',
                tooth_number: 'UR1',
                surface: 'MO',
            },
        });

        const contextBanner = screen.getByTestId('treatment-modal-context-banner');
        expect(contextBanner).toBeInTheDocument();
        expect(contextBanner).toHaveTextContent('quick_launcher');
        expect(contextBanner).toHaveTextContent('Cleaning');
        expect(contextBanner).toHaveTextContent('#UR1 (MO)');
    });

    it('10. renders localized tooth-status chips in Arabic without hardcoded English labels', () => {
        renderSheet();

        expect(screen.getByRole('button', { name: 'سليم' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'مفقود' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'منطمر' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'غير بازغ' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'جذر متبقي' })).toBeInTheDocument();

        // Must NOT render unlocalized English strings as chips
        expect(screen.queryByRole('button', { name: 'Retained Root' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Unerupted' })).not.toBeInTheDocument();
    });

    it('11. displays condition suggestion and confirms only upon doctor action', async () => {
        renderSheet({
            initialData: {
                ...initialData,
                procedure: 'Crown PFM',
                diagnosis: 'Healthy',
            },
        });

        // Procedure "Crown PFM" suggests Crown
        const banner = await screen.findByTestId('condition-suggestion-banner');
        expect(banner).toBeInTheDocument();
        expect(banner).toHaveTextContent(/الحالة المقترحة:/i);

        const confirmBtn = screen.getByRole('button', { name: 'تأكيد الحالة' });
        fireEvent.click(confirmBtn);

        // After confirmation, banner disappears
        await waitFor(() => {
            expect(screen.queryByTestId('condition-suggestion-banner')).not.toBeInTheDocument();
        });
    });

    it('12. displays lab section when prosthetic procedure is selected and includes lab_order in payload', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        renderSheet({
            onSave,
            initialData: {
                ...initialData,
                procedure: 'Crown PFM',
                cost: '1200',
            },
        });

        expect(await screen.findByText('بيانات المعمل')).toBeInTheDocument();
        expect(screen.getByLabelText('اختر المعمل')).toBeInTheDocument();

        // Select laboratory
        fireEvent.change(screen.getByLabelText('اختر المعمل'), { target: { value: '101' } });
        fireEvent.change(screen.getByLabelText('درجة اللون (Shade)'), { target: { value: 'A2' } });

        fireEvent.click(screen.getByRole('button', { name: 'حفظ' }));

        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
            procedure: 'Crown PFM',
            lab_order: expect.objectContaining({
                laboratory_id: '101',
                shade: 'A2',
            }),
        }));
    });

    it('13. renders sessions list in edit mode and allows recording legacy sessions (D4)', async () => {
        renderSheet({
            isEditing: true,
            initialData: {
                ...initialData,
                id: 99,
                treatment_sessions: [
                    { id: 1, notes: 'First visit prep', created_at: '2026-10-20T10:00:00Z' },
                ],
            },
        });

        expect(await screen.findByText('سجل الجلسات (Sessions)')).toBeInTheDocument();
        expect(screen.getByText('First visit prep')).toBeInTheDocument();

        // Add new session
        fireEvent.click(screen.getByRole('button', { name: 'إضافة جلسة' }));
        const notesInput = screen.getByPlaceholderText('ماذا تم في هذه الجلسة؟');
        fireEvent.change(notesInput, { target: { value: 'Second visit try-in' } });

        fireEvent.click(screen.getByRole('button', { name: 'حفظ الجلسة' }));

        await waitFor(() => {
            expect(addTreatmentSession).toHaveBeenCalledWith(99, expect.objectContaining({
                notes: 'Second visit try-in',
                treatment_id: 99,
            }));
        });
    });

    it('14. reopening sheet in edit mode for prosthetic treatment without linked lab order displays lab section for retry', async () => {
        getPatientLabOrders.mockResolvedValue({ data: [] });
        const onSave = vi.fn().mockResolvedValue(undefined);
        renderSheet({
            isEditing: true,
            onSave,
            initialData: {
                ...initialData,
                id: 88,
                procedure: 'Crown PFM',
                cost: '1200',
            },
        });

        expect(await screen.findByText('بيانات المعمل')).toBeInTheDocument();
        expect(screen.getByLabelText('اختر المعمل')).toBeInTheDocument();

        // Select lab and save again
        fireEvent.change(screen.getByLabelText('اختر المعمل'), { target: { value: '101' } });
        fireEvent.click(screen.getByRole('button', { name: 'حفظ' }));

        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
            id: 88,
            procedure: 'Crown PFM',
            lab_order: expect.objectContaining({
                laboratory_id: '101',
            }),
        }));
    });
});
