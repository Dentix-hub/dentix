import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import Settings from './Settings';
import * as api from '../api';

vi.mock('../api', () => ({
    getMe: vi.fn(),
    getBackupStatus: vi.fn(),
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
    getPrescriptionHeader: vi.fn().mockResolvedValue({ data: {} }),
    getPriceLists: vi.fn().mockResolvedValue({ data: [] }),
    getInsuranceProviders: vi.fn().mockResolvedValue({ data: [] }),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => fallback || key,
        i18n: { language: 'ar' },
    }),
}));

// Mock Lucide icons
vi.mock('lucide-react', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
    };
});

describe('Settings page - Backup Readiness Integration', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        delete window.location;
        window.location = new URL('http://localhost:3000/settings?tab=backup');
        api.getMe.mockResolvedValue({
            data: {
                id: 1,
                username: 'admin',
                role: 'admin',
                tenant_id: 10,
                tenant: { id: 10, name: 'Clinic A', backup_frequency: 'off' },
            },
        });
    });

    it('disables connect and encrypted download buttons when backend reports unconfigured', async () => {
        api.getBackupStatus.mockResolvedValue({
            data: {
                connected: false,
                connection_status: 'disconnected',
                account_email: null,
                google_configured: false,
                google_unconfigured_reason: 'إعدادات ربط Google غير مكتملة',
                archive_configured: false,
                archive_unconfigured_reason: 'إعدادات النسخ الاحتياطي غير مكتملة',
            },
        });

        render(<Settings />);

        await waitFor(() => {
            expect(api.getBackupStatus).toHaveBeenCalled();
        });

        // The connect button should be disabled with unconfigured reason
        const connectBtn = await screen.findByRole('button', { name: /backup.connect_btn/i });
        expect(connectBtn).toBeDisabled();
        expect(connectBtn).toHaveAttribute('title', 'إعدادات ربط Google غير مكتملة');

        // The encrypted download button should be disabled with unconfigured reason
        const encryptedBtn = await screen.findByRole('button', { name: /backup.encrypted_download/i });
        expect(encryptedBtn).toBeDisabled();
        expect(encryptedBtn).toHaveAttribute('title', 'إعدادات النسخ الاحتياطي غير مكتملة');
    });

    it('enables connect and encrypted download buttons when backend reports configured', async () => {
        api.getBackupStatus.mockResolvedValue({
            data: {
                connected: false,
                connection_status: 'disconnected',
                account_email: null,
                google_configured: true,
                google_unconfigured_reason: null,
                archive_configured: true,
                archive_unconfigured_reason: null,
            },
        });

        render(<Settings />);

        await waitFor(() => {
            expect(api.getBackupStatus).toHaveBeenCalled();
        });

        const connectBtn = await screen.findByRole('button', { name: /backup.connect_btn/i });
        expect(connectBtn).not.toBeDisabled();
        expect(connectBtn).not.toHaveAttribute('title');

        const encryptedBtn = await screen.findByRole('button', { name: /backup.encrypted_download/i });
        expect(encryptedBtn).not.toBeDisabled();
        expect(encryptedBtn).not.toHaveAttribute('title');
    });
});
