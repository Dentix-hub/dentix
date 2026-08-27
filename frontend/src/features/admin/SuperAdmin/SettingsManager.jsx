import { useState, useEffect } from 'react';
import logger from '@/utils/logger';
import { Save, AlertTriangle, Monitor, Megaphone } from 'lucide-react';
import { api } from '@/api';
import { toast, ConfirmDialog } from '@/shared/ui';
import { useTranslation } from 'react-i18next';

const SettingsManager = ({ settings, fetchData }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    const [localSettings, setLocalSettings] = useState(Array.isArray(settings) ? settings : []);
    const [loadingKey, setLoadingKey] = useState(null);
    const [maintenanceConfirmOpen, setMaintenanceConfirmOpen] = useState(false);

    useEffect(() => {
        if (Array.isArray(settings)) {
            setLocalSettings(settings);
        }
    }, [settings]);

    const getSettingValue = (key) => {
        return localSettings.find(s => s.key === key)?.value || '';
    };

    const isMaintenanceOn = getSettingValue('maintenance_mode') === 'true';

    const handleToggleMaintenance = () => {
        setMaintenanceConfirmOpen(true);
    };

    const confirmToggleMaintenance = async () => {
        const nextValue = isMaintenanceOn ? 'false' : 'true';
        await updateSetting('maintenance_mode', nextValue);
    };

    const updateSetting = async (key, value) => {
        const originalSavedSetting = (Array.isArray(settings) ? settings : []).find(s => s.key === key)?.value || '';
        setLoadingKey(key);

        // Optimistic update
        setLocalSettings(prev => {
            const exists = prev.find(s => s.key === key);
            if (exists) {
                return prev.map(s => s.key === key ? { ...s, value } : s);
            }
            return [...prev, { key, value }];
        });

        try {
            await api.put(`/api/v1/admin/settings/${key}`, { key, value, updated_at: new Date().toISOString() });
            if (fetchData) fetchData();
            toast.success(t('super_admin.settings.save_success') || 'تم حفظ الإعدادات بنجاح');
        } catch (error) {
            logger.error('Failed to update setting:', error);
            // Rollback to original saved value on failure
            setLocalSettings(prev => {
                const exists = prev.find(s => s.key === key);
                if (exists) {
                    return prev.map(s => s.key === key ? { ...s, value: originalSavedSetting } : s);
                }
                return prev.filter(s => s.key !== key);
            });
            const detail = error.response?.data?.detail || error.message || t('super_admin.settings.save_fail') || 'فشل حفظ الإعدادات';
            toast.error(detail);
        } finally {
            setLoadingKey(null);
        }
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

    return (
        <div className="space-y-6 animate-fade-in-up" dir={isRtl ? 'rtl' : 'ltr'}>

            {/* Maintenance Mode Card */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex items-start justify-between">
                    <div className="flex gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-rose-100 dark:bg-rose-900/30 flex items-center justify-center text-rose-600 dark:text-rose-400 shrink-0">
                            <AlertTriangle size={24} />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-slate-800 dark:text-white">
                                {t('super_admin.settings.maintenance_title') || 'وضع الصيانة (Maintenance Mode)'}
                            </h3>
                            <p className="text-slate-500 dark:text-slate-400 text-sm mt-1 leading-relaxed">
                                {t('super_admin.settings.maintenance_desc') || 'عند تفعيل هذا الوضع، لن يتمكن أي مستخدم (باستثناء Super Admin) من تسجيل الدخول إلى النظام. استخدم هذا الوضع عند إجراء تحديثات حرجة للنظام.'}
                            </p>
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={handleToggleMaintenance}
                        disabled={loadingKey === 'maintenance_mode'}
                        className={`relative w-16 h-8 rounded-full transition-colors duration-300 focus:outline-none shrink-0 ${isMaintenanceOn ? 'bg-rose-500' : 'bg-slate-200 dark:bg-slate-700'}`}
                        aria-label={t('super_admin.settings.maintenance_toggle') || 'تبديل وضع الصيانة'}
                    >
                        <span className={`absolute top-1 end-1 bg-white w-6 h-6 rounded-full shadow-sm transition-transform duration-300 ${isMaintenanceOn ? '-translate-x-8' : 'translate-x-0'}`} />
                    </button>
                </div>
            </div>

            {/* Global Banner Card */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex gap-4 mb-6">
                    <div className="w-12 h-12 rounded-2xl bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0">
                        <Megaphone size={24} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">
                            {t('super_admin.settings.announcement_title') || 'تنويه عام (Global Announcement)'}
                        </h3>
                        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
                            {t('super_admin.settings.announcement_desc') || 'النص المكتوب هنا سيظهر كشريط تنبيه عام في أعلى واجهة التطبيق لجميع المستخدمين.'}
                        </p>
                    </div>
                </div>

                <div className="space-y-4">
                    <textarea
                        className="w-full p-4 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 min-h-[100px] text-slate-700 dark:text-slate-300 font-medium"
                        placeholder={t('super_admin.settings.announcement_placeholder') || "أدخل نص التنويه العام هنا..."}
                        value={getSettingValue('global_announcement')}
                        onChange={(e) => handleLocalChange('global_announcement', e.target.value)}
                    />
                    <div className="flex justify-end">
                        <button
                            type="button"
                            onClick={() => updateSetting('global_announcement', getSettingValue('global_announcement'))}
                            disabled={loadingKey === 'global_announcement'}
                            className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-400 text-white rounded-xl font-bold shadow-lg shadow-indigo-500/30 transition-all"
                        >
                            <Save size={18} />
                            {loadingKey === 'global_announcement' ? (t('common.saving') || 'جاري الحفظ...') : (t('super_admin.settings.save_changes') || 'حفظ التغييرات')}
                        </button>
                    </div>
                </div>
            </div>

            {/* Support Info Card */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex gap-4 mb-6">
                    <div className="w-12 h-12 rounded-2xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0">
                        <Monitor size={24} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">
                            {t('super_admin.settings.support_info_title') || 'بيانات الدعم الفني'}
                        </h3>
                        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
                            {t('super_admin.settings.support_info_desc') || 'تحديث أرقام التواصل وساعات العمل التي تظهر في صفحة الدعم الفني العامة.'}
                        </p>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <label htmlFor="setting_support_phone" className="block text-sm font-bold text-slate-700 dark:text-slate-300">
                            {t('super_admin.settings.support_phone') || 'رقم الهاتف (للعرض)'}
                        </label>
                        <input
                            id="setting_support_phone"
                            type="text"
                            className="w-full p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 font-medium outline-none focus:ring-2 focus:ring-emerald-500"
                            value={getSettingValue('support_phone')}
                            onChange={(e) => handleLocalChange('support_phone', e.target.value)}
                        />
                        <button
                            type="button"
                            onClick={() => updateSetting('support_phone', getSettingValue('support_phone'))}
                            disabled={loadingKey === 'support_phone'}
                            className="text-xs text-indigo-600 dark:text-indigo-400 font-bold hover:underline"
                        >
                            {loadingKey === 'support_phone' ? (t('common.saving') || 'جاري الحفظ...') : (t('common.save') || 'حفظ')}
                        </button>
                    </div>

                    <div className="space-y-2">
                        <label htmlFor="setting_support_whatsapp" className="block text-sm font-bold text-slate-700 dark:text-slate-300">
                            {t('super_admin.settings.support_whatsapp') || 'Whatsapp (أرقام فقط)'}
                        </label>
                        <input
                            id="setting_support_whatsapp"
                            type="text"
                            className="w-full p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 font-medium outline-none focus:ring-2 focus:ring-emerald-500"
                            value={getSettingValue('support_whatsapp')}
                            onChange={(e) => handleLocalChange('support_whatsapp', e.target.value)}
                        />
                        <button
                            type="button"
                            onClick={() => updateSetting('support_whatsapp', getSettingValue('support_whatsapp'))}
                            disabled={loadingKey === 'support_whatsapp'}
                            className="text-xs text-indigo-600 dark:text-indigo-400 font-bold hover:underline"
                        >
                            {loadingKey === 'support_whatsapp' ? (t('common.saving') || 'جاري الحفظ...') : (t('common.save') || 'حفظ')}
                        </button>
                    </div>

                    <div className="space-y-2">
                        <label htmlFor="setting_support_email" className="block text-sm font-bold text-slate-700 dark:text-slate-300">
                            {t('super_admin.settings.support_email') || 'البريد الإلكتروني'}
                        </label>
                        <input
                            id="setting_support_email"
                            type="email"
                            className="w-full p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 font-medium outline-none focus:ring-2 focus:ring-emerald-500"
                            value={getSettingValue('support_email')}
                            onChange={(e) => handleLocalChange('support_email', e.target.value)}
                        />
                        <button
                            type="button"
                            onClick={() => updateSetting('support_email', getSettingValue('support_email'))}
                            disabled={loadingKey === 'support_email'}
                            className="text-xs text-indigo-600 dark:text-indigo-400 font-bold hover:underline"
                        >
                            {loadingKey === 'support_email' ? (t('common.saving') || 'جاري الحفظ...') : (t('common.save') || 'حفظ')}
                        </button>
                    </div>

                    <div className="space-y-2">
                        <label htmlFor="setting_support_working_hours" className="block text-sm font-bold text-slate-700 dark:text-slate-300">
                            {t('super_admin.settings.support_working_hours') || 'ساعات العمل'}
                        </label>
                        <input
                            id="setting_support_working_hours"
                            type="text"
                            className="w-full p-3 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 font-medium outline-none focus:ring-2 focus:ring-emerald-500"
                            value={getSettingValue('support_working_hours')}
                            onChange={(e) => handleLocalChange('support_working_hours', e.target.value)}
                        />
                        <button
                            type="button"
                            onClick={() => updateSetting('support_working_hours', getSettingValue('support_working_hours'))}
                            disabled={loadingKey === 'support_working_hours'}
                            className="text-xs text-indigo-600 dark:text-indigo-400 font-bold hover:underline"
                        >
                            {loadingKey === 'support_working_hours' ? (t('common.saving') || 'جاري الحفظ...') : (t('common.save') || 'حفظ')}
                        </button>
                    </div>
                </div>
            </div>

            {/* Confirm Dialog for Maintenance Mode Toggle */}
            <ConfirmDialog
                isOpen={maintenanceConfirmOpen}
                onClose={() => setMaintenanceConfirmOpen(false)}
                onConfirm={confirmToggleMaintenance}
                title={t('super_admin.settings.maintenance_confirm_title') || 'تأكيد تغيير وضع الصيانة'}
                message={isMaintenanceOn
                    ? (t('super_admin.settings.maintenance_disable_confirm') || 'هل أنت متأكد من إيقاف وضع الصيانة والسماح للجميع بتسجيل الدخول؟')
                    : (t('super_admin.settings.maintenance_enable_confirm') || 'هل أنت متأكد من تفعيل وضع الصيانة؟ سيتم منع جميع المستخدمين (غير المسؤولين) من الدخول.')}
                confirmText={t('common.confirm') || 'تأكيد'}
                cancelText={t('common.cancel') || 'إلغاء'}
                variant={isMaintenanceOn ? 'primary' : 'danger'}
                isLoading={loadingKey === 'maintenance_mode'}
            />
        </div>
    );
};

export default SettingsManager;
