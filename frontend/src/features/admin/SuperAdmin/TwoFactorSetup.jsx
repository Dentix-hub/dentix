import { useState } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import { Shield, Smartphone, Check, X, Copy, AlertCircle } from 'lucide-react';
import { toast, ConfirmDialog } from '@/shared/ui';
import { useTranslation } from 'react-i18next';

export default function TwoFactorSetup({ isEnabled, onToggle }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    const [setupData, setSetupData] = useState(null);
    const [verificationCode, setVerificationCode] = useState('');
    const [loading, setLoading] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [disableConfirmOpen, setDisableConfirmOpen] = useState(false);

    const startSetup = async () => {
        setLoading(true);
        try {
            const res = await api.post('/api/v1/auth/2fa/setup');
            const data = res.data?.data || res.data;
            if (data?.secret && data?.qr_code) {
                setSetupData(data);
                setShowConfirm(true);
            } else {
                toast.error(t('super_admin.two_factor.invalid_setup_payload') || 'بيانات إعداد المصادقة غير مكتملة');
            }
        } catch (err) {
            logger.error('2FA setup failed:', err);
            toast.error(err.response?.data?.detail || t('super_admin.two_factor.setup_fail') || 'فشل بدء إعداد التحقق بخطوتين');
        } finally {
            setLoading(false);
        }
    };

    const cancelSetup = () => {
        setShowConfirm(false);
        setSetupData(null);
        setVerificationCode('');
    };

    const verifyAndEnable = async () => {
        if (!setupData?.secret) {
            toast.error(t('super_admin.two_factor.missing_secret') || 'الرمز السري غير متوفر، يرجى إعادة بدء الإعداد');
            return;
        }

        if (verificationCode.length !== 6) {
            toast.error(t('super_admin.two_factor.code_length_error') || 'يرجى إدخال الرمز المكون من 6 أرقام');
            return;
        }

        setLoading(true);
        try {
            await api.post('/api/v1/auth/2fa/verify', {
                code: verificationCode,
                secret: setupData.secret
            });
            toast.success(t('super_admin.two_factor.enable_success') || 'تم تفعيل التحقق بخطوتين بنجاح');
            setShowConfirm(false);
            setSetupData(null);
            setVerificationCode('');
            if (onToggle) onToggle(true);
        } catch (err) {
            logger.error('2FA verify failed:', err);
            toast.error(err.response?.data?.detail || t('super_admin.two_factor.invalid_code') || 'رمز التحقق غير صحيح');
        } finally {
            setLoading(false);
        }
    };

    const handleDisableClick = () => {
        setDisableConfirmOpen(true);
    };

    const confirmDisable2FA = async () => {
        setLoading(true);
        try {
            await api.delete('/api/v1/auth/2fa/disable');
            toast.success(t('super_admin.two_factor.disable_success') || 'تم تعطيل التحقق بخطوتين');
            setDisableConfirmOpen(false);
            if (onToggle) onToggle(false);
        } catch (err) {
            logger.error('2FA disable failed:', err);
            toast.error(err.response?.data?.detail || t('super_admin.two_factor.disable_fail') || 'فشل تعطيل التحقق بخطوتين');
        } finally {
            setLoading(false);
        }
    };

    const copySecret = async () => {
        if (!setupData?.secret) return;
        try {
            if (navigator?.clipboard?.writeText) {
                await navigator.clipboard.writeText(setupData.secret);
                toast.success(t('super_admin.two_factor.secret_copied') || 'تم نسخ الرمز السري');
            } else {
                toast.error(t('super_admin.two_factor.clipboard_unsupported') || 'الحافظة غير مدعومة في متصفحك');
            }
        } catch (err) {
            logger.error('Failed to copy secret:', err);
            toast.error(t('super_admin.two_factor.clipboard_fail') || 'فشل نسخ الرمز السري');
        }
    };

    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-100 dark:border-slate-800 p-8 shadow-sm" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="flex items-center gap-4 mb-6">
                <div className={`p-4 rounded-2xl ${isEnabled ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400' : 'bg-slate-50 dark:bg-slate-800 text-slate-400'}`}>
                    <Shield size={32} />
                </div>
                <div className="text-start">
                    <h3 className="text-xl font-black text-slate-800 dark:text-white">
                        {t('super_admin.two_factor.title') || 'التحقق بخطوتين (2FA)'}
                    </h3>
                    <p className="text-slate-500 dark:text-slate-400 font-bold text-sm">
                        {t('super_admin.two_factor.subtitle') || 'تأمين حسابك باستخدام تطبيق Authenticator'}
                    </p>
                </div>
                <div className="ms-auto">
                    {isEnabled ? (
                        <span className="px-4 py-1.5 bg-emerald-500 text-white text-xs font-black rounded-full shadow-lg shadow-emerald-500/20">
                            {t('common.enabled') || 'مفعل'}
                        </span>
                    ) : (
                        <span className="px-4 py-1.5 bg-slate-100 dark:bg-slate-800 text-slate-400 text-xs font-black rounded-full">
                            {t('common.disabled') || 'غير مفعل'}
                        </span>
                    )}
                </div>
            </div>

            {!isEnabled ? (
                !showConfirm ? (
                    <div className="space-y-4">
                        <p className="text-slate-600 dark:text-slate-400 font-medium text-sm leading-relaxed">
                            {t('super_admin.two_factor.desc') || 'يضيف التحقق بخطوتين طبقة إضافية من الأمان لحسابك. عند تسجيل الدخول، ستحتاج إلى إدخال رمز من تطبيق Google Authenticator أو أي تطبيق مماثل.'}
                        </p>
                        <button 
                            type="button"
                            onClick={startSetup}
                            disabled={loading}
                            className="w-full py-4 bg-slate-800 hover:bg-slate-900 disabled:bg-slate-400 text-white rounded-2xl font-black shadow-xl transition-all flex items-center justify-center gap-2"
                        >
                            <Smartphone size={20} />
                            {loading ? (t('common.loading') || 'جاري التحميل...') : (t('super_admin.two_factor.start_setup') || 'إعداد التحقق بخطوتين')}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-6 animate-in slide-in-from-right duration-300 text-start">
                        {setupData && (
                            <div className="flex flex-col md:flex-row gap-8 items-center">
                                {setupData.qr_code && (
                                    <div className="p-4 bg-white rounded-3xl border-4 border-slate-50 shadow-inner">
                                        <img 
                                            src={`data:image/png;base64,${setupData.qr_code}`} 
                                            alt="2FA QR Code" 
                                            className="w-48 h-48"
                                        />
                                    </div>
                                )}
                                <div className="flex-1 space-y-4">
                                    <div className="space-y-1">
                                        <h4 className="font-black text-slate-800 dark:text-white">
                                            {t('super_admin.two_factor.scan_qr') || 'امسح رمز الاستجابة السريعة'}
                                        </h4>
                                        <p className="text-xs text-slate-500 font-bold">
                                            {t('super_admin.two_factor.scan_qr_desc') || 'استخدم تطبيق Google Authenticator لمسح الكود أعلاه'}
                                        </p>
                                    </div>
                                    
                                    {setupData.secret && (
                                        <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 relative overflow-hidden group">
                                            <p className="text-[10px] text-slate-400 font-black uppercase tracking-widest mb-1">
                                                {t('super_admin.two_factor.manual_secret') || 'الرمز السري اليدوي'}
                                            </p>
                                            <div className="flex items-center justify-between">
                                                <code className="text-sm font-black text-slate-700 dark:text-slate-200 tracking-wider select-all">{setupData.secret}</code>
                                                <button 
                                                    type="button" 
                                                    onClick={copySecret} 
                                                    className="p-2 hover:bg-white dark:hover:bg-slate-700 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
                                                    aria-label={t('common.copy') || 'نسخ'}
                                                >
                                                    <Copy size={16} />
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        <div className="space-y-2">
                            <label htmlFor="two_factor_verification_code" className="block text-sm font-black text-slate-600 dark:text-slate-300">
                                {t('super_admin.two_factor.enter_code') || 'أدخل الرمز المكون من 6 أرقام للتأكيد'}
                            </label>
                            <input 
                                id="two_factor_verification_code"
                                type="text"
                                maxLength="6"
                                placeholder="000000"
                                value={verificationCode}
                                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
                                className="w-full p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border-2 border-transparent focus:border-emerald-500 outline-none text-center text-2xl font-black tracking-[0.5em] text-slate-800 dark:text-slate-200"
                            />
                        </div>

                        <div className="flex gap-4">
                            <button 
                                type="button"
                                onClick={verifyAndEnable}
                                disabled={loading || verificationCode.length !== 6}
                                className="flex-1 py-4 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-400 text-white rounded-2xl font-black shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-2"
                            >
                                <Check size={20} />
                                {loading ? (t('common.saving') || 'جاري التفعيل...') : (t('super_admin.two_factor.activate_now') || 'تفعيل الآن')}
                            </button>
                            <button 
                                type="button"
                                onClick={cancelSetup}
                                disabled={loading}
                                className="px-6 py-4 bg-slate-100 dark:bg-slate-800 text-slate-500 rounded-2xl font-bold hover:bg-slate-200 dark:hover:bg-slate-700"
                            >
                                {t('common.cancel') || 'إلغاء'}
                            </button>
                        </div>
                    </div>
                )
            ) : (
                <div className="space-y-6">
                    <div className="p-4 bg-emerald-50 dark:bg-emerald-900/10 rounded-2xl border border-emerald-100 dark:border-emerald-900/20 flex items-start gap-4">
                        <AlertCircle className="text-emerald-500 mt-1 shrink-0" size={20} />
                        <p className="text-sm font-bold text-emerald-800 dark:text-emerald-400 leading-relaxed text-start">
                            {t('super_admin.two_factor.enabled_desc') || 'حسابك محمي حالياً بواسطة التحقق بخطوتين. سيُطلب منك إدخال الرمز في كل مرة تقوم فيها بتسجيل الدخول من جهاز جديد.'}
                        </p>
                    </div>
                    <button 
                        type="button"
                        onClick={handleDisableClick}
                        disabled={loading}
                        className="w-full py-4 border-2 border-red-100 dark:border-red-900/20 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 rounded-2xl font-black transition-all flex items-center justify-center gap-2"
                    >
                        <X size={20} />
                        {loading ? (t('common.loading') || 'جاري التعطيل...') : (t('super_admin.two_factor.disable_btn') || 'تعطيل التحقق بخطوتين')}
                    </button>
                </div>
            )}

            {/* Confirm Dialog for Disabling 2FA */}
            <ConfirmDialog
                isOpen={disableConfirmOpen}
                onClose={() => setDisableConfirmOpen(false)}
                onConfirm={confirmDisable2FA}
                title={t('super_admin.two_factor.disable_confirm_title') || 'تأكيد تعطيل التحقق بخطوتين'}
                message={t('super_admin.two_factor.disable_confirm_msg') || 'هل أنت متأكد من تعطيل التحقق بخطوتين؟ هذا سيقلل من أمان حسابك.'}
                confirmText={t('common.confirm') || 'تأكيد'}
                cancelText={t('common.cancel') || 'إلغاء'}
                variant="danger"
                isLoading={loading}
            />
        </div>
    );
}
