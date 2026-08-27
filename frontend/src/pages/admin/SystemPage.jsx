import { useCallback, useEffect, useState } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import SettingsManager from '@/features/admin/SuperAdmin/SettingsManager';
import AuditLogViewer from '@/features/admin/SuperAdmin/AuditLogViewer';
import SecurityPanel from '@/features/admin/SuperAdmin/SecurityPanel';
import FeatureManager from '@/features/admin/SuperAdmin/FeatureManager';
import SessionManager from '@/features/admin/SuperAdmin/SessionManager';
import TwoFactorSetup from '@/features/admin/SuperAdmin/TwoFactorSetup';
import {
    Settings,
    User,
    Database,
    Shield,
    Zap,
    Monitor,
    Clock,
    CheckCircle2,
    XCircle,
    AlertTriangle,
} from 'lucide-react';
import { toast, ConfirmDialog } from '@/shared/ui';
import { useAuthStore } from '@/store/auth.store';
import { useTranslation } from 'react-i18next';

export default function SystemPage() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    const [activeTab, setActiveTab] = useState('settings');
    const [settings, setSettings] = useState([]);
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);
    const [is2faEnabled, setIs2faEnabled] = useState(false);
    const [profileForm, setProfileForm] = useState({ username: '', email: '', password: '' });
    const [updatingProfile, setUpdatingProfile] = useState(false);
    const [profileConfirmOpen, setProfileConfirmOpen] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [backupConfirmOpen, setBackupConfirmOpen] = useState(false);
    const [disconnectConfirmOpen, setDisconnectConfirmOpen] = useState(false);
    const [disconnecting, setDisconnecting] = useState(false);
    const [googleConnected, setGoogleConnected] = useState(false);
    const [lastBackupInfo, setLastBackupInfo] = useState({ status: null, message: null, date: null });

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [settingsRes, tenantsRes, googleRes, userRes] = await Promise.all([
                api.get('/api/v1/admin/settings'),
                api.get('/api/v1/admin/tenants'),
                api.get('/api/v1/admin/system/backup/google-status').catch(() => ({
                    data: { connected: false, last_backup: null },
                })),
                api.get('/api/v1/users/me'),
            ]);
            setSettings(Array.isArray(settingsRes.data) ? settingsRes.data : []);
            setTenants(Array.isArray(tenantsRes.data) ? tenantsRes.data : []);

            const googleData = googleRes.data?.data || googleRes.data;
            setGoogleConnected(Boolean(googleData?.connected));
            setLastBackupInfo(googleData?.last_backup || { status: null, message: null, date: null });
            setIs2faEnabled(Boolean(userRes.data?.is_2fa_enabled));
        } catch (error) {
            logger.error('Failed to fetch system data:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const status = params.get('backup_status');
        if (status) {
            if (status === 'success') {
                toast.success(t('super_admin.backup.oauth_success'));
            } else {
                const error = params.get('error') || t('super_admin.backup.oauth_failed');
                toast.error(t('super_admin.backup.oauth_error', { status, error }));
            }
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }, [t]);

    const handleProfileSubmit = (event) => {
        event.preventDefault();
        const username = profileForm.username.trim();
        const email = profileForm.email.trim();
        const password = profileForm.password.trim();

        if (!username && !email && !password) {
            toast.error(t('super_admin.profile.no_changes_error'));
            return;
        }

        setProfileConfirmOpen(true);
    };

    const confirmUpdateProfile = async () => {
        const payload = {};
        if (profileForm.username.trim()) payload.username = profileForm.username.trim();
        if (profileForm.email.trim()) payload.email = profileForm.email.trim();
        if (profileForm.password.trim()) payload.password = profileForm.password.trim();

        setUpdatingProfile(true);
        try {
            const response = await api.put('/api/v1/admin/system/profile', payload);
            toast.success(t('super_admin.profile.update_success'));

            const currentUser = useAuthStore.getState().user;
            if (currentUser && response.data?.data) {
                useAuthStore.getState().setUser({
                    ...currentUser,
                    ...response.data.data,
                });
            }

            setProfileForm({ username: '', email: '', password: '' });
            setProfileConfirmOpen(false);
        } catch (error) {
            const detail = error.response?.data?.detail;
            const message = typeof detail === 'string'
                ? detail
                : (Array.isArray(detail)
                    ? detail.map((item) => item.msg || item).join(', ')
                    : (error.message || t('super_admin.profile.update_fail')));
            toast.error(message);
        } finally {
            setUpdatingProfile(false);
        }
    };

    const handleConnectGoogle = async () => {
        try {
            const response = await api.get('/api/v1/admin/system/backup/google-auth');
            const data = response.data?.data || response.data;
            if (data?.url) {
                window.location.href = data.url;
            } else {
                toast.error(t('super_admin.backup.drive_not_configured'));
            }
        } catch {
            toast.error(t('super_admin.backup.connect_failed'));
        }
    };

    const confirmGoogleUpload = async () => {
        setUploading(true);
        try {
            const response = await api.post('/api/v1/admin/system/backup/google-upload');
            const data = response.data?.data || response.data;
            toast.info(data?.message || t('super_admin.backup.started_msg'));
            setLastBackupInfo((previous) => ({
                ...previous,
                status: 'processing',
                message: data?.message || t('super_admin.backup.started_msg'),
                date: new Date().toISOString(),
            }));
            setBackupConfirmOpen(false);
        } catch (error) {
            toast.error(error.response?.data?.detail || t('super_admin.backup.trigger_failed'));
        } finally {
            setUploading(false);
        }
    };

    const confirmDisconnectGoogle = async () => {
        setDisconnecting(true);
        try {
            await api.delete('/api/v1/admin/system/backup/google-auth');
            toast.success(t('super_admin.backup.disconnect_success'));
            setGoogleConnected(false);
            setDisconnectConfirmOpen(false);
        } catch (error) {
            toast.error(error.response?.data?.detail || t('super_admin.backup.disconnect_fail'));
        } finally {
            setDisconnecting(false);
        }
    };

    if (loading) {
        return <div className="p-8 text-center text-slate-500">{t('super_admin.system.loading')}</div>;
    }

    const tabs = [
        { id: 'settings', label: t('super_admin.system.tabs.settings'), icon: Settings },
        { id: 'features', label: t('super_admin.system.tabs.features'), icon: Zap },
        { id: 'profile', label: t('super_admin.system.tabs.profile'), icon: User },
        { id: 'backup', label: t('super_admin.system.tabs.backup'), icon: Database },
        { id: 'security', label: t('super_admin.system.tabs.security'), icon: Shield },
        { id: 'sessions', label: t('super_admin.system.tabs.sessions'), icon: Monitor },
    ];

    return (
        <div className="space-y-6 animate-fade-in-up" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-4">
                    <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-2xl text-slate-600 dark:text-slate-400">
                        <Settings size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white">
                            {t('super_admin.system.title')}
                        </h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">
                            {t('super_admin.system.subtitle')}
                        </p>
                    </div>
                </div>
                <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl flex-wrap">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            type="button"
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === tab.id ? 'bg-white dark:bg-slate-700 shadow text-slate-800 dark:text-white' : 'text-slate-500'}`}
                        >
                            <tab.icon size={16} />
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {activeTab === 'settings' && <SettingsManager settings={settings} fetchData={fetchData} />}
            {activeTab === 'features' && <FeatureManager tenants={tenants} />}

            {activeTab === 'profile' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-overlay shadow-sm border border-slate-100 dark:border-slate-800">
                        <h3 className="text-xl font-black mb-6 text-slate-800 dark:text-white">
                            {t('super_admin.profile.title')}
                        </h3>
                        <form onSubmit={handleProfileSubmit} className="space-y-6">
                            <div>
                                <label htmlFor="profile_username" className="block text-sm font-bold mb-2 text-slate-600 dark:text-slate-400">
                                    {t('super_admin.profile.username_label')}
                                </label>
                                <input
                                    id="profile_username"
                                    type="text"
                                    className="w-full p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 font-bold text-slate-800 dark:text-slate-200"
                                    value={profileForm.username}
                                    onChange={(event) => setProfileForm({ ...profileForm, username: event.target.value })}
                                    placeholder={t('super_admin.profile.unchanged_placeholder')}
                                />
                            </div>
                            <div>
                                <label htmlFor="profile_email" className="block text-sm font-bold mb-2 text-slate-600 dark:text-slate-400">
                                    {t('super_admin.profile.email_label')}
                                </label>
                                <input
                                    id="profile_email"
                                    type="email"
                                    className="w-full p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 font-bold text-slate-800 dark:text-slate-200"
                                    value={profileForm.email}
                                    onChange={(event) => setProfileForm({ ...profileForm, email: event.target.value })}
                                    placeholder={t('super_admin.profile.unchanged_placeholder')}
                                />
                            </div>
                            <div>
                                <label htmlFor="profile_password" className="block text-sm font-bold mb-2 text-slate-600 dark:text-slate-400">
                                    {t('super_admin.profile.password_label')}
                                </label>
                                <input
                                    id="profile_password"
                                    type="password"
                                    className="w-full p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 font-bold text-slate-800 dark:text-slate-200"
                                    value={profileForm.password}
                                    onChange={(event) => setProfileForm({ ...profileForm, password: event.target.value })}
                                    placeholder="*******"
                                    autoComplete="new-password"
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={updatingProfile || (!profileForm.username.trim() && !profileForm.email.trim() && !profileForm.password.trim())}
                                className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white rounded-2xl font-black shadow-xl shadow-indigo-500/20 transition-all cursor-pointer disabled:cursor-not-allowed"
                            >
                                {updatingProfile ? t('common.saving', 'Saving...') : t('super_admin.profile.save_changes')}
                            </button>
                        </form>
                    </div>
                    <TwoFactorSetup isEnabled={is2faEnabled} onToggle={setIs2faEnabled} />
                </div>
            )}

            {activeTab === 'backup' && (
                <>
                    <div className="bg-indigo-50/60 dark:bg-indigo-950/20 p-8 rounded-overlay border border-indigo-100 dark:border-indigo-900/30 flex flex-col md:flex-row items-center gap-6">
                        <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/40 rounded-2xl flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0">
                            <Shield size={32} />
                        </div>
                        <div className="space-y-2 text-start">
                            <h3 className="text-xl font-bold text-slate-800 dark:text-white">
                                {t('super_admin.backup.policy_title')}
                            </h3>
                            <p className="text-slate-600 dark:text-slate-300 text-sm leading-relaxed">
                                {t('super_admin.backup.policy_desc')}{' '}
                                <code className="font-mono text-xs bg-slate-200 dark:bg-slate-800 px-2 py-0.5 rounded">
                                    scripts/backup/
                                </code>
                            </p>
                        </div>
                    </div>

                    <div className="bg-white dark:bg-slate-900 p-8 rounded-overlay shadow-sm border border-slate-100 dark:border-slate-800 mt-6">
                        <div className="flex items-center justify-between mb-6 gap-4">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-xl flex items-center justify-center text-green-600">
                                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                                        <path d="M23.64 12.03l-3.535 6.13H13.06l3.525-6.13h7.056zM11.97 12.03l-3.53-6.13H1.385l3.53-6.13h7.054zm0 0L8.44 5.89h7.065l3.53 6.134h-7.066zm-5.65 0L2.79 5.89h7.066l3.53 6.134H6.32zM12 2.625l3.535 6.13H8.465L12 2.625z" />
                                    </svg>
                                </div>
                                <div className="text-start">
                                    <h3 className="text-xl font-bold text-slate-800 dark:text-white">
                                        {t('super_admin.backup.drive_title')}
                                    </h3>
                                    <p className="text-slate-500 dark:text-slate-400 text-sm">
                                        {t('super_admin.backup.drive_subtitle')}
                                    </p>
                                </div>
                            </div>
                            <span className={`px-3 py-1 text-xs font-bold rounded-full ${googleConnected
                                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-500'}`}
                            >
                                {googleConnected
                                    ? t('super_admin.backup.connected')
                                    : t('super_admin.backup.disconnected')}
                            </span>
                        </div>

                        <div className="mb-6 p-4 bg-slate-50 dark:bg-slate-800/60 rounded-2xl border border-slate-100 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div className="flex items-center gap-3">
                                <Clock size={20} className="text-slate-400 shrink-0" />
                                <div>
                                    <p className="text-xs text-slate-400 font-bold">{t('super_admin.backup.last_run_label')}</p>
                                    <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                                        {lastBackupInfo.date
                                            ? new Date(lastBackupInfo.date).toLocaleString(i18n.language)
                                            : t('super_admin.backup.no_runs_yet')}
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2 flex-wrap">
                                {lastBackupInfo.status === 'success' && (
                                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400">
                                        <CheckCircle2 size={14} />
                                        {t('super_admin.backup.status_success')}
                                    </span>
                                )}
                                {lastBackupInfo.status === 'processing' && (
                                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400">
                                        <AlertTriangle size={14} />
                                        {t('super_admin.backup.status_processing')}
                                    </span>
                                )}
                                {lastBackupInfo.status === 'failed' && (
                                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400">
                                        <XCircle size={14} />
                                        {t('super_admin.backup.status_failed')}
                                    </span>
                                )}
                                {lastBackupInfo.message && (
                                    <span className="text-xs text-slate-500 max-w-xs truncate" title={lastBackupInfo.message}>
                                        ({lastBackupInfo.message})
                                    </span>
                                )}
                            </div>
                        </div>

                        <div className="flex flex-wrap gap-4">
                            {!googleConnected ? (
                                <button
                                    type="button"
                                    onClick={handleConnectGoogle}
                                    className="px-6 py-3 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 hover:border-blue-500 hover:text-blue-600 text-slate-600 dark:text-slate-300 rounded-xl font-bold transition-all flex items-center gap-2"
                                >
                                    {t('super_admin.backup.connect_btn')}
                                </button>
                            ) : (
                                <>
                                    <button
                                        type="button"
                                        onClick={() => setBackupConfirmOpen(true)}
                                        disabled={uploading}
                                        className="px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-slate-400 text-white rounded-xl font-bold shadow-lg shadow-green-500/30 transition-all flex items-center gap-2"
                                    >
                                        {uploading ? t('super_admin.backup.starting') : t('super_admin.backup.trigger_cloud_btn')}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setDisconnectConfirmOpen(true)}
                                        disabled={disconnecting || uploading}
                                        className="px-6 py-3 bg-slate-100 hover:bg-rose-50 hover:text-rose-600 dark:bg-slate-800 dark:hover:bg-rose-950/30 dark:hover:text-rose-400 text-slate-600 dark:text-slate-300 rounded-xl font-bold transition-all"
                                    >
                                        {disconnecting ? t('super_admin.backup.disconnecting') : t('super_admin.backup.disconnect_btn')}
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                </>
            )}

            {activeTab === 'security' && (
                <div className="space-y-8">
                    <SecurityPanel />
                    <AuditLogViewer tenants={tenants} />
                </div>
            )}

            {activeTab === 'sessions' && <SessionManager />}

            <ConfirmDialog
                isOpen={profileConfirmOpen}
                onClose={() => setProfileConfirmOpen(false)}
                onConfirm={confirmUpdateProfile}
                title={t('super_admin.profile.confirm_title')}
                message={t('super_admin.profile.confirm_msg')}
                confirmText={t('common.confirm', 'Confirm')}
                cancelText={t('common.cancel')}
                variant="primary"
                isLoading={updatingProfile}
            />

            <ConfirmDialog
                isOpen={backupConfirmOpen}
                onClose={() => setBackupConfirmOpen(false)}
                onConfirm={confirmGoogleUpload}
                title={t('super_admin.backup.confirm_upload_title')}
                message={t('super_admin.backup.confirm_upload_msg')}
                confirmText={t('super_admin.backup.confirm_start_btn')}
                cancelText={t('common.cancel')}
                variant="primary"
                isLoading={uploading}
            />

            <ConfirmDialog
                isOpen={disconnectConfirmOpen}
                onClose={() => setDisconnectConfirmOpen(false)}
                onConfirm={confirmDisconnectGoogle}
                title={t('super_admin.backup.disconnect_confirm_title')}
                message={t('super_admin.backup.disconnect_confirm_msg')}
                confirmText={t('common.confirm', 'Confirm')}
                cancelText={t('common.cancel')}
                variant="danger"
                isLoading={disconnecting}
            />
        </div>
    );
}
