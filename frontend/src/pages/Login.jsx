import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, Link } from 'react-router-dom';
import { login } from '../api';
import { Sun, Moon, Globe } from 'lucide-react';
import logo from '@/assets/logo.png';

export default function Login({ isDarkMode, toggleDarkMode }) {
    const { t, i18n } = useTranslation();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        try {
            const { data } = await login(username, password);
            // Save token based on rememberMe
            if (rememberMe) {
                localStorage.setItem('token', data.access_token);
            } else {
                sessionStorage.setItem('token', data.access_token);
            }
            if (data.role === 'super_admin') {
                window.location.href = '/admin';
            } else {
                window.location.href = '/';
            }
        } catch (err) {
            console.error("Login Error:", err);
            if (err.response) {
                // Server responded with a status code
                setError(err.response.data.detail || err.response.data.error?.message || t('auth.login.errors.server') + ': ' + err.response.status);
            } else if (err.request) {
                // Request made but no response received
                setError(t('auth.login.errors.connection'));
            } else {
                // Something else happened
                setError(t('auth.login.errors.unknown') + ': ' + err.message);
            }
        }
    };

    return (
        <div className={`min-h-screen flex items-center justify-center p-4 transition-colors duration-500 bg-background`}>
            <div className={`w-full max-w-md p-8 rounded-[2rem] shadow-2xl border transition-all duration-300 bg-surface border-white/10 text-center`}>
                <div className="flex justify-between items-start mb-6 w-full">
                    {/* Language Switcher */}
                    <button
                        onClick={() => {
                            const newLang = i18n.language === 'ar' ? 'en' : 'ar';
                            i18n.changeLanguage(newLang);
                        }}
                        className={`p-3 rounded-2xl transition-colors bg-surface-hover text-text-secondary hover:text-text-primary hover:bg-primary/5`}
                        title={i18n.language === 'ar' ? 'Switch to English' : 'تغيير للعربية'}
                    >
                        <Globe size={20} />
                    </button>

                    <img src={logo} alt="DENTIX Logo" className="h-24 w-auto object-contain" />

                    <button
                        onClick={toggleDarkMode}
                        className={`p-3 rounded-2xl transition-colors bg-surface-hover text-text-secondary hover:text-text-primary hover:bg-primary/5`}
                    >
                        {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
                    </button>
                </div>

                <h1 className={`text-3xl font-black mb-2 text-text-primary`}>{t('auth.login.title')}</h1>
                <p className={`text-text-secondary mb-8 font-medium`}>{t('auth.login.subtitle')}</p>

                {error && (
                    <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-4 rounded-2xl text-sm font-bold mb-6 animate-shake">
                        {error}
                    </div>
                )}

                <form onSubmit={handleLogin} className="space-y-5">
                    <div className="relative group">
                        <input
                            type="text"
                            placeholder={t('auth.login.username')}
                            className={`w-full p-4 rounded-2xl border outline-none transition-all text-right bg-input border-border text-text-primary focus:border-primary focus:ring-1 focus:ring-primary`}
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                        />
                    </div>
                    <div className="relative group">
                        <input
                            type="password"
                            placeholder={t('auth.login.password')}
                            className={`w-full p-4 rounded-2xl border outline-none transition-all text-right bg-input border-border text-text-primary focus:border-primary focus:ring-1 focus:ring-primary`}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>

                    <div className="flex items-center justify-between px-1">
                        <Link
                            to="/forgot-password"
                            className={`text-sm font-bold hover:underline text-primary`}
                        >
                            {t('auth.login.forgot_password')}
                        </Link>
                        <div className="flex items-center gap-3">
                            <label htmlFor="rememberMe" className={`text-sm cursor-pointer select-none font-medium text-text-secondary hover:text-text-primary`}>
                                {t('auth.login.remember_me')}
                            </label>
                            <input
                                id="rememberMe"
                                type="checkbox"
                                className="w-5 h-5 rounded-lg border-slate-300 text-primary focus:ring-primary cursor-pointer transition-transform active:scale-90"
                                checked={rememberMe}
                                onChange={(e) => setRememberMe(e.target.checked)}
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="w-full py-4 bg-primary text-white font-black rounded-2xl hover:brightness-110 shadow-xl shadow-primary/25 transition-all active:scale-[0.98] transform"
                    >
                        {t('auth.login.submit')}
                    </button>

                    <div className="text-center mt-6">
                        <Link
                            to="/register"
                            className={`inline-block w-full py-3 rounded-2xl border-2 font-bold transition-all ${isDarkMode
                                ? 'border-primary/50 text-primary hover:bg-primary/10'
                                : 'border-primary text-primary hover:bg-primary/5'
                                }`}
                        >
                            {t('auth.login.register_new')}
                        </Link>
                    </div>
                </form>

                <div className="mt-8 pt-6 border-t border-slate-100/10 flex flex-col gap-2">
                    <div className="flex justify-center gap-4 text-xs font-medium text-text-secondary">
                        <Link to="/terms" className="hover:text-primary transition-colors">{t('auth.login.terms')}</Link>
                        <span>•</span>
                        <Link to="/privacy" className="hover:text-primary transition-colors">{t('auth.login.privacy')}</Link>
                    </div>
                    <p className={`text-xs ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                        {t('auth.login.copyright')}
                    </p>
                </div>
            </div>
        </div>
    );
}
