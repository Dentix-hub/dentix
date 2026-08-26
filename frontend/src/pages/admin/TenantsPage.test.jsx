import { render, screen, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TenantsPage from './TenantsPage';

const apiMocks = vi.hoisted(() => ({
    apiGet: vi.fn(),
    apiPost: vi.fn(),
    apiDelete: vi.fn(),
}));

let currentSearchParams = new URLSearchParams('');
const mockSetSearchParams = vi.fn((params) => {
    if (params instanceof URLSearchParams) {
        currentSearchParams = params;
    } else {
        currentSearchParams = new URLSearchParams(params);
    }
});

vi.mock('react-router-dom', () => ({
    useSearchParams: () => [currentSearchParams, mockSetSearchParams],
}));

vi.mock('@/api', () => ({
    api: {
        get: apiMocks.apiGet,
        post: apiMocks.apiPost,
        delete: apiMocks.apiDelete,
    },
}));

vi.mock('@/utils/logger', () => ({ default: { error: vi.fn() } }));
vi.mock('@/shared/ui', () => ({
    toast: { success: vi.fn(), error: vi.fn() },
    Modal: ({ children, isOpen }) => (isOpen ? <div data-testid="modal">{children}</div> : null),
    ConfirmDialog: ({ children, isOpen }) => (isOpen ? <div data-testid="confirm-dialog">{children}</div> : null),
}));

vi.mock('@/features/admin/SuperAdmin/TenantsManager', () => ({
    default: ({ tenants, onSelectTenant }) => (
        <div data-testid="tenants-manager">
            {tenants.map((t) => (
                <button key={t.id} onClick={() => onSelectTenant(t.id)}>
                    {t.name}
                </button>
            ))}
        </div>
    ),
}));

vi.mock('@/features/admin/SuperAdmin/TenantDetailPanel', () => ({
    default: ({ tenantId, onClose }) =>
        tenantId ? (
            <div data-testid="tenant-detail-panel">
                <span>Selected Tenant: {tenantId}</span>
                <button onClick={onClose}>Close Detail</button>
            </div>
        ) : null,
}));

describe('TenantsPage deep linking and detail query state', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        currentSearchParams = new URLSearchParams('');
        apiMocks.apiGet.mockImplementation((url) => {
            if (url === '/api/v1/admin/tenants') {
                return Promise.resolve({
                    data: [
                        { id: 10, name: 'Clinic Alpha' },
                        { id: 20, name: 'Clinic Beta' },
                    ],
                });
            }
            if (url === '/api/v1/admin/subscriptions/plans') {
                return Promise.resolve({ data: [] });
            }
            return Promise.resolve({ data: [] });
        });
    });

    it('consumes ?id query param on mount and opens TenantDetailPanel', async () => {
        currentSearchParams = new URLSearchParams('id=20');

        render(<TenantsPage />);

        expect(await screen.findByTestId('tenant-detail-panel')).toBeInTheDocument();
        expect(screen.getByText('Selected Tenant: 20')).toBeInTheDocument();
    });

    it('cleans ?id from query params when detail panel is closed', async () => {
        currentSearchParams = new URLSearchParams('id=20');

        render(<TenantsPage />);

        expect(await screen.findByTestId('tenant-detail-panel')).toBeInTheDocument();

        fireEvent.click(screen.getByText('Close Detail'));

        expect(mockSetSearchParams).toHaveBeenCalled();
        expect(screen.queryByTestId('tenant-detail-panel')).not.toBeInTheDocument();
    });
});
