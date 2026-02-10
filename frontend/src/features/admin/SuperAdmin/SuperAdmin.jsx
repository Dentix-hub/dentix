import { useState } from 'react';
import {
    LayoutDashboard, Building2, CreditCard, CalendarRange,
    MessageSquare, Bell, ShieldCheck, Activity, Users, Settings, Puzzle
} from 'lucide-react';
// Imported Sub-Components
import DashboardStats from '@/features/admin/SuperAdmin/DashboardStats';
import TenantsManager from '@/features/admin/SuperAdmin/TenantsManager';
import PlansManager from '@/features/admin/SuperAdmin/PlansManager';
import PaymentsManager from '@/features/admin/SuperAdmin/PaymentsManager';
import UsersManager from '@/features/admin/SuperAdmin/UsersManager';
import SettingsManager from '@/features/admin/SuperAdmin/SettingsManager';
import SupportInbox from '@/features/admin/SuperAdmin/SupportInbox';
import NotificationsManager from '@/features/admin/SuperAdmin/NotificationsManager';
import AuditLogViewer from '@/features/admin/SuperAdmin/AuditLogViewer';
import SecurityPanel from '@/features/admin/SuperAdmin/SecurityPanel'; // Phase 3
import FeatureManager from '@/features/admin/SuperAdmin/FeatureManager'; // Phase 3
import SystemHealth from '@/features/admin/SuperAdmin/SystemHealth'; // Phase 5
export default function SuperAdmin() {
    const [activeTab, setActiveTab] = useState('dashboard');
    const menuItems = [
        { id: 'dashboard', label: 'لوحة المعلومات', icon: LayoutDashboard },
        { id: 'tenants', label: 'إدارة العيادات', icon: Building2 },
        { id: 'plans', label: 'إدارة الخطط', icon: CalendarRange },
        { id: 'payments', label: 'المدفوعات', icon: CreditCard },
        { id: 'users', label: 'المستخدمين', icon: Users },
        { id: 'support', label: 'الدعم الفني', icon: MessageSquare },
        { id: 'notifications', label: 'الإشعارات', icon: Bell },
        { id: 'audit', label: 'سجل النشاط', icon: Activity },
        { id: 'health', label: 'صحة النظام', icon: Activity },
        { id: 'security', label: 'الأمان', icon: ShieldCheck },
        { id: 'settings', label: 'الإعدادات', icon: Settings },
        { id: 'features', label: 'المميزات', icon: Puzzle },
    ];
    return (
        <div className="flex h-screen bg-slate-50 dark:bg-slate-950 overflow-hidden font-cairo">
            {/* Sidebar */}
            <aside className="w-64 bg-white dark:bg-slate-900 border-l border-slate-100 dark:border-slate-800 flex flex-col z-20 shadow-xl shadow-slate-200/50 dark:shadow-none hidden md:flex">
                <div className="p-8 pb-4">
                    <div className="flex items-center gap-3 mb-1">
                        <div className="w-10 h-10 bg-gradient-to-tr from-indigo-600 to-violet-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
                            <ShieldCheck size={24} />
                        </div>
                        <div>
                            <h1 className="text-xl font-black text-slate-800 dark:text-white tracking-tight">DENTIX</h1>
                            <p className="text-[10px] font-bold text-indigo-500 uppercase tracking-widest">Super Admin</p>
                        </div>
                    </div>
                </div>
                <div className="p-4 flex-1 overflow-y-auto custom-scrollbar space-y-1">
                    {menuItems.map(item => (
                        <button
                            key={item.id}
                            onClick={() => setActiveTab(item.id)}
                            className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl font-bold transition-all duration-300 relative overflow-hidden group ${activeTab === item.id
                                ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 shadow-sm'
                                : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-800 dark:hover:text-slate-200'
                                }`}
                        >
                            {activeTab === item.id && (
                                <span className="absolute right-0 top-0 bottom-0 w-1 bg-indigo-600 rounded-r-full" />
                            )}
                            <item.icon size={20} className={`transition-transform duration-300 ${activeTab === item.id ? 'scale-110' : 'group-hover:scale-110'}`} />
                            <span>{item.label}</span>
                        </button>
                    ))}
                </div>
                <div className="p-4 border-t border-slate-100 dark:border-slate-800">
                    <div className="bg-indigo-50/50 dark:bg-slate-800/50 p-4 rounded-2xl border border-indigo-100 dark:border-slate-700">
                        <p className="text-xs font-bold text-slate-500 mb-1">حالة النظام</p>
                        <div className="flex items-center gap-2 text-emerald-500 font-bold text-sm">
                            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                            يعمل بكفاءة
                        </div>
                    </div>
                </div>
            </aside>
            {/* Main Content */}
            <main className="flex-1 overflow-y-auto relative scroll-smooth bg-slate-50 dark:bg-slate-950">
                {/* Header for Mobile */}
                <div className="md:hidden bg-white dark:bg-slate-900 p-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center sticky top-0 z-30">
                    <div className="font-black text-slate-800 dark:text-white">DENTIX Admin</div>
                    <button className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                        <LayoutDashboard size={20} />
                    </button>
                </div>
                <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-8 min-h-screen pb-20">
                    {/* Header */}
                    <header className="flex justify-between items-end mb-8 animate-fade-in-down">
                        <div>
                            <h2 className="text-3xl font-black text-slate-800 dark:text-white mb-2 leading-tight">
                                {menuItems.find(m => m.id === activeTab)?.label}
                            </h2>
                            <p className="text-slate-500 font-medium">إدارة النظام والتحكم الكامل في العيادات</p>
                        </div>
                    </header>
                    {/* Content Area */}
                    <div className="animate-fade-in-up">
                        {activeTab === 'dashboard' && <DashboardStats />}
                        {activeTab === 'tenants' && <TenantsManager />}
                        {activeTab === 'plans' && <PlansManager />}
                        {activeTab === 'payments' && <PaymentsManager />}
                        {activeTab === 'notifications' && <NotificationsManager />}
                        {activeTab === 'support' && <SupportInbox />}
                        {activeTab === 'audit' && <AuditLogViewer />}
                        {/* Phase 2: Users */}
                        {activeTab === 'users' && <UsersManager />}
                        {/* Phase 3: Settings & Security */}
                        {activeTab === 'settings' && <SettingsManager />}
                        {activeTab === 'security' && <SecurityPanel />}
                        {activeTab === 'features' && <FeatureManager />}
                        {/* Phase 5: System Health */}
                        {activeTab === 'health' && <SystemHealth />}
                    </div>
                </div>
            </main>
        </div>
    );
}
