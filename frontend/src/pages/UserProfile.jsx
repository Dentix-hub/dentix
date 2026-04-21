import { useState, useEffect } from 'react';
import { User, Shield, CheckCircle, AlertTriangle } from 'lucide-react';
import { getMe } from '../api';
import GeneralSettings from '@/features/settings/SettingsTabs/GeneralSettings';
import SecuritySettings from '@/features/settings/Profile/SecuritySettings';
import { useTranslation } from 'react-i18next';
export default function UserProfile() {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState('general');
    const [message, setMessage] = useState(null);
    const [currentUser, setCurrentUser] = useState(null);
    useEffect(() => {
        loadUserInfo();
    }, []);
    const loadUserInfo = async () => {
        try {
            const res = await getMe();
            setCurrentUser(res.data);
        } catch (err) {
            console.error('Failed to load user info', err);
        }
    };
    const tabs = [
        { id: 'general', label: t('static.user_profile.tabs.general'), icon: User },
        { id: 'security', label: t('static.user_profile.tabs.security'), icon: Shield },
    ];
    if (!currentUser) return <div className="p-8 text-center text-slate-400 font-bold">{t('static.user_profile.loading')}</div>;
    return (
        <div className="min-h-screen bg-slate-50/50 dark:bg-slate-900/50 p-6 flex flex-col md:flex-row gap-6 animate-in fade-in active">
            {/* Sidebar Navigation */}
            <div className="w-full md:w-64 flex-shrink-0">
                <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 shadow-sm border border-slate-100 dark:border-white/5 sticky top-6">
                    <h2 className="text-xl font-bold text-slate-800 dark:text-white px-4 mb-6 flex items-center gap-2">
                        <User className="text-emerald-500" />
                        {t('static.user_profile.menu_title')}
                    </h2>
                    <nav className="space-y-1">
                        {tabs.map(tab => {
                            const Icon = tab.icon;
                            const isActive = activeTab === tab.id;
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-bold ${isActive
                                        ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                                        : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                                        }`}
                                >
                                    <Icon size={20} />
                                    {tab.label}
                                </button>
                            );
                        })}
                    </nav>
                </div>
            </div>
            {/* Main Content Area */}
            <div className="flex-1">
                <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-white/5 min-h-[600px] relative overflow-hidden">
                    {/* Header Banner */}
                    <div className="h-32 bg-gradient-to-r from-emerald-500 to-teal-600 relative overflow-hidden">
                        <div className="absolute inset-0 opacity-10" style={{backgroundImage: 'linear-gradient(45deg, currentColor 25%, transparent 25%), linear-gradient(-45deg, currentColor 25%, transparent 25%), linear-gradient(45deg, transparent 75%, currentColor 75%), linear-gradient(-45deg, transparent 75%, currentColor 75%)', backgroundSize: '20px 20px', backgroundPosition: '0 0, 0 10px, 10px -10px, -10px 0px'}}></div>
                        <div className="absolute -bottom-6 right-8">
                            <div className="p-4 bg-white dark:bg-slate-800 rounded-2xl shadow-lg border-4 border-white dark:border-slate-800">
                                {activeTab === 'general' && <User size={32} className="text-emerald-600" />}
                                {activeTab === 'security' && <Shield size={32} className="text-emerald-600" />}
                            </div>
                        </div>
                    </div>
                    <div className="p-8 pt-12">
                        {/* Tab Title */}
                        <div className="mb-8">
                            <h2 className="text-2xl font-bold text-slate-800 dark:text-white">
                                {tabs.find(t => t.id === activeTab)?.label}
                            </h2>
                            <p className="text-slate-500 dark:text-slate-400">
                                {activeTab === 'general' && t('static.user_profile.desc.general')}
                                {activeTab === 'security' && t('static.user_profile.desc.security')}
                            </p>
                        </div>
                        {/* TAB CONTENT */}
                        {activeTab === 'general' && (
                            <GeneralSettings
                                currentUser={currentUser}
                                loadUserInfo={loadUserInfo}
                                setMessage={setMessage}
                            />
                        )}
                        {activeTab === 'security' && (
                            <SecuritySettings />
                        )}
                    </div>
                </div>
            </div>
            {/* Toast Message */}
            {message && (
                <div className={`fixed bottom-8 left-8 p-4 rounded-2xl flex items-center gap-3 shadow-2xl animate-in slide-in-from-bottom-10 z-[100] ${message.type === 'success' ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'}`}>
                    {message.type === 'success' ? <CheckCircle size={24} /> : <AlertTriangle size={24} />}
                    <span className="font-bold text-lg">{message.text}</span>
                </div>
            )}
        </div>
    );
}

