import React, { useState } from 'react';
import { api } from '@/api';
import { Shield, Smartphone, Check, X, Copy, AlertCircle } from 'lucide-react';
import { toast } from '@/shared/ui';

export default function TwoFactorSetup({ isEnabled, onToggle }) {
    const [setupData, setSetupData] = useState(null);
    const [verificationCode, setVerificationCode] = useState('');
    const [loading, setLoading] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);

    const startSetup = async () => {
        setLoading(true);
        try {
            const res = await api.post('/api/v1/auth/2fa/setup');
            setSetupData(res.data);
            setShowConfirm(true);
        } catch (err) {
            toast.error('فشل بدء إعداد التحقق بخطوتين');
        } finally {
            setLoading(false);
        }
    };

    const verifyAndEnable = async () => {
        if (verificationCode.length !== 6) {
            toast.error('يرجى إدخال الرمز المكون من 6 أرقام');
            return;
        }
        setLoading(true);
        try {
            await api.post('/api/v1/auth/2fa/verify', {
                code: verificationCode,
                secret: setupData.secret
            });
            toast.success('تم تفعيل التحقق بخطوتين بنجاح');
            setShowConfirm(false);
            setSetupData(null);
            onToggle(true);
        } catch (err) {
            toast.error('رمز التحقق غير صحيح');
        } finally {
            setLoading(false);
        }
    };

    const disable2FA = async () => {
        if (!window.confirm('هل أنت متأكد من تعطيل التحقق بخطوتين؟ هذا سيقلل من أمان حسابك.')) return;
        setLoading(true);
        try {
            await api.delete('/api/v1/auth/2fa/disable');
            toast.success('تم تعطيل التحقق بخطوتين');
            onToggle(false);
        } catch (err) {
            toast.error('فشل تعطيل التحقق بخطوتين');
        } finally {
            setLoading(false);
        }
    };

    const copySecret = () => {
        navigator.clipboard.writeText(setupData.secret);
        toast.success('تم نسخ الرمز السري');
    };

    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-100 dark:border-slate-800 p-8 shadow-sm">
            <div className="flex items-center gap-4 mb-6">
                <div className={`p-4 rounded-2xl ${isEnabled ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-50 text-slate-400'}`}>
                    <Shield size={32} />
                </div>
                <div className="text-right">
                    <h3 className="text-xl font-black text-slate-800 dark:text-white">التحقق بخطوتين (2FA)</h3>
                    <p className="text-slate-500 font-bold text-sm">تأمين حسابك باستخدام تطبيق Authenticator</p>
                </div>
                <div className="me-auto">
                    {isEnabled ? (
                        <span className="px-4 py-1.5 bg-emerald-500 text-white text-xs font-black rounded-full shadow-lg shadow-emerald-500/20">مفعل</span>
                    ) : (
                        <span className="px-4 py-1.5 bg-slate-100 dark:bg-slate-800 text-slate-400 text-xs font-black rounded-full">غير مفعل</span>
                    )}
                </div>
            </div>

            {!isEnabled ? (
                !showConfirm ? (
                    <div className="space-y-4">
                        <p className="text-slate-600 dark:text-slate-400 font-medium text-sm leading-relaxed">
                            يضيف التحقق بخطوتين طبقة إضافية من الأمان لحسابك. عند تسجيل الدخول، ستحتاج إلى إدخال رمز من تطبيق Google Authenticator أو أي تطبيق مماثل.
                        </p>
                        <button 
                            onClick={startSetup}
                            disabled={loading}
                            className="w-full py-4 bg-slate-800 hover:bg-slate-900 text-white rounded-2xl font-black shadow-xl transition-all flex items-center justify-center gap-2"
                        >
                            <Smartphone size={20} />
                            إعداد التحقق بخطوتين
                        </button>
                    </div>
                ) : (
                    <div className="space-y-6 animate-in slide-in-from-right duration-300 text-right">
                        <div className="flex flex-col md:flex-row gap-8 items-center">
                            <div className="p-4 bg-white rounded-3xl border-4 border-slate-50 shadow-inner">
                                <img 
                                    src={`data:image/png;base64,${setupData.qr_code}`} 
                                    alt="2FA QR Code" 
                                    className="w-48 h-48"
                                />
                            </div>
                            <div className="flex-1 space-y-4">
                                <div className="space-y-1">
                                    <h4 className="font-black text-slate-800 dark:text-white">امسح رمز الاستجابة السريعة</h4>
                                    <p className="text-xs text-slate-500 font-bold">استخدم تطبيق Google Authenticator لمسح الكود أعلاه</p>
                                </div>
                                
                                <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 relative overflow-hidden group">
                                    <p className="text-[10px] text-slate-400 font-black uppercase tracking-widest mb-1">الرمز السري اليدوي</p>
                                    <div className="flex items-center justify-between">
                                        <code className="text-sm font-black text-slate-700 dark:text-slate-200 tracking-wider">{setupData.secret}</code>
                                        <button onClick={copySecret} className="p-2 hover:bg-white dark:hover:bg-slate-700 rounded-lg text-slate-400">
                                            <Copy size={16} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="block text-sm font-black text-slate-600">أدخل الرمز المكون من 6 أرقام للتأكيد</label>
                            <input 
                                type="text"
                                maxLength="6"
                                placeholder="000000"
                                value={verificationCode}
                                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
                                className="w-full p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border-2 border-transparent focus:border-emerald-500 outline-none text-center text-2xl font-black tracking-[0.5em]"
                            />
                        </div>

                        <div className="flex gap-4">
                            <button 
                                onClick={verifyAndEnable}
                                disabled={loading}
                                className="flex-1 py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-black shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-2"
                            >
                                <Check size={20} />
                                تفعيل الآن
                            </button>
                            <button 
                                onClick={() => setShowConfirm(false)}
                                className="px-6 py-4 bg-slate-100 dark:bg-slate-800 text-slate-500 rounded-2xl font-bold hover:bg-slate-200"
                            >
                                إلغاء
                            </button>
                        </div>
                    </div>
                )
            ) : (
                <div className="space-y-6">
                    <div className="p-4 bg-emerald-50 dark:bg-emerald-900/10 rounded-2xl border border-emerald-100 dark:border-emerald-900/20 flex items-start gap-4">
                        <AlertCircle className="text-emerald-500 mt-1 shrink-0" size={20} />
                        <p className="text-sm font-bold text-emerald-800 dark:text-emerald-400 leading-relaxed text-right">
                            حسابك محمي حالياً بواسطة التحقق بخطوتين. سيُطلب منك إدخال الرمز في كل مرة تقوم فيها بتسجيل الدخول من جهاز جديد.
                        </p>
                    </div>
                    <button 
                        onClick={disable2FA}
                        disabled={loading}
                        className="w-full py-4 border-2 border-red-100 dark:border-red-900/20 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 rounded-2xl font-black transition-all flex items-center justify-center gap-2"
                    >
                        <X size={20} />
                        تعطيل التحقق بخطوتين
                    </button>
                </div>
            )}
        </div>
    );
}
