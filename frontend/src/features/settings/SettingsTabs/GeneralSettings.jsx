import { Save } from 'lucide-react';
import * as api from '@/api';
import { useTranslation } from 'react-i18next';

const GeneralSettings = ({ currentUser, loadUserInfo, setMessage }) => {
    const { t } = useTranslation();

    return (
        <form onSubmit={async (e) => {
            e.preventDefault();
            const newUsername = e.target.username.value;
            const newEmail = e.target.email.value;
            const newPassword = e.target.password.value;
            if (!newUsername) return;
            try {
                await api.updateProfile({
                    username: newUsername,
                    email: newEmail || undefined,
                    password: newPassword || undefined
                });
                setMessage({ type: 'success', text: t('settings.general.success') });
                loadUserInfo();
                e.target.password.value = '';
            } catch (err) {
                setMessage({ type: 'error', text: err.response?.data?.detail || t('settings.general.error') });
            }
        }} className="max-w-2xl space-y-6">
            <div className="space-y-2">
                <label className="text-sm font-bold text-slate-700 dark:text-slate-300">{t('settings.general.username')}</label>
                <input
                    name="username"
                    key={`username-${currentUser?.id || 'loading'}`}
                    defaultValue={currentUser?.username}
                    className="w-full p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all font-bold"
                />
            </div>
            <div className="space-y-2">
                <label className="text-sm font-bold text-slate-700 dark:text-slate-300">{t('settings.general.email')}</label>
                <input
                    name="email"
                    type="email"
                    key={`email-${currentUser?.id || 'loading'}`}
                    defaultValue={currentUser?.email || ''}
                    className="w-full p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all font-bold"
                    dir="ltr"
                />
            </div>
            <div className="space-y-2">
                <label className="text-sm font-bold text-slate-700 dark:text-slate-300">{t('settings.general.new_password')}</label>
                <input
                    name="password"
                    type="password"
                    placeholder="••••••••"
                    className="w-full p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all font-bold"
                />
                <p className="text-xs text-slate-400">{t('settings.general.password_hint')}</p>
            </div>
            <div className="pt-4">
                <button type="submit" className="flex items-center gap-2 px-8 py-3 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition shadow-lg shadow-indigo-500/20 active:scale-95">
                    <Save size={20} />
                    {t('settings.general.save')}
                </button>
            </div>
        </form>
    );
};

export default GeneralSettings;
