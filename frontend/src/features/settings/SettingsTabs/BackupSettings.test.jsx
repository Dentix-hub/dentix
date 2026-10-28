import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BackupSettings from './BackupSettings';
import * as api from '@/api';

vi.mock('@/api', () => ({
    exportTenantBackup: vi.fn(),
    exportTenantBackupXlsx: vi.fn(),
    uploadBackup: vi.fn(),
    downloadClinicArchive: vi.fn(),
    previewClinicRestore: vi.fn(),
    confirmClinicRestore: vi.fn(),
    getClinicRestoreStatus: vi.fn(),
    purgeDeletedPatients: vi.fn(),
    getGoogleAuthUrl: vi.fn(),
    triggerManualBackup: vi.fn(),
    listDriveBackups: vi.fn(),
    previewDriveBackup: vi.fn(),
    disconnectGoogleDrive: vi.fn(),
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

    it('previews before confirmation and submits current credentials', async () => {
        api.previewClinicRestore.mockResolvedValueOnce({ data: {
            operation_id: 'operation-1', confirmation: 'token', archive_digest: 'digest',
            counts: { patients: 2 }, backup_date: '2026-01-01', legacy_unverified: true, missing_sections: ['material_sessions'],
        } });
        api.confirmClinicRestore.mockResolvedValueOnce({ data: { operation_id: 'operation-1', status: 'confirmed' } });
        render(<BackupSettings backupStatus={mockBackupStatus} currentUser={mockCurrentUser} setMessage={mockSetMessage} loadUserInfo={mockLoadUserInfo} />);
        const file = new File(['synthetic'], 'clinic.dentix', { type: 'application/octet-stream' });
        fireEvent.change(screen.getByLabelText('backup.restore_btn'), { target: { files: [file] } });
        expect(await screen.findByText('backup.legacy_unverified')).toBeInTheDocument();
        expect(api.confirmClinicRestore).not.toHaveBeenCalled();
        fireEvent.change(screen.getByLabelText('backup.confirm_password'), { target: { value: 'synthetic-password' } });
        fireEvent.click(screen.getByRole('button', { name: 'backup.confirm_restore' }));
        await waitFor(() => expect(api.confirmClinicRestore).toHaveBeenCalledWith({
            operation_id: 'operation-1', confirmation: 'token', archive_digest: 'digest', password: 'synthetic-password',
        }));
        expect(await screen.findByText(/backup.operation_confirmed/)).toBeInTheDocument();
    });

    it('shows a queued backup until the operation reports completion', async () => {
        api.triggerManualBackup.mockResolvedValueOnce({ data: { operation_id: 'backup-1', status: 'queued' } });
        api.getClinicRestoreStatus.mockResolvedValueOnce({ data: { operation_id: 'backup-1', status: 'completed' } });
        render(<BackupSettings backupStatus={{ connected: true, loading: false }} currentUser={mockCurrentUser} setMessage={mockSetMessage} loadUserInfo={mockLoadUserInfo} />);
        fireEvent.click(screen.getByRole('button', { name: 'backup.backup_now' }));
        expect(await screen.findByText(/backup.operation_queued/)).toBeInTheDocument();
        expect(mockSetMessage).not.toHaveBeenCalledWith({ type: 'success', text: 'backup.backup_success' });
        fireEvent.click(screen.getByRole('button', { name: 'backup.refresh_status' }));
        await waitFor(() => expect(mockSetMessage).toHaveBeenCalledWith({ type: 'success', text: 'backup.backup_success' }));
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

    it('unpacks Blob error responses to extract detail and status for JSON backup download', async () => {
        const errorBlob = new Blob([JSON.stringify({ detail: 'Tenant export crashed' })], {
            type: 'application/json',
        });
        api.exportTenantBackup.mockRejectedValueOnce({
            response: { status: 500, data: errorBlob },
        });

        render(
            <BackupSettings
                backupStatus={mockBackupStatus}
                currentUser={mockCurrentUser}
                setMessage={mockSetMessage}
                loadUserInfo={mockLoadUserInfo}
            />
        );

        const btn = screen.getByText(/backup.download_btn/i);
        fireEvent.click(btn);

        await waitFor(() => {
            expect(mockSetMessage).toHaveBeenCalledWith({
                type: 'error',
                text: 'Tenant export crashed (500)',
            });
        });
    });

    it('unpacks Blob error responses for Excel backup export', async () => {
        const errorBlob = new Blob([JSON.stringify({ detail: 'Excel export crashed' })], {
            type: 'application/json',
        });
        api.exportTenantBackupXlsx.mockRejectedValueOnce({
            response: { status: 502, data: errorBlob },
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
                text: 'Excel export crashed (502)',
            });
        });
    });

    it('falls back to localized default message when Blob error response contains no detail', async () => {
        const errorBlob = new Blob(['not-json'], {
            type: 'text/plain',
        });
        api.exportTenantBackup.mockRejectedValueOnce({
            response: { status: 503, data: errorBlob },
        });

        render(
            <BackupSettings
                backupStatus={mockBackupStatus}
                currentUser={mockCurrentUser}
                setMessage={mockSetMessage}
                loadUserInfo={mockLoadUserInfo}
            />
        );

        const btn = screen.getByText(/backup.download_btn/i);
        fireEvent.click(btn);

        await waitFor(() => {
            expect(mockSetMessage).toHaveBeenCalledWith({
                type: 'error',
                text: 'not-json (503)',
            });
        });
    });

    it('disables google connect button and displays unconfigured reason when google_configured is false', () => {
        render(
            <BackupSettings
                backupStatus={{
                    connected: false,
                    loading: false,
                    google_configured: false,
                    google_unconfigured_reason: 'إعدادات ربط Google غير مكتملة',
                }}
                currentUser={mockCurrentUser}
                setMessage={mockSetMessage}
                loadUserInfo={mockLoadUserInfo}
            />
        );

        const connectBtn = screen.getByRole('button', { name: 'backup.connect_btn' });
        expect(connectBtn).toBeDisabled();
        expect(screen.getByText('إعدادات ربط Google غير مكتملة')).toBeInTheDocument();
    });

    it('extracts backend error detail safely when getGoogleAuthUrl fails', async () => {
        api.getGoogleAuthUrl.mockRejectedValueOnce({
            response: {
                status: 400,
                data: { detail: 'إعدادات ربط Google غير مكتملة' },
            },
        });

        render(
            <BackupSettings
                backupStatus={{ connected: false, loading: false, google_configured: true }}
                currentUser={mockCurrentUser}
                setMessage={mockSetMessage}
                loadUserInfo={mockLoadUserInfo}
            />
        );

        const connectBtn = screen.getByRole('button', { name: 'backup.connect_btn' });
        fireEvent.click(connectBtn);

        await waitFor(() => {
            expect(mockSetMessage).toHaveBeenCalledWith({
                type: 'error',
                text: 'إعدادات ربط Google غير مكتملة (400)',
            });
        });
    });

    it('disables encrypted download button and displays unconfigured reason when archive_configured is false', () => {
        render(
            <BackupSettings
                backupStatus={{
                    connected: false,
                    loading: false,
                    archive_configured: false,
                    archive_unconfigured_reason: 'مفتاح تشفير النسخ الاحتياطي غير صالح',
                }}
                currentUser={mockCurrentUser}
                setMessage={mockSetMessage}
                loadUserInfo={mockLoadUserInfo}
            />
        );

        const encryptedBtn = screen.getByText('backup.encrypted_download').closest('button');
        expect(encryptedBtn).toBeDisabled();
        expect(screen.getByText('مفتاح تشفير النسخ الاحتياطي غير صالح')).toBeInTheDocument();
    });
});
