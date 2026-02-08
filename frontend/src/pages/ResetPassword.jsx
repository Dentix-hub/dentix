import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Lock, Eye, EyeOff, CheckCircle, AlertCircle, ArrowLeft } from 'lucide-react';
import { verifyResetToken, resetPassword } from '../api';

export default function ResetPassword() {
    const { t } = useTranslation();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const token = searchParams.get('token');

    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [tokenValid, setTokenValid] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!token) {
            setError(t('auth.reset_password.errors.invalid_link'));
            setLoading(false);
            return;
        }

        // Verify token on mount
        verifyResetToken(token)
            .then(res => {
                setTokenValid(res.data.valid);
                if (!res.data.valid) {
                    setError(res.data.message || t('auth.reset_password.errors.invalid_link'));
                }
            })
            .catch(() => {
                setError(t('auth.reset_password.errors.verification_error'));
            })
            .finally(() => {
                setLoading(false);
            });
    }, [token]);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!password) return setError(t('auth.reset_password.errors.password_required'));
        if (password.length < 6) return setError(t('auth.reset_password.errors.password_min_length'));
        if (password !== confirmPassword) return setError(t('auth.reset_password.errors.password_mismatch'));


        setSubmitting(true);
        setError('');

        try {
            await resetPassword(token, password);
            setSuccess(true);
            setTimeout(() => navigate('/login'), 3000);
        } catch (err) {
            setError(err.response?.data?.detail || t('auth.forgot_password.errors.generic'));
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-100 to-sky-50 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-sky-500 border-t-transparent"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-100 to-sky-50 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="text-5xl mb-2">🏥</div>
                    <h1 className="text-3xl font-black text-slate-800 dark:text-white">DENTIX</h1>
                </div>

                <div className="bg-white dark:bg-slate-800 rounded-3xl shadow-2xl p-8">
                    {success ? (
                        <div className="text-center">
                            <div className="w-20 h-20 bg-emerald-100 dark:bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                                <CheckCircle className="text-emerald-500" size={40} />
                            </div>
                            <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">{t('auth.reset_password.success_title')}</h2>
                            <p className="text-slate-500 mb-4">{t('auth.reset_password.success_msg')}</p>
                        </div>
                    ) : !tokenValid ? (
                        <div className="text-center">
                            <div className="w-20 h-20 bg-red-100 dark:bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                                <AlertCircle className="text-red-500" size={40} />
                            </div>
                            <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">{t('auth.reset_password.invalid_link_title')}</h2>
                            <p className="text-slate-500 mb-4">{error}</p>
                            <Link to="/forgot-password" className="text-sky-500 hover:underline font-bold">
                                {t('auth.reset_password.request_new')}
                            </Link>
                        </div>
                    ) : (
                        <>
                            <div className="text-center mb-6">
                                <div className="w-16 h-16 bg-sky-100 dark:bg-sky-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <Lock className="text-sky-500" size={32} />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">{t('auth.reset_password.title')}</h2>
                                <p className="text-slate-500">{t('auth.reset_password.subtitle')}</p>
                            </div>

                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">{t('auth.reset_password.new_password')}</label>
                                    <div className="relative">
                                        <input
                                            type={showPassword ? "text" : "password"}
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            className="w-full p-4 bg-slate-50 dark:bg-slate-700 rounded-xl border border-slate-200 dark:border-slate-600 outline-none focus:border-sky-500 transition-colors"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowPassword(!showPassword)}
                                            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                                        >
                                            {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                                        </button>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">{t('auth.reset_password.confirm_password')}</label>
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        className="w-full p-4 bg-slate-50 dark:bg-slate-700 rounded-xl border border-slate-200 dark:border-slate-600 outline-none focus:border-sky-500 transition-colors"
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
                                    disabled={submitting}
                                    className="w-full py-4 bg-gradient-to-r from-sky-500 to-blue-600 text-white font-bold rounded-xl hover:from-sky-600 hover:to-blue-700 transition-all shadow-lg shadow-sky-500/30 flex items-center justify-center gap-2 disabled:opacity-50"
                                >
                                    {submitting ? (
                                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                                    ) : (
                                        t('auth.reset_password.submit')
                                    )}
                                </button>
                            </form>
                        </>
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
