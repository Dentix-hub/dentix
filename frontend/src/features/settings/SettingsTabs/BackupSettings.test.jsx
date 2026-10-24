import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BackupSettings from './BackupSettings';
import * as api from '@/api';

vi.mock('@/api', () => ({
    exportTenantBackup: vi.fn(),
    exportTenantBackupXlsx: vi.fn(),
    uploadBackup: vi.fn(),
    purgeDeletedPatients: vi.fn(),
    getGoogleAuthUrl: vi.fn(),
    triggerManualBackup: vi.fn(),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
    }),
}));

describe('BackupSettings - Excel Export', () => {
    const mockBackupStatus = { connected: false, loading: false };
    const mockCurrentUser = {
        tenant_id: 1,
        tenant: { name: 'Alpha Clinic', last_backup_at: null },
    };
    const mockSetMessage = vi.fn();
    const mockLoadUserInfo = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        window.URL.createObjectURL = vi.fn(() => 'blob:http://localhost/dummy');
        window.URL.revokeObjectURL = vi.fn();
    });

    it('renders the Export to Excel button', () => {
        render(
            <BackupSettings
                backupStatus={mockBackupStatus}
                currentUser={mockCurrentUser}
                setMessage={mockSetMessage}
                loadUserInfo={mockLoadUserInfo}
            />
        );

        const btn = screen.getByTestId('export-excel-button');
        expect(btn).toBeInTheDocument();
        expect(btn).toHaveTextContent('backup.export_excel_btn');
    });

    it('triggers Excel export and displays loading and success messages', async () => {
        api.exportTenantBackupXlsx.mockResolvedValueOnce({
            data: new Uint8Array([1, 2, 3]),
            headers: {
                'content-disposition': 'attachment; filename="dentix-backup-alpha_clinic-2026-10-24.xlsx"',
            },
        });

        render(
            <BackupSettings
                backupStatus={mockBackupStatus}
                currentUser={mockCurrentUser}
                setMessage={mockSetMessage}
                loadUserInfo={mockLoadUserInfo}
            />
        );

        const btn = screen.getByTestId('export-excel-button');
        fireEvent.click(btn);

        expect(mockSetMessage).toHaveBeenCalledWith({
            type: 'info',
            text: 'backup.export_excel_loading',
        });

        await waitFor(() => {
            expect(api.exportTenantBackupXlsx).toHaveBeenCalledTimes(1);
            expect(mockSetMessage).toHaveBeenCalledWith({
                type: 'success',
                text: 'backup.export_excel_success',
            });
        });
    });

    it('handles export failure gracefully', async () => {
        api.exportTenantBackupXlsx.mockRejectedValueOnce({
            response: { data: { detail: 'Export error' } },
        });

        render(
            <BackupSettings
                backupStatus={mockBackupStatus}
                currentUser={mockCurrentUser}
                setMessage={mockSetMessage}
                loadUserInfo={mockLoadUserInfo}
            />
        );

        const btn = screen.getByTestId('export-excel-button');
        fireEvent.click(btn);

        await waitFor(() => {
            expect(mockSetMessage).toHaveBeenCalledWith({
                type: 'error',
                text: 'Export error',
            });
        });
    });
});
