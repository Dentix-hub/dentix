import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, Link } from 'react-router-dom';
import { registerClinic } from '../api';
const logo = '/logo.png';
import { Building2, User, Lock, AlertCircle } from 'lucide-react';
const RegisterClinic = ({ isDarkMode }) => {
    const { t } = useTranslation();
    const [formData, setFormData] = useState({
        clinic_name: '',
        admin_username: '',
        admin_email: '',
        admin_password: '',
        confirm_password: ''
    });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        // Frontend validations
        if (!formData.clinic_name.trim() || formData.clinic_name.trim().length < 2) {
            setError(t('auth.register.errors.clinic_name_short'));
            return;
        }
        if (!formData.admin_email.includes('@') || !formData.admin_email.includes('.')) {
            setError(t('auth.register.errors.invalid_email'));
            return;
        }
        if (!formData.admin_username.trim() || formData.admin_username.trim().length < 3) {
            setError(t('auth.register.errors.username_short'));
            return;
        }
        if (formData.admin_password.length < 8) {
            setError(t('auth.register.errors.password_min_length'));
            return;
        }
        const hasLetter = /\p{L}/u.test(formData.admin_password);
        const hasNumber = /[0-9]/.test(formData.admin_password);
        const hasSpecial = /[^\p{L}0-9]/u.test(formData.admin_password);
        if (!hasLetter || !hasNumber || !hasSpecial) {
            setError(t('auth.register.errors.password_weak'));
            return;
        }
        if (formData.admin_password !== formData.confirm_password) {
            setError(t('auth.register.errors.password_mismatch'));
            return;
        }
        setLoading(true);
        try {
            const data = new FormData();
            data.append('clinic_name', formData.clinic_name.trim());
            data.append('admin_username', formData.admin_username.trim());
            data.append('admin_email', formData.admin_email.trim().toLowerCase());
            data.append('admin_password', formData.admin_password);
            await registerClinic(data);
            navigate('/', { state: { message: t('auth.register.success') } });
        } catch (err) {
            console.error(err);
            const serverDetail = err.response?.data?.detail;
            
            if (serverDetail) {
                if (typeof serverDetail === 'string') {
                    setError(serverDetail);
                } else if (Array.isArray(serverDetail)) {
                    const messages = serverDetail.map(d => d.msg || d.message || JSON.stringify(d)).join(' | ');
                    setError(messages);
                } else if (typeof serverDetail === 'object') {
                    setError(JSON.stringify(serverDetail));
                } else {
                    setError(t('auth.register.errors.generic'));
                }
            } else if (err.code === 'ERR_NETWORK' || !err.response) {
                setError(t('auth.register.errors.connection'));
            } else {
                setError(t('auth.register.errors.generic'));
            }
        } finally {
            setLoading(false);
        }
    };
    return (
        <div className={`min-h-screen flex items-center justify-center p-4 dir-rtl bg-background`}>
            <div className={`w-full max-w-md p-8 rounded-2xl shadow-xl bg-surface`}>
                <div className="text-center mb-8">
                    <div className="h-32 w-full overflow-hidden flex items-center justify-center mb-4">
                        <img src={logo} alt="Logo" className="h-full w-full object-contain scale-[2.5] translate-x-4" />
                    </div>
                    <h1 className={`text-2xl font-bold mb-2 text-text-primary`}>{t('auth.register.title')}</h1>
                    <p className={`text-sm text-text-secondary`}>{t('auth.register.subtitle')}</p>
                </div>
                {error && (
                    <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-500">
                        <AlertCircle size={20} />
                        <span className="text-sm font-medium">{error}</span>
                    </div>
                )}
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <label className={`text-sm font-medium text-text-secondary`}>{t('auth.register.clinic_name')}</label>
                        <div className="relative">
                            <Building2 className={`absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-text-secondary`} />
                            <input
                                type="text"
                                name="clinic_name"
                                required
                                value={formData.clinic_name}
                                onChange={handleChange}
                                className={`w-full pr-10 pl-4 py-3 rounded-xl outline-none focus:ring-2 transition-all bg-input border-border text-text-primary focus:ring-primary/20 focus:border-primary border`}
                                placeholder={t('auth.register.clinic_name_placeholder')}
                            />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className={`text-sm font-medium text-text-secondary`}>{t('auth.register.email')}</label>
                        <div className="relative">
                            <input
                                type="email"
                                name="admin_email"
                                required
                                value={formData.admin_email}
                                onChange={handleChange}
                                className={`w-full pr-4 pl-4 py-3 rounded-xl outline-none focus:ring-2 transition-all bg-input border-border text-text-primary focus:ring-primary/20 focus:border-primary border`}
                                placeholder="example@email.com"
                                dir="ltr"
                            />
                        </div>
                        <p className={`text-xs text-text-secondary`}>{t('auth.register.email_hint')}</p>
                    </div>
                    <div className="space-y-2">
                        <label className={`text-sm font-medium text-text-secondary`}>{t('auth.register.username')}</label>
                        <div className="relative">
                            <User className={`absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-text-secondary`} />
                            <input
                                type="text"
                                name="admin_username"
                                required
                                value={formData.admin_username}
                                onChange={handleChange}
                                className={`w-full pr-10 pl-4 py-3 rounded-xl outline-none focus:ring-2 transition-all bg-input border-border text-text-primary focus:ring-primary/20 focus:border-primary border`}
                                placeholder={t('auth.register.username_placeholder')}
                            />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className={`text-sm font-medium text-text-secondary`}>{t('auth.register.password')}</label>
                        <div className="relative">
                            <Lock className={`absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-text-secondary`} />
                            <input
                                type="password"
                                name="admin_password"
                                required
                                value={formData.admin_password}
                                onChange={handleChange}
                                className={`w-full pr-10 pl-4 py-3 rounded-xl outline-none focus:ring-2 transition-all bg-input border-border text-text-primary focus:ring-primary/20 focus:border-primary border`}
                                placeholder="••••••••"
                            />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className={`text-sm font-medium text-text-secondary`}>{t('auth.register.confirm_password')}</label>
                        <div className="relative">
                            <Lock className={`absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-text-secondary`} />
                            <input
                                type="password"
                                name="confirm_password"
                                required
                                value={formData.confirm_password}
                                onChange={handleChange}
                                className={`w-full pr-10 pl-4 py-3 rounded-xl outline-none focus:ring-2 transition-all bg-input border-border text-text-primary focus:ring-primary/20 focus:border-primary border`}
                                placeholder="••••••••"
                            />
                        </div>
                    </div>
                    <div className="flex items-start gap-3 mt-4">
                        <div className="relative flex items-center">
                            <input
                                type="checkbox"
                                required
                                id="terms"
                                className="peer h-5 w-5 cursor-pointer appearance-none rounded-md border border-slate-300 transition-all checked:border-primary checked:bg-primary hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/20"
                            />
                            <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-white opacity-0 transition-opacity peer-checked:opacity-100">
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" stroke="currentColor" strokeWidth="1">
                                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path>
                                </svg>
                            </div>
                        </div>
                        <label htmlFor="terms" className="text-xs text-text-secondary cursor-pointer select-none leading-relaxed">
                            {t('auth.register.agree_pre')} <Link to="/terms" className="text-primary hover:underline font-bold" target="_blank">{t('auth.register.agree_terms')}</Link> {t('auth.register.agree_and')} <Link to="/privacy" className="text-primary hover:underline font-bold" target="_blank">{t('auth.register.agree_privacy')}</Link> {t('auth.register.agree_post')}
                        </label>
                    </div>
                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-primary hover:bg-primary-600 text-white py-3 rounded-xl font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-4 shadow-lg shadow-primary/25"
                    >
                        {loading ? t('auth.register.submitting') : t('auth.register.submit')}
                    </button>
                    <div className="text-center mt-4">
                        <Link to="/" className={`text-sm hover:underline text-primary`}>
                            {t('auth.register.login_link')}
                        </Link>
                    </div>
                </form>
            </div>
        </div>
    );
};
export default RegisterClinic;

