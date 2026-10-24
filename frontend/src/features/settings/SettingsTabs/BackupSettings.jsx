import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Database, Upload, Download, AlertTriangle, FileSpreadsheet } from 'lucide-react';
import * as api from '@/api';
const BackupSettings = ({ backupStatus, currentUser, setMessage, loadUserInfo }) => {
    const { t } = useTranslation();
    const [restoring, setRestoring] = useState(false);
    const [exportingXlsx, setExportingXlsx] = useState(false);

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
    const handleUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (!window.confirm(t('backup.restore_warning'))) return;
        const formData = new FormData();
        formData.append('file', file);
        try {
            setRestoring(true);
            await api.uploadBackup(formData);
            setMessage({ type: 'success', text: t('backup.restore_success') });
            setTimeout(() => window.location.reload(), 2000);
        } catch (err) {
            const msg = await extractErrorMessage(err, t('backup.restore_fail', 'فشل استعادة البيانات'));
            setMessage({ type: 'error', text: msg });
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
                                {backupStatus.loading ? t('backup.checking') : (backupStatus.connected ? t('backup.connected') : t('backup.disconnected'))}
                            </p>
                        </div>
                        {!backupStatus.connected && !backupStatus.loading && (
                            <button
                                onClick={async () => {
                                    try {
                                        const res = await api.getGoogleAuthUrl();
                                        window.location.href = res.data.url;
                                    } catch (err) { setMessage({ type: 'error', text: t('backup.connect_fail', 'فشل الاتصال') }) }
                                }}
                                className="px-6 py-2 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700"
                            >
                                {t('backup.connect_btn')}
                            </button>
                        )}
                    </div>
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
                                    onClick={async () => {
                                        setMessage({ type: 'info', text: t('backup.backing_up', 'جاري النسخ...') });
                                        await api.triggerManualBackup();
                                        setMessage({ type: 'success', text: t('backup.backup_success') });
                                        loadUserInfo();
                                    }}
                                    className="w-full py-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 text-center"
                                >
                                    {t('backup.backup_now')}
                                </button>
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
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                        <input type="file" accept=".json" onChange={handleUpload} disabled={restoring} className="absolute inset-0 opacity-0 cursor-pointer w-full h-full z-10" />
                        <div className="h-full p-6 border-2 border-amber-200 border-dashed rounded-2xl bg-amber-50/50 flex flex-col items-center justify-center gap-3">
                            {restoring ? <div className="animate-spin h-8 w-8 border-4 border-amber-500 border-t-transparent rounded-full" /> : <Upload className="text-amber-500" size={32} />}
                            <span className="font-bold text-amber-700">{t('backup.restore_btn')} (.json)</span>
                        </div>
                    </div>
                </div>
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

