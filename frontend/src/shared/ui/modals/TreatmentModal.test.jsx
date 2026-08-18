import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TreatmentModal from './TreatmentModal';

const getStockSummary = vi.fn();
const getMaterials = vi.fn();
const getActiveSessions = vi.fn();
const palmerToFdi = vi.fn();

vi.mock('@/api/inventory', () => ({
    getStockSummary: (...args) => getStockSummary(...args),
    getMaterials: (...args) => getMaterials(...args),
    getActiveSessions: (...args) => getActiveSessions(...args),
}));

vi.mock('@/utils/toothUtils', () => ({
    palmerToFdi: (...args) => palmerToFdi(...args),
}));

vi.mock('@/features/inventory/components/EnhancedMaterialConsumption', () => ({
    EnhancedMaterialConsumption: ({ isOpen }) => isOpen ? <div data-testid="smart-material-dialog">Smart materials</div> : null,
}));

vi.mock('@/features/inventory/MaterialConsumptionPanel', () => ({
    default: () => <div data-testid="material-consumption-panel">Material suggestions</div>,
}));

vi.mock('@/features/inventory/components/TrackSessionModal', () => ({
    default: ({ isOpen, stockItem, material }) => isOpen ? (
        <div data-testid="track-session-dialog">
            {stockItem?.id}:{material?.name}
        </div>
    ) : null,
}));

vi.mock('../components/MultiSessionPanel', () => ({
    MultiSessionPanel: () => <div data-testid="multi-session-panel">Sessions</div>,
}));

vi.mock('@/api', () => ({
    addTreatmentSession: vi.fn(),
}));

vi.mock('react-hot-toast', () => ({
    default: Object.assign(vi.fn(), {
        error: vi.fn(),
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

const procedures = [{
    id: 5,
    name: 'Cleaning',
    price: 100,
    suggestedMaterials: [],
}];

function renderTreatmentModal(overrides = {}) {
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
            <TreatmentModal {...props} />
        </QueryClientProvider>
    );

    return props;
}

describe('TreatmentModal', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        getStockSummary.mockResolvedValue({ data: [] });
        getMaterials.mockResolvedValue({ data: [] });
        getActiveSessions.mockResolvedValue([]);
        palmerToFdi.mockReturnValue(11);
    });

    it('uses the canonical accessible dialog at a clinical-workspace width', () => {
        renderTreatmentModal();

        const dialog = screen.getByRole('dialog');
        expect(dialog.className).toContain('bg-surface-elevated');
        expect(dialog.className).toContain('max-w-3xl');
        expect(screen.getByText('تفاصيل السن رقم #UR1')).toBeInTheDocument();
        expect(screen.getByLabelText('التشخيص')).toBeInTheDocument();
        expect(screen.getByLabelText('التكلفة')).toBeInTheDocument();
        expect(screen.getByLabelText('الخصم')).toBeInTheDocument();
        expect(screen.getByLabelText('رقم السن')).toBeInTheDocument();
    });

    it('preserves the treatment save payload contract after the shell migration', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        renderTreatmentModal({ onSave });

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

    it('preserves the confirm-open recovery path for treatment stock conflicts', async () => {
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
        renderTreatmentModal({ onSave });

        fireEvent.click(screen.getByRole('button', { name: 'حفظ' }));

        const sessionDialog = await screen.findByTestId('track-session-dialog');
        expect(sessionDialog).toHaveTextContent('42:Composite A3');
    });
});
