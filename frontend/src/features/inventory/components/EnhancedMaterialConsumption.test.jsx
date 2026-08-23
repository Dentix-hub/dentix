import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { EnhancedMaterialConsumption } from './EnhancedMaterialConsumption';

// The component posts through the shared api client whose response
// interceptor ALREADY unwraps StandardResponse -> res.data is the payload.
const apiPost = vi.fn();
vi.mock('@/api', () => ({
    api: {
        post: (...args) => apiPost(...args),
    },
}));

vi.mock('./SmartMaterialRow', () => ({
    SmartMaterialRow: ({ material }) => (
        <div data-testid="material-row">{material.material_name}</div>
    ),
}));

vi.mock('react-hot-toast', () => ({ default: { error: vi.fn(), success: vi.fn() } }));

function renderModal(overrides = {}) {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    const props = {
        procedure: { name: 'حشو عصب' },
        availableMaterials: [
            { id: 3, name: 'Composite A3', base_unit: 'ml' },
        ],
        initialMaterials: [{ material_id: 3, quantity: 2 }],
        mode: 'smart',
        patientId: 12,
        onSave: vi.fn(),
        onClose: vi.fn(),
        isOpen: true,
        ...overrides,
    };

    render(
        <QueryClientProvider client={queryClient}>
            <EnhancedMaterialConsumption {...props} />
        </QueryClientProvider>
    );

    return props;
}

describe('EnhancedMaterialConsumption stock check contract', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('surfaces CRITICAL and WARNING stock states to the doctor', async () => {
        // Post-interceptor shape: { data: [...] } — NOT nested under .data.data.
        apiPost.mockResolvedValue({
            data: [
                {
                    material_id: 3,
                    material_name: 'Composite A3',
                    status: 'CRITICAL',
                    message: 'Out of stock',
                },
                {
                    material_id: 9,
                    material_name: 'Anesthetic',
                    status: 'WARNING',
                    message: 'Insufficient stock (Available: 0.5)',
                },
                {
                    material_id: 11,
                    material_name: 'Etchant',
                    status: 'OK',
                    message: '',
                },
            ],
        });

        renderModal();

        await waitFor(() => {
            expect(screen.getByText(/Composite A3: Out of stock/)).toBeInTheDocument();
        });
        expect(
            screen.getByText(/Anesthetic: Insufficient stock \(Available: 0\.5\)/)
        ).toBeInTheDocument();
        // OK rows must not produce warning banners
        expect(screen.queryByText(/Etchant/)).not.toBeInTheDocument();
    });

    it('renders no warning banners when every material is OK', async () => {
        apiPost.mockResolvedValue({
            data: [
                { material_id: 3, material_name: 'Composite A3', status: 'OK', message: '' },
            ],
        });

        renderModal();

        await waitFor(() => {
            expect(apiPost).toHaveBeenCalledWith(
                '/api/v1/inventory/smart/check-availability',
                expect.objectContaining({
                    materials: [{ material_id: 3, quantity: 2 }],
                    patient_id: 12,
                })
            );
        });
        await waitFor(() => {
            expect(screen.getByTestId('material-row')).toBeInTheDocument();
        });
        expect(screen.queryByText(/Out of stock/i)).not.toBeInTheDocument();
    });
});
