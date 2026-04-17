import { useState, useEffect } from 'react';
import { api } from '@/api';
import { Shield, Smartphone, Monitor, Smartphone as PhoneIcon, X } from 'lucide-react';
export default function SecuritySettings() {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [user, setUser] = useState(null);
    // 2FA Flow
    const [show2FAModal, setShow2FAModal] = useState(false);
    const [secret, setSecret] = useState('');
    const [otpUrl, setOtpUrl] = useState('');
    const [verificationCode, setVerificationCode] = useState('');
    useEffect(() => {
        fetchSecurityData();
    }, []);
    const fetchSecurityData = async () => {
        try {
            setLoading(true);
            const [userRes, sessionRes] = await Promise.all([
                api.get('/api/v1/users/me'),
                api.get('/api/v1/auth/sessions')
            ]);
            setUser(userRes.data);
            setSessions(sessionRes.data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };
    const handleRevokeSession = async (sessionId) => {
        if (!window.confirm("هل أنت متأكد من تسجيل خروج هذا الجهاز؟")) return;
        try {
            await api.delete(`/api/v1/auth/sessions/${sessionId}`);
            fetchSecurityData();
        } catch (error) {
            alert("فشل قطع الاتصال");
        }
    };
    const start2FASetup = async () => {
        try {
            const res = await api.post('/api/v1/auth/2fa/setup');
            setSecret(res.data.secret);
            setOtpUrl(res.data.otpauth_url);
            setShow2FAModal(true);
        } catch (error) {
            alert("فشل بدء إعداد المصادقة الثنائية");
        }
    };
    const handleVerify2FA = async () => {
        try {
            await api.post('/api/v1/auth/2fa/verify', null, {
                params: { code: verificationCode, secret: secret }
            });
            alert("تم تفعيل المصادقة الثنائية بنجاح!");
            setShow2FAModal(false);
            setSecret('');
            setVerificationCode('');
            fetchSecurityData();
        } catch (error) {
            alert("رمز التحقق غير صحيح");
        }
    };
    if (loading) return <div>جاري التحميل...</div>;
    return (
        <div className="space-y-8 animate-fade-in-up">
            {/* 2FA Status Card */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-4">
                        <div className={`p-4 rounded-2xl ${user.is_2fa_enabled ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-500'}`}>
                            <Shield size={32} />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-slate-800 dark:text-white">المصادقة الثنائية (2FA)</h3>
                            <p className="text-slate-500 mt-1">
                                {user.is_2fa_enabled
                                    ? "حسابك محمي بواسطة المصادقة الثنائية."
                                    : "تأمين حسابك يتطلب خطوة إضافية عند تسجيل الدخول."}
                            </p>
                        </div>
                    </div>
                    {!user.is_2fa_enabled ? (
                        <button
                            onClick={start2FASetup}
                            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold shadow-lg shadow-indigo-500/20"
                        >
                            تفعيل الحماية
                        </button>
                    ) : (
                        <span className="px-4 py-2 bg-emerald-100 text-emerald-700 rounded-lg font-bold">
                            الخدمة مفعلة
                        </span>
                    )}
                </div>
            </div>
            {/* Active Sessions List */}
            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                <div className="p-6 border-b border-slate-100 dark:border-slate-800">
                    <h3 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        <Monitor className="text-indigo-500" />
                        الجلسات النشطة (Active Sessions)
                    </h3>
                </div>
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                    {sessions.map(session => (
                        <div key={session.id} className="p-6 flex justify-between items-center hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-slate-100 dark:bg-slate-800 rounded-xl text-slate-500">
                                    {session.device_info?.toLowerCase().includes('mobile') ? <PhoneIcon /> : <Monitor />}
                                </div>
                                <div>
                                    <p className="font-bold text-slate-800 dark:text-white dir-ltr text-left">
                                        {session.ip_address}
                                        {session.token_hash /* Ideally don't show hash, show 'Current Session' if matches */}
                                    </p>
                                    <p className="text-sm text-slate-500 mt-1" dir="ltr">
                                        Last active: {new Date(session.last_active_at).toLocaleString()}
                                    </p>
                                    <p className="text-xs text-slate-400 mt-0.5 truncate max-w-md" dir="ltr">
                                        {session.user_agent}
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={() => handleRevokeSession(session.id)}
                                className="text-red-500 hover:bg-red-50 px-4 py-2 rounded-lg font-bold text-sm transition-colors"
                            >
                                تسجيل خروج
                            </button>
                        </div>
                    ))}
                    {sessions.length === 0 && (
                        <div className="p-8 text-center text-slate-400">لا توجد جلسات نشطة أخرى.</div>
                    )}
                </div>
            </div>
            {/* 2FA Setup Modal */}
            {show2FAModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 w-full max-w-md shadow-2xl space-y-6">
                        <div className="flex justify-between items-center">
                            <h3 className="text-xl font-bold text-slate-800 dark:text-white">إعداد المصادقة الثنائية</h3>
                            <button onClick={() => setShow2FAModal(false)}><X className="text-slate-400" /></button>
                        </div>
                        <div className="space-y-4 text-center">
                            <div className="bg-slate-100 p-4 rounded-xl mx-auto inline-block">
                                {/* In real app: <QRCode value={otpUrl} /> */}
                                <Smartphone size={64} className="text-slate-400 mx-auto" />
                                <p className="text-xs text-slate-500 mt-2 font-mono break-all">{secret}</p>
                            </div>
                            <p className="text-slate-600 dark:text-slate-300 text-sm">
                                امسح الكود باستخدام تطبيق Google Authenticator أو أدخل الرمز السري يدوياً (محاكاة: أدخل 123456).
                            </p>
                            <input
                                type="text"
                                placeholder="أدخل الرمز (مثال: 123456)"
                                className="w-full text-center text-2xl tracking-widest px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 outline-none font-mono"
                                value={verificationCode}
                                onChange={(e) => setVerificationCode(e.target.value)}
                            />
                            <button
                                onClick={handleVerify2FA}
                                className="w-full py-3 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl font-bold shadow-lg"
                            >
                                تفعيل وتأكيد
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
