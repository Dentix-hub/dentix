import { useEffect, useState } from 'react';
import { api } from '@/api';
import SettingsManager from '@/features/admin/SuperAdmin/SettingsManager';
import AuditLogViewer from '@/features/admin/SuperAdmin/AuditLogViewer';
import SecurityPanel from '@/features/admin/SuperAdmin/SecurityPanel';
import { Settings, User, Database, Shield } from 'lucide-react';
export default function SystemPage() {
    const [activeTab, setActiveTab] = useState('settings');
    const [settings, setSettings] = useState([]);
    const [auditLogs, setAuditLogs] = useState([]);
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);
    // Profile State
    const [profileForm, setProfileForm] = useState({ username: '', email: '', password: '' });
    // Backup State
    const [uploading, setUploading] = useState(false);
    // Google Drive Handlers
    const [googleConnected, setGoogleConnected] = useState(false);
    const [lastBackupStatus, setLastBackupStatus] = useState(null);
    const fetchData = async () => {
        setLoading(true);
        try {
            const [setRes, auditRes, tenantsRes, googleRes] = await Promise.all([
                api.get('/api/v1/admin/settings'),
                api.get('/api/v1/admin/audit-logs'),
                api.get('/api/v1/admin/tenants'),
                api.get('/api/v1/admin/system/backup/google-status').catch(() => ({ data: { connected: false } }))
            ]);
            setSettings(Array.isArray(setRes.data) ? setRes.data : []);
            setAuditLogs(Array.isArray(auditRes.data) ? auditRes.data : []);
            setTenants(Array.isArray(tenantsRes.data) ? tenantsRes.data : []);
            setGoogleConnected(googleRes.data?.connected || false);
            setLastBackupStatus(googleRes.data?.last_backup || null);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };
    useEffect(() => {
        fetchData();
        // Check for backup status in URL (from OAuth redirect)
        const params = new URLSearchParams(window.location.search);
        const status = params.get('backup_status');
        if (status) {
            if (status === 'success') {
                alert('تم ربط حساب Google Drive بنجاح ✅');
                window.history.replaceState({}, document.title, window.location.pathname);
            } else {
                const error = params.get('error') || 'فشل الربط';
                alert(`حدث خطأ أثناء الربط: ${status}\n${error}`);
            }
        }
    }, []);
    // --- Profile Handlers ---
    const handleUpdateProfile = async (e) => {
        e.preventDefault();
        if (!window.confirm("هل أنت متأكد من تحديث بيانات الدخول؟")) return;
        try {
            await api.put('/admin/system/profile', profileForm);
            alert("تم تحديث الملف الشخصي بنجاح");
            setProfileForm({ username: '', email: '', password: '' }); // Reset or keep? 
        } catch (error) {
            alert("فشل تحديث البيانات");
        }
    };
    // --- Backup Handlers ---
    const handleDownloadBackup = async () => {
        try {
            setUploading(true); // Reuse uploading state for loading indicator
            const response = await api.get('/api/v1/admin/system/backup', {
                responseType: 'blob' // Important for binary files
            });
            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            // Extract filename from headers or default
            const contentDisposition = response.headers['content-disposition'];
            let fileName = 'smart_clinic_backup.db';
            if (contentDisposition) {
                const fileNameMatch = contentDisposition.match(/filename="?(.+)"?/);
                if (fileNameMatch && fileNameMatch.length === 2)
                    fileName = fileNameMatch[1];
            }
            link.setAttribute('download', fileName);
            document.body.appendChild(link);
            link.click();
            link.parentNode.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error("Backup download failed:", error);
            alert("فشل تحميل النسخة الاحتياطية. يرجى التأكد من الصلاحيات.");
        } finally {
            setUploading(false);
        }
    };
    const handleRestoreBackup = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        if (!window.confirm("تحذير: استعادة النسخة الاحتياطية ستقوم بحذف جميع البيانات الحالية واستبدالها بالنسخة. هل أنت متأكد تماماً؟")) return;
        const formData = new FormData();
        formData.append('file', file);
        setUploading(true);
        try {
            await api.post('/api/v1/admin/system/restore', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            alert("تم استعادة النسخة الاحتياطية بنجاح. يرجى إعادة تشغيل النظام.");
        } catch (error) {
            alert("فشلت عملية الاستعادة");
        } finally {
            setUploading(false);
        }
    };
    // --- Google Drive Handlers ---
    const handleConnectGoogle = async () => {
        try {
            // Example endpoint, adjust if backend has a specific route
            const res = await api.get('/api/v1/admin/system/backup/google-auth');
            if (res.data.url) {
                window.location.href = res.data.url;
            } else {
                alert("لم يتم تكوين إعدادات Google Drive في النظام");
            }
        } catch (error) {
            console.error("Google Auth Error", error);
            alert("فشل الاتصال بـ Google Drive");
        }
    };
    const handleGoogleUpload = async () => {
        if (!window.confirm("هل تريد رفع نسخة احتياطية إلى Google Drive الآن؟")) return;
        setUploading(true);
        setUploading(true);
        try {
            await api.post('/api/v1/admin/system/backup/google-upload');
            alert("تم الرفع بنجاح");
        } catch (error) {
            console.error(error);
            const msg = error.response?.data?.detail || "فشل الرفع";
            alert(`فشل الرفع: ${msg}`);
        } finally {
            setUploading(false);
        }
    };
    if (loading) return <div className="p-8 text-center text-slate-500">جاري تحميل إعدادات النظام...</div>;
    return (
        <div className="space-y-6 animate-fade-in-up">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-4">
                    <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-2xl text-slate-600 dark:text-slate-400">
                        <Settings size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-black text-slate-800 dark:text-white">إعدادات النظام</h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">التحكم في الإعدادات العامة والأمان</p>
                    </div>
                </div>
                <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl flex-wrap">
                    {[
                        { id: 'settings', label: 'عام', icon: Settings },
                        { id: 'profile', label: 'الملف الشخصي', icon: User }, // New
                        { id: 'backup', label: 'النسخ الاحتياطي', icon: Database }, // New
                        { id: 'security', label: 'الأمان', icon: Shield },
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
            {/* General Settings */}
            {activeTab === 'settings' && (
                <SettingsManager settings={settings} fetchData={fetchData} />
            )}
            {/* Profile Management */}
            {activeTab === 'profile' && (
                <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 max-w-2xl">
                    <h3 className="text-lg font-bold mb-4 text-slate-800 dark:text-white">تحديث بيانات المدير</h3>
                    <form onSubmit={handleUpdateProfile} className="space-y-4">
                        <div>
                            <label className="block text-sm font-bold mb-1 text-slate-600">اسم المستخدم الجديد</label>
                            <input
                                type="text"
                                className="w-full p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700"
                                value={profileForm.username}
                                onChange={e => setProfileForm({ ...profileForm, username: e.target.value })}
                                placeholder="اتركه فارغاً إذا لم ترد تغييره"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-bold mb-1 text-slate-600">البريد الإلكتروني الجديد</label>
                            <input
                                type="email"
                                className="w-full p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700"
                                value={profileForm.email}
                                onChange={e => setProfileForm({ ...profileForm, email: e.target.value })}
                                placeholder="اتركه فارغاً إذا لم ترد تغييره"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-bold mb-1 text-slate-600">كلمة المرور الجديدة</label>
                            <input
                                type="password"
                                className="w-full p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700"
                                value={profileForm.password}
                                onChange={e => setProfileForm({ ...profileForm, password: e.target.value })}
                                placeholder="*******"
                            />
                        </div>
                        <button type="submit" className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-bold shadow-lg shadow-indigo-500/30 hover:bg-indigo-700 transition-colors">
                            حفظ التغييرات
                        </button>
                    </form>
                </div>
            )}
            {/* Backup & Restore */}
            {activeTab === 'backup' && (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col items-center text-center gap-4">
                            <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center text-blue-600">
                                <Database size={32} />
                            </div>
                            <h3 className="text-xl font-bold text-slate-800 dark:text-white">تحميل نسخة احتياطية</h3>
                            <p className="text-slate-500 dark:text-slate-400 text-sm">
                                قم بتحميل نسخة كاملة من قاعدة البيانات الحالية (ملف .db) للاحتفاظ بها في مكان آمن.
                            </p>
                            <button
                                onClick={handleDownloadBackup}
                                className="mt-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow-lg shadow-blue-500/30 transition-all w-full md:w-auto"
                            >
                                تحميل الآن
                            </button>
                        </div>
                        <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col items-center text-center gap-4 border-2 border-dashed border-slate-200 dark:border-slate-700">
                            <div className="w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-2xl flex items-center justify-center text-amber-600">
                                <Shield size={32} />
                            </div>
                            <h3 className="text-xl font-bold text-slate-800 dark:text-white">استعادة نسخة احتياطية</h3>
                            <p className="text-slate-500 dark:text-slate-400 text-sm">
                                رفع ملف نسخة احتياطية لاستبدال البيانات الحالية. <br /><span className="text-rose-500 font-bold">تحذير: سيتم حذف البيانات الحالية!</span>
                            </p>
                            <label className={`mt-2 px-6 py-3 ${uploading ? 'bg-slate-400' : 'bg-slate-800 hover:bg-slate-900'} text-white rounded-xl font-bold shadow-lg cursor-pointer transition-all w-full md:w-auto`}>
                                {uploading ? 'جاري الرفع...' : 'رفع ملف الاستعادة'}
                                <input type="file" className="hidden" accept=".db" onChange={handleRestoreBackup} disabled={uploading} />
                            </label>
                        </div>
                    </div>
                    {/* Google Drive Integration */}
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 mt-6">
                        <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-xl flex items-center justify-center text-green-600">
                                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M23.64 12.03l-3.535 6.13H13.06l3.525-6.13h7.056zM11.97 12.03l-3.53 6.13H1.385l3.53-6.13h7.054zm0 0L8.44 5.89h7.065l3.53 6.134h-7.066zm-5.65 0L2.79 5.89h7.066l3.53 6.134H6.32zM12 2.625l3.535 6.13H8.465L12 2.625z" />
                                    </svg>
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-slate-800 dark:text-white">Google Drive Backup</h3>
                                    <p className="text-slate-500 dark:text-slate-400 text-sm">اربط حسابك لتخزين النسخ الاحتياطية سحابياً</p>
                                </div>
                            </div>
                            {googleConnected ? (
                                <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full">متصل</span>
                            ) : (
                                <span className="px-3 py-1 bg-slate-100 text-slate-500 text-xs font-bold rounded-full">غير متصل</span>
                            )}
                        </div>
                        <div className="flex gap-4">
                            {!googleConnected ? (
                                <button
                                    onClick={handleConnectGoogle}
                                    className="px-6 py-3 bg-white border-2 border-slate-200 hover:border-blue-500 hover:text-blue-600 text-slate-600 rounded-xl font-bold transition-all flex items-center gap-2"
                                >
                                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" /><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" /><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.21.81-.63z" fill="#FBBC05" /><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" /></svg>
                                    ربط حساب Google
                                </button>
                            ) : (
                                <button
                                    onClick={handleGoogleUpload}
                                    disabled={uploading}
                                    className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-xl font-bold shadow-lg shadow-green-500/30 transition-all flex items-center gap-2"
                                >
                                    {uploading ? 'جاري الرفع...' : 'نسخ احتياطي للسحابة الآن'}
                                </button>
                            )}
                        </div>
                        {/* Status Display */}
                        {googleConnected && lastBackupStatus && lastBackupStatus.status && (
                            <div className={`mt-6 p-4 rounded-xl border ${lastBackupStatus.status === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' :
                                lastBackupStatus.status === 'processing' ? 'bg-blue-50 border-blue-200 text-blue-800' :
                                    'bg-rose-50 border-rose-200 text-rose-800'
                                }`}>
                                <div className="flex items-center gap-2 font-bold mb-1">
                                    {lastBackupStatus.status === 'success' && <div className="w-2 h-2 rounded-full bg-emerald-500"></div>}
                                    {lastBackupStatus.status === 'processing' && <div className="animate-pulse w-2 h-2 rounded-full bg-blue-500"></div>}
                                    {lastBackupStatus.status === 'failed' && <div className="w-2 h-2 rounded-full bg-rose-500"></div>}
                                    <span>
                                        {lastBackupStatus.status === 'success' ? 'آخر عملية نسخ: ناجحة' :
                                            lastBackupStatus.status === 'processing' ? 'جاري النسخ الآن...' :
                                                'آخر عملية نسخ: فشلت'}
                                    </span>
                                    <span className="text-xs opacity-70 px-2">
                                        {lastBackupStatus.date && new Date(lastBackupStatus.date).toLocaleString('en-US')}
                                    </span>
                                </div>
                                <div className="text-sm opacity-90 font-mono" dir="ltr">
                                    {lastBackupStatus.message.startsWith('http') ? (
                                        <a href={lastBackupStatus.message} target="_blank" rel="noopener noreferrer" className="underline text-blue-600 hover:text-blue-800 flex items-center gap-1">
                                            فتح الملف في Google Drive ↗
                                            <span className="text-xs text-slate-500 no-underline ml-2">({lastBackupStatus.message})</span>
                                        </a>
                                    ) : (
                                        lastBackupStatus.message
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </>
            )
            }
            {/* Security Audit */}
            {
                activeTab === 'security' && (
                    <div className="space-y-8">
                        <SecurityPanel />
                        <AuditLogViewer
                            logs={auditLogs}
                            tenants={tenants}
                            onFilter={async (filters) => {
                                try {
                                    const params = new URLSearchParams();
                                    if (filters.tenant_id) params.append('tenant_id', filters.tenant_id);
                                    if (filters.action) params.append('action', filters.action);
                                    if (filters.start_date) params.append('start_date', filters.start_date);
                                    if (filters.end_date) params.append('end_date', filters.end_date);
                                    const res = await api.get(`/admin/audit-logs?${params.toString()}`);
                                    setAuditLogs(Array.isArray(res.data) ? res.data : []);
                                } catch (err) {
                                    console.error('Filter error:', err);
                                }
                            }}
                        />
                    </div>
                )
            }
        </div >
    );
}
