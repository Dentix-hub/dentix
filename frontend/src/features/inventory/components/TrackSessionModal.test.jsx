import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TrackSessionModal from './TrackSessionModal';

const openSession = vi.fn();
const closeSession = vi.fn();
const getMaterialStock = vi.fn();

vi.mock('@/api/inventory', () => ({
    openSession: (...args) => openSession(...args),
    closeSession: (...args) => closeSession(...args),
    getMaterialStock: (...args) => getMaterialStock(...args),
}));

function renderDialog(overrides = {}) {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
        },
    });

    const props = {
        isOpen: true,
        onClose: vi.fn(),
        session: null,
        material: { id: 5, name: 'Composite A3' },
        stockItem: { id: 21, name: 'Composite A3' },
        mode: 'OPEN',
        onSuccess: vi.fn(),
        ...overrides,
    };

    render(
        <QueryClientProvider client={queryClient}>
            <TrackSessionModal {...props} />
        </QueryClientProvider>
    );

    return props;
}

describe('TrackSessionModal', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        getMaterialStock.mockResolvedValue({ data: [] });
        openSession.mockResolvedValue({ data: {} });
        closeSession.mockResolvedValue({ data: {} });
    });

    it('renders on the canonical opaque dialog surface', () => {
        renderDialog();

        const dialog = screen.getByRole('dialog');
        expect(dialog.className).toContain('bg-surface-elevated');
        expect(dialog.className).toContain('z-modal');
        expect(screen.getByText('Composite A3')).toBeInTheDocument();
    });

    it('routes canonical close interaction through the existing onClose callback', () => {
        const onClose = vi.fn();
        renderDialog({ onClose });

        fireEvent.click(screen.getByRole('button', { name: /Close|إغلاق/i }));
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
