import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, Send, CheckCircle, AlertCircle } from 'lucide-react';
import { forgotPassword } from '../api';
export default function ForgotPassword() {
    const { t } = useTranslation();
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');
    const [devToken, setDevToken] = useState(null);
    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!email) return setError(t('auth.forgot_password.errors.email_required'));
        setLoading(true);
        setError('');
        try {
            const res = await forgotPassword(email);
            setSuccess(true);
            // For development - show token if SMTP not configured
            if (res.data.dev_token) {
                setDevToken(res.data.dev_token);
            }
        } catch (err) {
            setError(err.response?.data?.detail || t('auth.forgot_password.errors.generic'));
        } finally {
            setLoading(false);
        }
    };
    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-100 to-sky-50 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="text-5xl mb-2">🏥</div>
                    <h1 className="text-3xl font-black text-slate-800 dark:text-white">DENTIX</h1>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-3xl shadow-2xl p-8">
                    {!success ? (
                        <>
                            <div className="text-center mb-6">
                                <div className="w-16 h-16 bg-sky-100 dark:bg-sky-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <Mail className="text-sky-500" size={32} />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">{t('auth.forgot_password.title')}</h2>
                                <p className="text-slate-500">{t('auth.forgot_password.subtitle')}</p>
                            </div>
                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">{t('auth.forgot_password.email')}</label>
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="example@email.com"
                                        className="w-full p-4 bg-slate-50 dark:bg-slate-700 rounded-xl border border-slate-200 dark:border-slate-600 outline-none focus:border-sky-500 transition-colors text-left"
                                        dir="ltr"
                                    />
                                </div>
                                {error && (
                                    <div className="flex items-center gap-2 text-red-500 bg-red-50 dark:bg-red-500/10 p-3 rounded-xl">
                                        <AlertCircle size={18} />
                                        <span className="text-sm">{error}</span>
                                    </div>
                                )}
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full py-4 bg-gradient-to-r from-sky-500 to-blue-600 text-white font-bold rounded-xl hover:from-sky-600 hover:to-blue-700 transition-all shadow-lg shadow-sky-500/30 flex items-center justify-center gap-2 disabled:opacity-50"
                                >
                                    {loading ? (
                                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                                    ) : (
                                        <>
                                            <Send size={18} />
                                            {t('auth.forgot_password.submit')}
                                        </>
                                    )}
                                </button>
                            </form>
                        </>
                    ) : (
                        <div className="text-center">
                            <div className="w-20 h-20 bg-emerald-100 dark:bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                                <CheckCircle className="text-emerald-500" size={40} />
                            </div>
                            <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">{t('auth.forgot_password.success_title')}</h2>
                            <p className="text-slate-500 mb-4">{t('auth.forgot_password.success_msg')}</p>
                            {devToken && (
                                <div className="bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-xl p-4 mb-4 text-left" dir="ltr">
                                    <p className="text-amber-600 text-xs font-bold mb-2">⚠️ Development Mode (SMTP not configured)</p>
                                    <p className="text-xs text-slate-600 mb-2">Reset Link:</p>
                                    <a
                                        href={`/reset-password?token=${devToken}`}
                                        className="text-sky-500 text-sm break-all hover:underline"
                                    >
                                        /reset-password?token={devToken}
                                    </a>
                                </div>
                            )}
                        </div>
                    )}
                    <div className="mt-6 text-center">
                        <Link to="/login" className="inline-flex items-center gap-2 text-sky-500 hover:text-sky-600 font-bold">
                            <ArrowLeft size={16} />
                            {t('auth.forgot_password.back_to_login')}
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
