import { useEffect, useState } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import SettingsManager from '@/features/admin/SuperAdmin/SettingsManager';
import AuditLogViewer from '@/features/admin/SuperAdmin/AuditLogViewer';
import SecurityPanel from '@/features/admin/SuperAdmin/SecurityPanel';
import FeatureManager from '@/features/admin/SuperAdmin/FeatureManager';
import SessionManager from '@/features/admin/SuperAdmin/SessionManager';
import TwoFactorSetup from '@/features/admin/SuperAdmin/TwoFactorSetup';
import { Settings, User, Database, Shield, Zap, Monitor } from 'lucide-react';
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
    
    // Profile State
    const [profileForm, setProfileForm] = useState({ username: '', email: '', password: '' });
    const [updatingProfile, setUpdatingProfile] = useState(false);
    const [profileConfirmOpen, setProfileConfirmOpen] = useState(false);
    
    // Backup State
    const [uploading, setUploading] = useState(false);
    const [backupConfirmOpen, setBackupConfirmOpen] = useState(false);
    
    // Google Drive Handlers
    const [googleConnected, setGoogleConnected] = useState(false);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [setRes, tenantsRes, googleRes, userRes] = await Promise.all([
                api.get('/api/v1/admin/settings'),
                api.get('/api/v1/admin/tenants'),
                api.get('/api/v1/admin/system/backup/google-status').catch(() => ({ data: { connected: false } })),
                api.get('/api/v1/users/me')
            ]);
            setSettings(Array.isArray(setRes.data) ? setRes.data : []);
            setTenants(Array.isArray(tenantsRes.data) ? tenantsRes.data : []);
            setGoogleConnected(googleRes.data?.connected || false);
            setIs2faEnabled(userRes.data?.is_2fa_enabled || false);
        } catch (err) {
            logger.error('Failed to fetch system data:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        
        const params = new URLSearchParams(window.location.search);
        const status = params.get('backup_status');
        if (status) {
            if (status === 'success') {
                toast.success('تم ربط حساب Google Drive بنجاح ✅');
                window.history.replaceState({}, document.title, window.location.pathname);
            } else {
                const error = params.get('error') || 'فشل الربط';
                toast.error(`حدث خطأ أثناء الربط: ${status}\n${error}`);
            }
        }
    }, []);

    const handleProfileSubmit = (e) => {
        e.preventDefault();
        const username = profileForm.username.trim();
        const email = profileForm.email.trim();
        const password = profileForm.password.trim();

        if (!username && !email && !password) {
            toast.error(t('super_admin.profile.no_changes_error') || 'يرجى إدخال حقل واحد على الأقل للتحديث');
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
            const res = await api.put('/api/v1/admin/system/profile', payload);
            toast.success(t('super_admin.profile.update_success') || "تم تحديث الملف الشخصي بنجاح");
            
            // Refresh identity state in auth store if user exists
            const currentUser = useAuthStore.getState().user;
            if (currentUser && res.data?.data) {
                useAuthStore.getState().setUser({
                    ...currentUser,
                    ...res.data.data
                });
            }

            setProfileForm({ username: '', email: '', password: '' });
            setProfileConfirmOpen(false);
        } catch (error) {
            const detail = error.response?.data?.detail;
            const message = typeof detail === 'string' 
                ? detail 
                : (Array.isArray(detail) ? detail.map(d => d.msg || d).join(', ') : (error.message || t('super_admin.profile.update_fail') || "فشل تحديث البيانات"));
            toast.error(message);
        } finally {
            setUpdatingProfile(false);
        }
    };

    const handleConnectGoogle = async () => {
        try {
            const res = await api.get('/api/v1/admin/system/backup/google-auth');
            if (res.data.url) window.location.href = res.data.url;
            else toast.error("لم يتم تكوين إعدادات Google Drive");
        } catch (error) {
            toast.error("فشل الاتصال بـ Google Drive");
        }
    };

    const confirmGoogleUpload = async () => {
        setUploading(true);
        try {
            await api.post('/api/v1/admin/system/backup/google-upload');
            toast.success("تم الرفع بنجاح");
            setBackupConfirmOpen(false);
        } catch (error) {
            toast.error(error.response?.data?.detail || "فشل الرفع");
        } finally {
            setUploading(false);
        }
    };

    if (loading) return <div className="p-8 text-center text-slate-500">جاري تحميل إعدادات النظام...</div>;

    return (
        <div className="space-y-6 animate-fade-in-up" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-4">
                    <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-2xl text-slate-600 dark:text-slate-400">
                        <Settings size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white">إعدادات النظام</h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">التحكم في الإعدادات العامة والأمان</p>
                    </div>
                </div>
                <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl flex-wrap">
                    {[
                        { id: 'settings', label: 'عام', icon: Settings },
                        { id: 'features', label: 'المميزات', icon: Zap },
                        { id: 'profile', label: 'الحساب', icon: User },
                        { id: 'backup', label: 'النسخ الاحتياطي', icon: Database },
                        { id: 'security', label: 'الأمان', icon: Shield },
                        { id: 'sessions', label: 'الجلسات', icon: Monitor },
                    ].map(tab => (
                        <button
                            key={tab.id}
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
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-[2.5rem] shadow-sm border border-slate-100 dark:border-slate-800">
                        <h3 className="text-xl font-black mb-6 text-slate-800 dark:text-white">تحديث بيانات المدير</h3>
                        <form onSubmit={handleProfileSubmit} className="space-y-6">
                            <div>
                                <label htmlFor="profile_username" className="block text-sm font-bold mb-2 text-slate-600 dark:text-slate-400">اسم المستخدم الجديد</label>
                                <input
                                    id="profile_username"
                                    type="text"
                                    className="w-full p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 font-bold text-slate-800 dark:text-slate-200"
                                    value={profileForm.username}
                                    onChange={e => setProfileForm({ ...profileForm, username: e.target.value })}
                                    placeholder="اتركه فارغاً إذا لم ترد تغييره"
                                />
                            </div>
                            <div>
                                <label htmlFor="profile_email" className="block text-sm font-bold mb-2 text-slate-600 dark:text-slate-400">البريد الإلكتروني الجديد</label>
                                <input
                                    id="profile_email"
                                    type="email"
                                    className="w-full p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 font-bold text-slate-800 dark:text-slate-200"
                                    value={profileForm.email}
                                    onChange={e => setProfileForm({ ...profileForm, email: e.target.value })}
                                    placeholder="اتركه فارغاً إذا لم ترد تغييره"
                                />
                            </div>
                            <div>
                                <label htmlFor="profile_password" className="block text-sm font-bold mb-2 text-slate-600 dark:text-slate-400">كلمة المرور الجديدة</label>
                                <input
                                    id="profile_password"
                                    type="password"
                                    className="w-full p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 outline-none focus:ring-2 focus:ring-indigo-500 font-bold text-slate-800 dark:text-slate-200"
                                    value={profileForm.password}
                                    onChange={e => setProfileForm({ ...profileForm, password: e.target.value })}
                                    placeholder="*******"
                                    autoComplete="new-password"
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={updatingProfile || (!profileForm.username.trim() && !profileForm.email.trim() && !profileForm.password.trim())}
                                className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white rounded-2xl font-black shadow-xl shadow-indigo-500/20 transition-all cursor-pointer disabled:cursor-not-allowed"
                            >
                                {updatingProfile ? (t('common.saving') || 'جاري الحفظ...') : (t('super_admin.profile.save_changes') || 'حفظ التغييرات')}
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
                        <div className="space-y-2 text-right">
                            <h3 className="text-xl font-bold text-slate-800 dark:text-white">سياسة النسخ الاحتياطي للنظام وقاعدة البيانات</h3>
                            <p className="text-slate-600 dark:text-slate-300 text-sm leading-relaxed">
                                تم تعطيل تحميل واستعادة قواعد البيانات الخام عبر HTTP لضمان أمان البيانات وعزل المستأجرين.
                                تُدار النسخ الاحتياطية الشاملة واستعادة النظام حصرياً عبر أوامر CLI الآمنة المعزولة على الخادم (<code className="font-mono text-xs bg-slate-200 dark:bg-slate-800 px-2 py-0.5 rounded">scripts/backup/</code>).
                            </p>
                        </div>
                    </div>
                    
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-[2.5rem] shadow-sm border border-slate-100 dark:border-slate-800 mt-6">
                        <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-xl flex items-center justify-center text-green-600">
                                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M23.64 12.03l-3.535 6.13H13.06l3.525-6.13h7.056zM11.97 12.03l-3.53-6.13H1.385l3.53-6.13h7.054zm0 0L8.44 5.89h7.065l3.53 6.134h-7.066zm-5.65 0L2.79 5.89h7.066l3.53 6.134H6.32zM12 2.625l3.535 6.13H8.465L12 2.625z" />
                                    </svg>
                                </div>
                                <div className="text-right">
                                    <h3 className="text-xl font-bold text-slate-800 dark:text-white">Google Drive Backup</h3>
                                    <p className="text-slate-500 dark:text-slate-400 text-sm">اربط حسابك لتخزين النسخ الاحتياطية سحابياً</p>
                                </div>
                            </div>
                            {googleConnected ? <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full">متصل</span> : <span className="px-3 py-1 bg-slate-100 text-slate-500 text-xs font-bold rounded-full">غير متصل</span>}
                        </div>
                        <div className="flex gap-4">
                            {!googleConnected ? (
                                <button onClick={handleConnectGoogle} className="px-6 py-3 bg-white border-2 border-slate-200 hover:border-blue-500 hover:text-blue-600 text-slate-600 rounded-xl font-bold transition-all flex items-center gap-2">
                                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" /><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" /><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.21.81-.63z" fill="#FBBC05" /><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" /></svg>
                                    ربط حساب Google
                                </button>
                            ) : (
                                <button onClick={() => setBackupConfirmOpen(true)} disabled={uploading} className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-xl font-bold shadow-lg shadow-green-500/30 transition-all flex items-center gap-2">
                                    {uploading ? 'جاري الرفع...' : 'نسخ احتياطي للسحابة الآن'}
                                </button>
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

            {/* Profile Update Confirmation Dialog */}
            <ConfirmDialog
                isOpen={profileConfirmOpen}
                onClose={() => setProfileConfirmOpen(false)}
                onConfirm={confirmUpdateProfile}
                title={t('super_admin.profile.confirm_title') || 'تأكيد تحديث بيانات الدخول'}
                message={t('super_admin.profile.confirm_msg') || 'هل أنت متأكد من رغبتك في تحديث بيانات الدخول؟'}
                confirmText={t('common.confirm') || 'تأكيد'}
                cancelText={t('common.cancel') || 'إلغاء'}
                variant="primary"
                isLoading={updatingProfile}
            />

            {/* Google Backup Confirmation Dialog */}
            <ConfirmDialog
                isOpen={backupConfirmOpen}
                onClose={() => setBackupConfirmOpen(false)}
                onConfirm={confirmGoogleUpload}
                title="تأكيد رفع النسخة الاحتياطية"
                message="هل تريد رفع نسخة احتياطية إلى Google Drive الآن؟"
                confirmText="تأكيد الرفع"
                cancelText="إلغاء"
                variant="primary"
                isLoading={uploading}
            />
        </div>
    );
}
