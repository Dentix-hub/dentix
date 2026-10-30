import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Database, Upload, Download, AlertTriangle, FileSpreadsheet } from 'lucide-react';
import * as api from '@/api';
const BackupSettings = ({ backupStatus, currentUser, setMessage, loadUserInfo, refreshBackupStatus }) => {
    const { t } = useTranslation();
    const [restoring, setRestoring] = useState(false);
    const [exportingXlsx, setExportingXlsx] = useState(false);
    const [restorePreview, setRestorePreview] = useState(null);
    const [restorePassword, setRestorePassword] = useState('');
    const [restoreOperation, setRestoreOperation] = useState(null);
    const [backupOperation, setBackupOperation] = useState(null);
    const [driveBackups, setDriveBackups] = useState([]);
    const [nextPage, setNextPage] = useState(null);
    const backupRequestKey = useRef(null);

    const readBlobText = async (blob) => {
        if (typeof blob?.text === 'function') {
            return await blob.text();
        }
        if (typeof FileReader !== 'undefined') {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = () => reject(reader.error);
                reader.readAsText(blob);
            });
        }
        if (typeof Response !== 'undefined') {
            try {
                return await new Response(blob).text();
            } catch {
                // ignore
            }
        }
        return '';
    };

    const extractErrorMessage = async (err, fallbackText) => {
        let detail = '';
        const status = err?.response?.status;
        const data = err?.response?.data;

        if (data instanceof Blob || (data && typeof data.text === 'function')) {
            try {
                const text = await readBlobText(data);
                const parsed = JSON.parse(text);
                detail = parsed.detail || parsed.message || text;
            } catch {
                try {
                    const text = await readBlobText(data);
                    if (text && text.length < 300) detail = text;
                } catch {
                    // ignore
                }
            }
        } else if (data && typeof data === 'object') {
            detail = data.detail || data.message || '';
        } else if (typeof data === 'string') {
            try {
                const parsed = JSON.parse(data);
                detail = parsed.detail || parsed.message || data;
            } catch {
                detail = data;
            }
        } else if (err?.message) {
            detail = err.message;
        }

        if (detail) {
            return status ? `${detail} (${status})` : detail;
        }
        return status ? `${fallbackText} (${status})` : fallbackText;
    };

    const handleExportXlsx = async () => {
        try {
            setExportingXlsx(true);
            setMessage({ type: 'info', text: t('backup.export_excel_loading') });
            const response = await api.exportTenantBackupXlsx();
            const blob = new Blob([response.data], {
                type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;

            let filename = '';
            const disposition = response.headers?.['content-disposition'];
            if (disposition) {
                const match = disposition.match(/filename="?([^"]+)"?/);
                if (match && match[1]) filename = match[1];
            }
            if (!filename) {
                const tenantName = currentUser?.tenant?.name || `tenant_${currentUser?.tenant_id || 'backup'}`;
                const slug = tenantName.toLowerCase().replace(/[^a-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '') || 'backup';
                const today = new Date().toISOString().split('T')[0];
                filename = `dentix-backup-${slug}-${today}.xlsx`;
            }

            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            setMessage({ type: 'success', text: t('backup.export_excel_success') });
        } catch (err) {
            const msg = await extractErrorMessage(err, t('backup.export_excel_fail'));
            setMessage({ type: 'error', text: msg });
        } finally {
            setExportingXlsx(false);
        }
    };
    const handleDownload = async () => {
        try {
            const response = await api.exportTenantBackup();
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            const timestamp = new Date().toISOString().split('T')[0];
            link.setAttribute('download', `clinic_backup_${timestamp}.json`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            const msg = await extractErrorMessage(err, t('backup.download_fail', 'فشل تحميل النسخة الاحتياطية'));
            setMessage({ type: 'error', text: msg });
        }
    };
    const handleEncryptedDownload = async () => {
        try {
            const response = await api.downloadClinicArchive();
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.download = `dentix-clinic-${new Date().toISOString().split('T')[0]}.dentix`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            setMessage({ type: 'error', text: await extractErrorMessage(err, t('backup.download_fail')) });
        }
    };
    const handleUpload = async (e) => {
        const file = e.target.files[0];
        e.target.value = '';
        if (!file) return;
        try {
            setRestoring(true);
            setRestorePreview(null);
            setRestoreOperation(null);
            const response = await api.previewClinicRestore(file);
            setRestorePreview(response.data);
        } catch (err) {
            setMessage({ type: 'error', text: await extractErrorMessage(err, t('backup.restore_fail')) });
        } finally {
            setRestoring(false);
        }
    };
    const handleConfirmRestore = async (event) => {
        event.preventDefault();
        if (!restorePreview || !restorePassword) return;
        try {
            setRestoring(true);
            const response = await api.confirmClinicRestore({
                operation_id: restorePreview.operation_id,
                confirmation: restorePreview.confirmation,
                archive_digest: restorePreview.archive_digest,
                password: restorePassword,
            });
            setRestoreOperation(response.data);
            setRestorePreview(null);
            setMessage({ type: 'info', text: t('backup.restore_queued') });
        } catch (err) {
            setMessage({ type: 'error', text: await extractErrorMessage(err, t('backup.restore_fail')) });
        } finally {
            setRestorePassword('');
            setRestoring(false);
        }
    };
    const refreshRestoreStatus = async () => {
        try {
            const response = await api.getClinicRestoreStatus(restoreOperation.operation_id);
            const operation = response.data;
            setRestoreOperation(operation);
            if (operation.status === 'completed') {
                setMessage({ type: 'success', text: t('backup.restore_completed') });
                loadUserInfo?.();
            } else if (['failed', 'expired'].includes(operation.status)) {
                setMessage({ type: 'error', text: t('backup.restore_failed_safe') });
            }
        } catch (err) {
            setMessage({ type: 'error', text: await extractErrorMessage(err, t('backup.restore_fail')) });
        }
    };
    const handleDriveBackup = async () => {
        try {
            if (!backupRequestKey.current) backupRequestKey.current = globalThis.crypto.randomUUID();
            const response = await api.triggerManualBackup(backupRequestKey.current);
            setBackupOperation(response.data);
            setMessage({ type: 'info', text: t('backup.backup_queued') });
        } catch (err) {
            setMessage({ type: 'error', text: await extractErrorMessage(err, t('backup.backup_failed')) });
        }
    };
    const refreshBackupOperation = async () => {
        try {
            const response = await api.getClinicRestoreStatus(backupOperation.operation_id);
            setBackupOperation(response.data);
            if (['completed', 'failed', 'expired'].includes(response.data.status)) backupRequestKey.current = null;
            if (response.data.status === 'completed') setMessage({ type: 'success', text: t('backup.backup_success') });
            if (response.data.status === 'failed') setMessage({ type: 'error', text: response.data.message || t('backup.backup_failed') });
        } catch (err) {
            setMessage({ type: 'error', text: await extractErrorMessage(err, t('backup.backup_failed')) });
        }
    };
    const loadDriveBackups = async (pageToken = null) => {
        try {
            const response = await api.listDriveBackups(pageToken);
            setDriveBackups((previous) => pageToken ? [...previous, ...response.data.files] : response.data.files);
            setNextPage(response.data.next_page_token);
        } catch (err) {
            setMessage({ type: 'error', text: await extractErrorMessage(err, t('backup.list_failed')) });
        }
    };
    const previewRemoteBackup = async (id) => {
        try {
            setRestoring(true);
            const response = await api.previewDriveBackup(id);
            setRestorePreview(response.data);
            setRestoreOperation(null);
        } catch (err) {
            setMessage({ type: 'error', text: await extractErrorMessage(err, t('backup.restore_fail')) });
        } finally {
            setRestoring(false);
        }
    };
    const handlePurge = async () => {
        if (!window.confirm(t('backup.danger_zone.purge_confirm'))) return;
        try {
            await api.purgeDeletedPatients(currentUser.tenant_id);
            setMessage({ type: 'success', text: t('backup.danger_zone.purge_success') });
        } catch (err) {
            const msg = await extractErrorMessage(err, t('backup.purge_fail', 'فشل تنفيذ العملية'));
            setMessage({ type: 'error', text: msg });
        }
    };
    return (
        <div className="space-y-8">
            {/* Google Drive */}
            <div className="space-y-4">
                <h3 className="font-bold text-lg flex items-center gap-2 text-slate-700 dark:text-slate-200">
                    <div className="p-2 bg-blue-100 text-blue-600 rounded-lg"><Database size={20} /></div>
                    {t('backup.cloud_title')}
                </h3>
                <div className={`p-6 rounded-2xl border ${backupStatus.connected ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-200'}`}>
                    <div className="flex justify-between items-center mb-4">
                        <div>
                            <p className="font-bold text-slate-800">{t('backup.status_label')}</p>
                            <p className={`text-sm ${backupStatus.connected ? 'text-emerald-600' : 'text-slate-500'}`}>
                                {backupStatus.loading ? t('backup.checking') : (backupStatus.connected ? t('backup.connected') : (backupStatus.connectionStatus === 'needs_reconnect' ? t('backup.needs_reconnect') : t('backup.disconnected')))}
                            </p>
                            {backupStatus.accountEmail && <p className="text-sm">{backupStatus.accountEmail}</p>}
                        </div>
                        {backupStatus.connected && <button type="button" onClick={async () => {
                            try {
                                await api.disconnectGoogleDrive();
                                await refreshBackupStatus?.();
                                setMessage({ type: 'success', text: t('backup.disconnect_done') });
                            } catch (err) {
                                setMessage({ type: 'error', text: await extractErrorMessage(err, t('backup.disconnect_failed')) });
                            }
                        }} className="rounded-xl border px-4 py-2 font-bold">{t('backup.disconnect_btn')}</button>}
                        {!backupStatus.connected && !backupStatus.loading && (
                            <div className="flex flex-col items-end gap-1">
                                <button
                                    onClick={async () => {
                                        try {
                                            const res = await api.getGoogleAuthUrl();
                                            window.location.href = res.data.url;
                                        } catch (err) {
                                            setMessage({
                                                type: 'error',
                                                text: await extractErrorMessage(err, t('backup.connect_fail', 'فشل الاتصال')),
                                            });
                                        }
                                    }}
                                    disabled={backupStatus.google_configured === false}
                                    title={backupStatus.google_configured === false ? (backupStatus.google_unconfigured_reason || t('backup.google_not_configured')) : undefined}
                                    className={`px-6 py-2 rounded-xl font-bold transition ${
                                        backupStatus.google_configured === false
                                            ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                                            : 'bg-blue-600 text-white hover:bg-blue-700'
                                    }`}
                                >
                                    {t('backup.connect_btn')}
                                </button>
                                {backupStatus.google_configured === false && (
                                    <span className="text-xs text-amber-600 font-medium max-w-xs text-end">
                                        {backupStatus.google_unconfigured_reason || t('backup.google_not_configured', 'إعدادات ربط Google غير مكتملة')}
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                    <p className="mb-3 text-sm">{t('backup.google_ownership')}</p>
                    <p className="mb-3 text-sm">{t('backup.disconnect_explanation')}</p>
                    {backupStatus.connected && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-200/50">
                            <div>
                                <label className="text-sm font-bold text-slate-600">{t('backup.auto_backup_label')}</label>
                                {/* Automatic backups are NOT executed by the backend yet
                                    (HIGH-12); the control is disabled to avoid a false promise. */}
                                <select
                                    defaultValue={currentUser?.tenant?.backup_frequency || 'off'}
                                    disabled
                                    title={t('backup.auto_not_available', 'النسخ الاحتياطي التلقائي غير متوفر حالياً')}
                                    className="w-full mt-2 p-3 bg-slate-100 border border-slate-200 rounded-xl text-slate-400 cursor-not-allowed"
                                >
                                    <option value="off">{t('backup.off')}</option>
                                    <option value="daily">{t('backup.daily')}</option>
                                    <option value="weekly">{t('backup.weekly')}</option>
                                    <option value="monthly">{t('backup.monthly')}</option>
                                </select>
                                <p className="text-xs text-slate-500 mt-1">
                                    {t('backup.auto_not_available_hint', 'النسخ التلقائي غير متوفر بعد — استخدم زر النسخ اليدوي.')}
                                </p>
                            </div>
                            <div className="flex items-end">
                                <button
                                    onClick={handleDriveBackup}
                                    className="w-full py-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 text-center"
                                >
                                    {t('backup.backup_now')}
                                </button>
                            </div>
                            {backupOperation && <div className="md:col-span-2" role="status">
                                <span>{t('backup.operation_status')}: {t(`backup.operation_${backupOperation.status}`)}</span>
                                <button type="button" onClick={refreshBackupOperation} className="ms-3 rounded border px-3 py-2">{t('backup.refresh_status')}</button>
                            </div>}
                            <div className="md:col-span-2">
                                <button type="button" onClick={() => loadDriveBackups()} className="rounded border px-3 py-2">{t('backup.list_drive')}</button>
                                <ul>{driveBackups.map((file) => <li key={file.id} className="mt-2 flex flex-wrap items-center gap-2"><span>{file.name} — {file.date} — {file.size}</span><button type="button" disabled={restoring} onClick={() => previewRemoteBackup(file.id)} className="rounded border px-3 py-1">{t('backup.preview_title')}</button></li>)}</ul>
                                {nextPage && <button type="button" onClick={() => loadDriveBackups(nextPage)} className="mt-2 rounded border px-3 py-2">{t('backup.more_files')}</button>}
                            </div>
                            {currentUser?.tenant?.last_backup_at && (
                                <p className="md:col-span-2 text-xs text-slate-500 text-center">
                                    {t('backup.curr_backup')} {new Date(currentUser.tenant.last_backup_at + "Z").toLocaleString('ar-EG')}
                                </p>
                            )}
                        </div>
                    )}
                </div>
            </div>
            {/* Local Backup */}
            <div className="space-y-4 pt-6 border-t dark:border-white/10">
                <h3 className="font-bold text-lg flex items-center gap-2 text-slate-700 dark:text-slate-200">
                    <div className="p-2 bg-amber-100 text-amber-600 rounded-lg"><Upload size={20} /></div>
                    {t('backup.local_title')}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                    <button
                        type="button"
                        onClick={handleEncryptedDownload}
                        disabled={backupStatus.archive_configured === false}
                        title={backupStatus.archive_configured === false ? (backupStatus.archive_unconfigured_reason || t('backup.archive_not_configured')) : undefined}
                        className={`p-6 border-2 border-dashed rounded-2xl transition flex flex-col items-center gap-3 ${
                            backupStatus.archive_configured === false
                                ? 'border-slate-200 bg-slate-50 text-slate-400 opacity-60 cursor-not-allowed'
                                : 'border-blue-200 hover:bg-blue-50 text-blue-700'
                        }`}
                    >
                        <Download className={backupStatus.archive_configured === false ? 'text-slate-400' : 'text-blue-600'} size={32} />
                        <span className="font-bold">{t('backup.encrypted_download')}</span>
                        {backupStatus.archive_configured === false && (
                            <span className="text-[11px] text-amber-600 text-center font-medium">
                                {backupStatus.archive_unconfigured_reason || t('backup.archive_not_configured', 'إعدادات النسخ غير مكتملة')}
                            </span>
                        )}
                    </button>
                    <button type="button" onClick={handleDownload} className="p-6 border-2 border-slate-200 border-dashed rounded-2xl hover:bg-slate-50 transition flex flex-col items-center gap-3">
                        <Download className="text-slate-500" size={32} />
                        <span className="font-bold text-slate-600">{t('backup.download_btn')} (.json)</span>
                    </button>
                    <button
                        type="button"
                        onClick={handleExportXlsx}
                        disabled={exportingXlsx}
                        data-testid="export-excel-button"
                        className="p-6 border-2 border-emerald-200 border-dashed rounded-2xl hover:bg-emerald-50/50 transition flex flex-col items-center gap-3 disabled:opacity-50"
                    >
                        {exportingXlsx ? (
                            <div className="animate-spin h-8 w-8 border-4 border-emerald-500 border-t-transparent rounded-full" />
                        ) : (
                            <FileSpreadsheet className="text-emerald-600" size={32} />
                        )}
                        <span className="font-bold text-emerald-700">{t('backup.export_excel_btn')} (.xlsx)</span>
                    </button>
                    <div className="relative">
                        <input type="file" accept=".json,.dentix" onChange={handleUpload} aria-label={t('backup.restore_btn')} disabled={restoring} className="absolute inset-0 opacity-0 cursor-pointer w-full h-full z-10" />
                        <div className="h-full p-6 border-2 border-amber-200 border-dashed rounded-2xl bg-amber-50/50 flex flex-col items-center justify-center gap-3">
                            {restoring ? <div className="animate-spin h-8 w-8 border-4 border-amber-500 border-t-transparent rounded-full" /> : <Upload className="text-amber-500" size={32} />}
                            <span className="font-bold text-amber-700">{t('backup.restore_btn')} (.dentix / .json)</span>
                        </div>
                    </div>
                </div>
                {restorePreview && (
                    <form onSubmit={handleConfirmRestore} className="space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4" aria-label={t('backup.preview_title')}>
                        <h4 className="font-bold">{t('backup.preview_title')}</h4>
                        <p>{t('backup.restore_explanation')}</p>
                        <p>{t('backup.preview_date')}: {restorePreview.backup_date}</p>
                        <p>{t('backup.preview_counts')}: {Object.values(restorePreview.counts || {}).reduce((sum, count) => sum + count, 0)}</p>
                        {restorePreview.attachment_availability && <p>{t('backup.attachments_missing')}: {restorePreview.attachment_availability.missing} · {t('backup.attachments_unverified')}: {restorePreview.attachment_availability.unverified}</p>}
                        <ul className="grid grid-cols-1 gap-1 sm:grid-cols-2" aria-label={t('backup.preview_counts')}>
                            {Object.entries(restorePreview.counts || {}).filter(([, count]) => count > 0).map(([section, count]) => <li key={section}>{t(`backup.sections.${section}`, section)}: {count}</li>)}
                        </ul>
                        {restorePreview.staff_mapping?.length > 0 && <div><p className="font-bold">{t('backup.staff_mapping')}</p><ul>{restorePreview.staff_mapping.map((staff) => <li key={staff.existing_user_id}>{staff.name}</li>)}</ul></div>}
                        {restorePreview.legacy_unverified && <p className="font-bold">{t('backup.legacy_unverified')}</p>}
                        {restorePreview.missing_sections?.length > 0 && <p>{t('backup.missing_sections')}: {restorePreview.missing_sections.map((section) => t(`backup.sections.${section}`, section)).join('، ')}</p>}
                        <label className="block">{t('backup.confirm_password')}<input required type="password" autoComplete="current-password" value={restorePassword} onChange={(event) => setRestorePassword(event.target.value)} className="block w-full rounded border p-2" /></label>
                        <p className="text-sm text-slate-600">{t('backup.confirm_password_hint')}</p>
                        <button type="submit" disabled={restoring || !restorePassword} className="rounded bg-amber-700 px-4 py-2 font-bold text-white disabled:opacity-50">{t('backup.confirm_restore')}</button>
                        <button type="button" onClick={() => { setRestorePreview(null); setRestorePassword(''); }} className="ms-3 rounded border px-4 py-2">{t('backup.cancel_restore')}</button>
                    </form>
                )}
                {restoreOperation && <div className="rounded-xl border p-4" role="status">
                    <p>{t('backup.operation_status')}: {t(`backup.operation_${restoreOperation.status}`)}</p>
                    <button type="button" onClick={refreshRestoreStatus} className="mt-2 rounded border px-4 py-2">{t('backup.refresh_status')}</button>
                </div>}
            </div>
            {/* Danger Zone */}
            <div className="space-y-4 pt-6 border-t border-red-100 dark:border-red-900/30">
                <h3 className="font-bold text-lg flex items-center gap-2 text-red-600">
                    <div className="p-2 bg-red-100 text-red-600 rounded-lg"><AlertTriangle size={20} /></div>
                    {t('backup.danger_zone.title')}
                </h3>
                <div className="p-6 bg-red-50 border border-red-100 rounded-2xl flex flex-col md:flex-row justify-between items-center gap-4">
                    <div>
                        <h4 className="font-bold text-red-700">{t('backup.danger_zone.purge_patients')}</h4>
                        <p className="text-sm text-red-600/80 mt-1">{t('backup.danger_zone.purge_desc')}</p>
                    </div>
                    <button
                        onClick={handlePurge}
                        className="px-6 py-2 bg-red-600 text-white rounded-xl font-bold hover:bg-red-700 whitespace-nowrap"
                    >
                        {t('common.delete')}
                    </button>
                </div>
            </div>
        </div>
    );
};
export default BackupSettings;

