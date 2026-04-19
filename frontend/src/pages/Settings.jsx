import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Database, List, User, Settings as SettingsIcon, CreditCard, CheckCircle, AlertTriangle, Printer } from 'lucide-react';
import { getMe, getBackupStatus } from '../api';
// Import newly created components
// Import newly created components
import GeneralSettings from '@/features/settings/SettingsTabs/GeneralSettings';
import SubscriptionSettings from '@/features/settings/SettingsTabs/SubscriptionSettings';
import ServicesSettings from '@/features/settings/SettingsTabs/ServicesSettings';
import BackupSettings from '@/features/settings/SettingsTabs/BackupSettings';
import RxSettings from '@/features/settings/SettingsTabs/RxSettings';
// Legacy imports removed (PriceLists, InsuranceProviders now inside ServicesSettings)
export default function Settings() {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState('general');
    const [message, setMessage] = useState(null);
    const [currentUser, setCurrentUser] = useState(null);
    // Backup State
    const [backupStatus, setBackupStatus] = useState({ connected: false, loading: true });
    useEffect(() => {
        // Parse URL params for status (redirected from Google)
        const query = new URLSearchParams(window.location.search);
        const status = query.get('status');
        const detail = query.get('detail');
        const tabParam = query.get('tab');
        if (status === 'success') {
            setMessage({ type: 'success', text: 'Google Account Linked Successfully' }); // Could keep backend msg or translate
            window.history.replaceState({}, document.title, window.location.pathname);
            setActiveTab('backup'); // Switch to backup tab
            checkBackupConnection();
        } else if (status === 'error') {
            setMessage({ type: 'error', text: detail || 'Failed to link Google Account' });
            window.history.replaceState({}, document.title, window.location.pathname);
            setActiveTab('backup');
        } else if (tabParam) {
            setActiveTab(tabParam);
            checkBackupConnection();
        } else {
            checkBackupConnection();
        }
        loadUserInfo();
    }, []);
    const checkBackupConnection = async () => {
        try {
            const res = await getBackupStatus();
            setBackupStatus({
                connected: res.data.connected === true,
                loading: false,
                lastBackup: res.data.last_backup
            });
        } catch (err) {
            setBackupStatus({ connected: false, loading: false });
        }
    };
    const loadUserInfo = async () => {
        try {
            const res = await getMe();
            setCurrentUser(res.data);
        } catch (err) {
            console.error('Failed to load user info', err);
        }
    };
    const tabs = useMemo(() => [
        { id: 'general', label: t('settings.tabs.general'), icon: User },
        { id: 'subscription', label: t('settings.tabs.subscription'), icon: CreditCard },
        { id: 'services', label: t('settings.tabs.services'), icon: List }, // Combined Tab
        { id: 'rx', label: t('settings.tabs.rx'), icon: Printer },
        { id: 'backup', label: t('settings.tabs.backup'), icon: Database },
    ], [t]);
    return (
        <div className="min-h-screen bg-slate-50/50 dark:bg-slate-900/50 p-6 flex flex-col md:flex-row gap-6 animate-in fade-in active">
            {/* Sidebar Navigation */}
            <div className="w-full md:w-64 flex-shrink-0">
                <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 shadow-sm border border-slate-100 dark:border-white/5 sticky top-6">
                    <h2 className="text-xl font-bold text-slate-800 dark:text-white px-4 mb-6 flex items-center gap-2">
                        <SettingsIcon className="text-indigo-600" />
                        {t('settings.title')}
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
                                        ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30'
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
                    <div className="h-32 bg-gradient-to-r from-indigo-500 to-cyan-600 relative overflow-hidden">
                        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10"></div>
                        <div className="absolute -bottom-6 right-8">
                            <div className="p-4 bg-white dark:bg-slate-800 rounded-2xl shadow-lg border-4 border-white dark:border-slate-800">
                                {activeTab === 'general' && <User size={32} className="text-indigo-600" />}
                                {activeTab === 'subscription' && <CreditCard size={32} className="text-indigo-600" />}
                                {activeTab === 'services' && <List size={32} className="text-indigo-600" />}
                                {activeTab === 'backup' && <Database size={32} className="text-indigo-600" />}
                                {activeTab === 'rx' && <Printer size={32} className="text-indigo-600" />}
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
                                {activeTab === 'general' && t('settings.headers.general')}
                                {activeTab === 'subscription' && t('settings.headers.subscription')}
                                {activeTab === 'services' && t('settings.headers.services')}
                                {activeTab === 'rx' && t('settings.headers.rx')}
                                {activeTab === 'backup' && t('settings.headers.backup')}
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
                        {activeTab === 'subscription' && (
                            <SubscriptionSettings
                                currentUser={currentUser}
                            />
                        )}
                        {activeTab === 'services' && (
                            <ServicesSettings
                                setMessage={setMessage}
                            />
                        )}
                        {activeTab === 'rx' && (
                            <RxSettings
                                setMessage={setMessage}
                            />
                        )}
                        {activeTab === 'backup' && (
                            <BackupSettings
                                backupStatus={backupStatus}
                                currentUser={currentUser}
                                setMessage={setMessage}
                                loadUserInfo={loadUserInfo}
                            />
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

