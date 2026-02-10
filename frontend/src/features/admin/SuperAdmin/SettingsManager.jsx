import { useState, useEffect } from 'react';
import { Save, AlertTriangle, Monitor, Megaphone } from 'lucide-react';
import { api } from '@/api';
const SettingsManager = () => {
    const [localSettings, setLocalSettings] = useState([]);
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        fetchSettings();
    }, []);
    const fetchSettings = async () => {
        try {
            setLoading(true);
            const res = await api.get('/api/v1/admin/settings');
            setLocalSettings(Array.isArray(res.data) ? res.data : []);
        } catch (err) {
            console.error("Failed to fetch settings", err);
        } finally {
            setLoading(false);
        }
    };
    const handleToggleMaintenance = async () => {
        const setting = localSettings.find(s => s.key === 'maintenance_mode');
        // If not found, assume false and create it on toggle
        const currentValue = setting ? setting.value : 'false';
        const newValue = currentValue === 'true' ? 'false' : 'true';
        const confirmMsg = newValue === 'true'
            ? "هل أنت متأكد من تفعيل وضع الصيانة؟ سيتم منع جميع المستخدمين (غير المسؤولين) من الدخول."
            : "هل أنت متأكد من إيقاف وضع الصيانة؟";
        if (!window.confirm(confirmMsg)) return;
        await updateSetting('maintenance_mode', newValue);
    };
    const updateSetting = async (key, value) => {
        // Optimistic update
        setLocalSettings(prev => {
            const exists = prev.find(s => s.key === key);
            if (exists) {
                return prev.map(s => s.key === key ? { ...s, value } : s);
            } else {
                return [...prev, { key, value }];
            }
        });
        try {
            await api.put(`/api/v1/admin/settings/${key}`, { key, value, updated_at: new Date().toISOString() });
            alert("تم حفظ الإعدادات بنجاح");
        } catch (error) {
            console.error(error);
            alert("فشل حفظ الإعدادات");
            // Revert changes on error would be ideal, but simple alert for now
            fetchSettings();
        }
    };
    const getSettingValue = (key) => {
        return localSettings.find(s => s.key === key)?.value || '';
    };
    const handleLocalChange = (key, newValue) => {
        setLocalSettings(prev => {
            const exists = prev.find(s => s.key === key);
            if (exists) {
                return prev.map(s => s.key === key ? { ...s, value: newValue } : s);
            } else {
                return [...prev, { key, value: newValue }];
            }
        });
    };
    if (loading && localSettings.length === 0) return <div className="p-10 text-center text-slate-500 animate-pulse">جاري تحميل الإعدادات...</div>;
    return (
        <div className="space-y-6 animate-fade-in-up">
            {/* Maintenance Mode Card */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex items-start justify-between">
                    <div className="flex gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-rose-100 dark:bg-rose-900/30 flex items-center justify-center text-rose-600 dark:text-rose-400">
                            <AlertTriangle size={24} />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-slate-800 dark:text-white">وضع الصيانة (Maintenance Mode)</h3>
                            <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
                                عند تفعيل هذا الوضع، لن يتمكن أي مستخدم (باستثناء Super Admin) من تسجيل الدخول إلى النظام.
                                <br />استخدم هذا الوضع عند إجراء تحديثات حرجة للنظام.
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={handleToggleMaintenance}
                        className={`relative w-16 h-8 rounded-full transition-colors duration-300 ${getSettingValue('maintenance_mode') === 'true'
                            ? 'bg-rose-500'
                            : 'bg-slate-200 dark:bg-slate-700'
                            }`}
                    >
                        <span className={`absolute top-1 right-1 bg-white w-6 h-6 rounded-full shadow-sm transition-transform duration-300 ${getSettingValue('maintenance_mode') === 'true'
                            ? '-translate-x-8'
                            : 'translate-x-0'
                            }`} />
                    </button>
                </div>
            </div>
            {/* Global Banner Card */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex gap-4 mb-6">
                    <div className="w-12 h-12 rounded-2xl bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                        <Megaphone size={24} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">تنويه عام (Global Announcement)</h3>
                        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
                            النص المكتوب هنا سيظهر كشريط تنبيه في أعلى الصفحة لجميع المستخدمين (قريباً).
                        </p>
                    </div>
                </div>
                <div className="space-y-4">
                    <textarea
                        className="w-full p-4 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 min-h-[100px] text-slate-700 dark:text-slate-300 font-medium"
                        placeholder="أدخل نص التنويه هنا..."
                        value={getSettingValue('global_announcement')}
                        onChange={(e) => handleLocalChange('global_announcement', e.target.value)}
                    />
                    <div className="flex justify-end">
                        <button
                            onClick={() => updateSetting('global_announcement', getSettingValue('global_announcement'))}
                            className="flex items-center gap-2 px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold shadow-lg shadow-indigo-500/30 transition-all"
                        >
                            <Save size={18} />
                            حفظ التغييرات
                        </button>
                    </div>
                </div>
            </div>
            {/* Support Info Card */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex gap-4 mb-6">
                    <div className="w-12 h-12 rounded-2xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                        <Monitor size={24} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">بيانات الدعم الفني</h3>
                        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
                            تحديث أرقام التواصل وساعات العمل التي تظهر في صفحة الدعم الفني.
                        </p>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label className="block text-sm font-bold mb-2 text-slate-700 dark:text-slate-300">رقم الهاتف (للعرض)</label>
                        <input
                            type="text"
                            className="w-full p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700"
                            value={getSettingValue('support_phone')}
                            onChange={(e) => handleLocalChange('support_phone', e.target.value)}
                        />
                        <button onClick={() => updateSetting('support_phone', getSettingValue('support_phone'))} className="text-xs text-indigo-600 font-bold mt-2">حفظ</button>
                    </div>
                    <div>
                        <label className="block text-sm font-bold mb-2 text-slate-700 dark:text-slate-300">Whatsapp (أرقام فقط)</label>
                        <input
                            type="text"
                            className="w-full p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700"
                            value={getSettingValue('support_whatsapp')}
                            onChange={(e) => handleLocalChange('support_whatsapp', e.target.value)}
                        />
                        <button onClick={() => updateSetting('support_whatsapp', getSettingValue('support_whatsapp'))} className="text-xs text-indigo-600 font-bold mt-2">حفظ</button>
                    </div>
                    <div>
                        <label className="block text-sm font-bold mb-2 text-slate-700 dark:text-slate-300">البريد الإلكتروني</label>
                        <input
                            type="text"
                            className="w-full p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700"
                            value={getSettingValue('support_email')}
                            onChange={(e) => handleLocalChange('support_email', e.target.value)}
                        />
                        <button onClick={() => updateSetting('support_email', getSettingValue('support_email'))} className="text-xs text-indigo-600 font-bold mt-2">حفظ</button>
                    </div>
                    <div>
                        <label className="block text-sm font-bold mb-2 text-slate-700 dark:text-slate-300">ساعات العمل</label>
                        <input
                            type="text"
                            className="w-full p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700"
                            value={getSettingValue('support_working_hours')}
                            onChange={(e) => handleLocalChange('support_working_hours', e.target.value)}
                        />
                        <button onClick={() => updateSetting('support_working_hours', getSettingValue('support_working_hours'))} className="text-xs text-indigo-600 font-bold mt-2">حفظ</button>
                    </div>
                </div>
            </div>
        </div>
    );
};
export default SettingsManager;
