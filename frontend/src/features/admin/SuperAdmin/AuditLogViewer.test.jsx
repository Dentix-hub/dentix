import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import AuditLogViewer from './AuditLogViewer';
import { api } from '@/api';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, options) => {
            if (options && options.count !== undefined) return `${options.count} / ${options.total}`;
            return key;
        },
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/api', () => ({
    api: {
        get: vi.fn(),
    },
}));

vi.mock('@/shared/ui', () => ({
    DateTimePicker: ({ value, onChange }) => (
        <input
            data-testid="date-picker"
            value={value || ''}
            onChange={onChange}
        />
    ),
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

describe('AuditLogViewer MS-08', () => {
    const mockTenants = [
        { id: 101, name: 'Dental Care Clinic', clinic_name: 'Dental Care Clinic' },
        { id: 102, name: 'Al-Amal Center', clinic_name: 'Al-Amal Center' },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('maps tenant_id to tenant name and shows System Global when tenant_id is null', async () => {
        api.get.mockResolvedValueOnce({
            data: {
                data: {
                    logs: [
                        {
                            id: 1,
                            created_at: '2026-08-20T10:00:00Z',
                            performed_by_username: 'admin1',
                            tenant_id: 101,
                            action: 'update',
                            entity_type: 'Patient',
                            entity_id: '501',
                            details: 'Updated patient chart',
                        },
                        {
                            id: 2,
                            created_at: '2026-08-20T11:00:00Z',
                            performed_by_username: 'super_admin',
                            tenant_id: null,
                            action: 'create',
                            entity_type: 'Tenant',
                            entity_id: '102',
                            details: 'Created new tenant',
                        },
                    ],
                    total: 2,
                    pages: 1,
                    current_page: 1,
                },
            },
        });

        render(<AuditLogViewer tenants={mockTenants} />);

        await waitFor(() => {
            expect(screen.getAllByText('Dental Care Clinic').length).toBeGreaterThanOrEqual(1);
            expect(screen.getByText('super_admin.audit.system_global')).toBeInTheDocument();
        });
    });


    it('renders error state on fetch failure separate from empty results', async () => {
        api.get.mockRejectedValueOnce(new Error('Network error'));

        render(<AuditLogViewer tenants={mockTenants} />);

        await waitFor(() => {
            expect(screen.getByText('Network error')).toBeInTheDocument();
            expect(screen.queryByText('super_admin.audit.no_results_found')).not.toBeInTheDocument();
        });
    });

    it('handles export CSV and revokes object URL', async () => {
        api.get.mockResolvedValueOnce({
            data: {
                data: { logs: [], total: 0, pages: 0, current_page: 1 },
            },
        });

        api.get.mockResolvedValueOnce({
            data: 'ID,Action,Entity\n1,create,Tenant #1',
        });

        const createObjectURLSpy = vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:http://localhost/mock-csv');
        const revokeObjectURLSpy = vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {});

        render(<AuditLogViewer tenants={mockTenants} />);

        await waitFor(() => {
            expect(screen.getByText('super_admin.audit.export_csv')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('super_admin.audit.export_csv'));

        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith(
                expect.stringContaining('/api/v1/admin/system/audit-logs/export'),
                expect.objectContaining({ responseType: 'blob' })
            );
            expect(createObjectURLSpy).toHaveBeenCalled();
            expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:http://localhost/mock-csv');
        });
    });
});
