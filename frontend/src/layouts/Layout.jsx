import { useEffect, Suspense, lazy, useCallback } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import {
    Home, Users, Banknote, Calendar, Menu, Settings as SettingsIcon, Package, LineChart, Globe,
    LogOut, Shield, Sun, Moon, FlaskConical, Brain, HelpCircle, AlertTriangle
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/auth/useAuth';
import { logoBase64 as logo } from '@/assets/logoBase64';
// Components
import GlobalSearch from '@/shared/ui/GlobalSearch';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import NotificationBell from '@/shared/ui/NotificationBell';
import GlobalBanner from '@/shared/ui/GlobalBanner';
// Prefetching hooks
import { usePrefetchPatients } from '@/hooks/usePatients';
import { usePrefetchAppointments } from '@/hooks/useAppointments';
import { usePrefetchDashboard } from '@/hooks/useDashboard';
// Lazy load AIChat
const AIChat = lazy(() => import('@/features/ai/AIChat'));
import { useUIStore } from '@/store/ui.store';
import { useTenantStore } from '@/store/tenant.store';
const Layout = ({ children }) => {
    const { t, i18n } = useTranslation();
    const { sidebarOpen, setSidebarOpen, darkMode: isDarkMode, toggleDarkMode } = useUIStore();
    const { tenant, hasFeature } = useTenantStore();
    const { user: currentUser, logout } = useAuth();
    const location = useLocation();
    // Role derived from user object directly
    const role = currentUser?.role || 'doctor';
    const isAdmin = role === 'admin';
    const isSuperAdmin = role === 'super_admin';
    const navigate = useNavigate();
    // Redirect Super Admin to /admin if they land on root /
    useEffect(() => {
        if (isSuperAdmin && location.pathname === '/') {
            navigate('/admin', { replace: true });
        }
    }, [isSuperAdmin, location.pathname, navigate]);
    // Navigation Items
    let navItems = [];
    if (isSuperAdmin) {
        // System Admin View (Redesigned)
        navItems = [
            { icon: Shield, label: t('sidebar.dashboard'), path: '/admin' },
            { icon: Home, label: t('sidebar.settings'), path: '/admin/tenants' }, // Using settings for tenants momentarily or add specific key
            { icon: Users, label: t('sidebar.users'), path: '/admin/users' },
            { icon: Banknote, label: t('sidebar.billing'), path: '/admin/finance' },
            { icon: HelpCircle, label: t('sidebar.contact'), path: '/admin/messages' },
            { icon: Brain, label: t('sidebar.ai'), path: '/ai/stats' }, // Existing
            { icon: AlertTriangle, label: t('sidebar.error_log'), path: '/admin/system/logs' },
            { icon: SettingsIcon, label: t('sidebar.settings'), path: '/admin/settings' },
        ];
    } else {
        // Clinic View
        navItems = [
            { icon: Home, label: t('sidebar.dashboard'), path: '/' },
            { icon: Calendar, label: t('sidebar.appointments'), path: '/appointments' },
            { icon: Users, label: t('sidebar.patients'), path: '/patients' },
            { icon: Package, label: t('sidebar.inventory'), path: '/inventory' },
        ];
        if (isAdmin) {
            // Always show Billing for Admins (User Request: All plans have it)
            navItems.push({ icon: Banknote, label: t('sidebar.billing'), path: '/billing' });
            navItems.push({ icon: LineChart, label: t('sidebar.reports'), path: '/analytics' });
            navItems.push(
                { icon: Users, label: t('sidebar.users'), path: '/users' },
                { icon: SettingsIcon, label: t('sidebar.settings'), path: '/settings' },
            );
        }
        // Labs visible to Admin or users with permission (Always Enabled for Tenant)
        let hasLabPermission = isAdmin;
        if (!isAdmin && currentUser?.permissions) {
            try {
                const perms = typeof currentUser.permissions === 'string'
                    ? JSON.parse(currentUser.permissions)
                    : currentUser.permissions;
                if (Array.isArray(perms) && perms.includes('manage_lab')) {
                    hasLabPermission = true;
                }
            } catch (e) {
                // ignore parse error
            }
        }
        if (hasLabPermission) {
            navItems.push({ icon: FlaskConical, label: t('sidebar.labs'), path: '/labs' });
        }
    }
    // Helper to calculate subscription days
    const getSubscriptionStatus = () => {
        if (!tenant?.subscription_end_date) return null;
        const daysLeft = Math.ceil((new Date(tenant.subscription_end_date) - new Date()) / (1000 * 60 * 60 * 24));
        if (daysLeft < 0) return { text: t('sidebar.subscription.expired'), color: 'text-red-500' };
        if (daysLeft === 0) return { text: t('sidebar.subscription.ends_today'), color: 'text-amber-500' };
        if (daysLeft <= 7) return { text: t('sidebar.subscription.days_left', { count: daysLeft }), color: 'text-amber-500' };
        return { text: t('sidebar.subscription.days_left', { count: daysLeft }), color: 'text-text-secondary' };
    };
    const subStatus = getSubscriptionStatus();
    // Prefetch functions for hover-based prefetching
    const prefetchPatients = usePrefetchPatients();
    const prefetchAppointments = usePrefetchAppointments();
    const prefetchDashboard = usePrefetchDashboard();
    // Handler for prefetching on hover
    const handlePrefetch = useCallback((path) => {
        switch (path) {
            case '/':
                prefetchDashboard();
                break;
            case '/patients':
                prefetchPatients();
                break;
            case '/appointments':
                prefetchAppointments();
                break;
            default:
                break;
        }
    }, [prefetchPatients, prefetchAppointments, prefetchDashboard]);
    return (
        <div className={`flex h-screen bg-background`}>
            {/* Global Banner (Phase 3) */}
            <div className="fixed top-0 left-0 right-0 z-[60]">
                <GlobalBanner />
            </div>
            {/* Mobile Sidebar Overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-20 md:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}
            {/* Sidebar */}
            <aside className={`
                fixed inset-y-0 right-0 z-30 w-72 bg-surface/95 backdrop-blur-xl border-l border-border/50 transform transition-transform duration-300 ease-in-out md:translate-x-0 md:static shadow-2xl shadow-black/5
                ${sidebarOpen ? 'translate-x-0' : 'translate-x-full'}
            `}>
                <div className={`flex flex-col items-center justify-center border-b border-border p-4`}>
                    <div className="h-28 w-full overflow-hidden flex items-center justify-center mb-4">
                        <img
                            src={tenant?.logo ? `${import.meta.env.VITE_API_BASE_URL}/${tenant.logo}` : logo}
                            alt={t('common.logo')}
                            className="h-full w-full object-contain drop-shadow-md scale-[2.5] translate-x-4"
                        />
                    </div>
                    <p
                        id="sidebar-clinic-name"
                        className="text-base font-black bg-gradient-to-r from-primary-600 to-blue-800 dark:from-sky-400 dark:to-blue-500 bg-clip-text text-transparent text-center tracking-tight"
                    >
                        {isSuperAdmin ? t('sidebar.system_admin') : (tenant?.name || t('common.default_clinic_name'))}
                    </p>
                    {/* Subscription Badge */}
                    {tenant && (
                        <div className="mt-2 text-center text-xs">
                            <span className={`px-2 py-1 rounded-full font-bold ${tenant.plan === 'premium' ? 'bg-amber-500/20 text-amber-600' :
                                tenant.plan === 'basic' ? 'bg-blue-500/20 text-blue-600' :
                                    'bg-surface-hover text-text-secondary'
                                }`}>
                                {tenant.plan === 'premium' ? t('sidebar.subscription.plan_premium') :
                                    tenant.plan === 'basic' ? t('sidebar.subscription.plan_basic') : t('sidebar.subscription.plan_trial')}
                            </span>
                            {subStatus && (
                                <p className={`mt-1 ${subStatus.color}`}>
                                    {subStatus.text}
                                </p>
                            )}
                        </div>
                    )}
                </div>
                <nav className="p-4 space-y-2">
                    {navItems.map((item) => {
                        const isActive = location.pathname === item.path;
                        const Icon = item.icon;
                        return (
                            <Link
                                key={item.path}
                                id={`nav-${item.path.replace(/\//g, '') || 'dashboard'}`}
                                to={item.path}
                                onClick={() => setSidebarOpen(false)}
                                onMouseEnter={() => handlePrefetch(item.path)}
                                className={`
                                    relative flex items-center gap-3 px-4 py-3.5 rounded-2xl transition-all duration-300 group
                                    ${isActive
                                        ? 'bg-primary/10 text-primary shadow-inner font-extrabold'
                                        : 'text-slate-700 dark:text-slate-200 font-bold hover:bg-surface-hover hover:text-primary hover:shadow-sm'}
                                    ${isActive ? 'before:absolute before:inset-0 before:rounded-2xl before:bg-primary/20 before:blur-sm before:opacity-70 before:scale-x-105' : 'hover:before:absolute hover:before:inset-0 hover:before:rounded-2xl hover:before:bg-primary/10 hover:before:blur-sm hover:before:opacity-50 hover:before:scale-x-105'}
                                `}
                            >
                                {isActive && (
                                    <div className="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 bg-primary rounded-r-full" />
                                )}
                                <Icon size={22} className={`transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`} />
                                <span className="text-sm">{item.label}</span>
                            </Link>
                        )
                    })}
                    <div className="mt-auto pt-6 border-t border-border/50">
                        {/* Utilities Row (Lang & Theme) */}
                        <div className="grid grid-cols-2 gap-3 mb-3">
                            <button
                                onClick={() => i18n.changeLanguage(i18n.language === 'ar' ? 'en' : 'ar')}
                                className="flex items-center justify-center py-3 rounded-2xl bg-surface-hover text-slate-600 dark:text-slate-300 hover:bg-primary/10 hover:text-primary transition-all group"
                                title={t('common.language')}
                            >
                                <Globe size={20} className="transition-transform group-hover:rotate-12" />
                            </button>
                            <button
                                onClick={toggleDarkMode}
                                className="flex items-center justify-center py-3 rounded-2xl bg-surface-hover text-slate-600 dark:text-slate-300 hover:bg-amber-400/10 hover:text-amber-500 transition-all group"
                                title={isDarkMode ? t('sidebar.mode.light') : t('sidebar.mode.dark')}
                            >
                                {isDarkMode ?
                                    <Sun size={20} className="transition-transform group-hover:rotate-90" /> :
                                    <Moon size={20} className="transition-transform group-hover:-rotate-12" />
                                }
                            </button>
                        </div>
                        <Link
                            to="/support"
                            onClick={() => setSidebarOpen(false)}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-colors text-slate-600 dark:text-slate-300 hover:bg-indigo-50 hover:text-indigo-600 dark:hover:bg-indigo-500/10 dark:hover:text-indigo-400 ${location.pathname === '/support' ? 'bg-indigo-50 dark:bg-indigo-900/20 font-bold text-indigo-600' : 'font-medium'}`}
                        >
                            <HelpCircle size={22} />
                            <span className="text-sm font-medium">{t('common.help_support')}</span>
                        </Link>
                        <button
                            onClick={() => {
                                logout();
                            }}
                            className="w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl transition-all text-red-500 hover:bg-red-50 hover:text-red-600 hover:scale-[1.02] mt-2 active:scale-95"
                        >
                            <LogOut size={22} />
                            <span className="text-sm font-bold">{t('sidebar.logout')}</span>
                        </button>
                        {!isAdmin && !isSuperAdmin && (
                            <div className="mt-4 p-4 bg-surface-hover rounded-xl text-center">
                                <p className="text-xs text-text-secondary">{t('sidebar.limited_account')}</p>
                            </div>
                        )}
                    </div>
                </nav>
            </aside>
            {/* Main Content */}
            <div className="flex-1 flex flex-col h-screen overflow-hidden bg-background/50">
                <header className={`h-18 border-b flex items-center justify-between px-6 md:px-8 shrink-0 sticky top-0 z-20 shadow-sm bg-surface/90 backdrop-blur-xl border-border/60`}>
                    <div className="flex items-center gap-4 md:hidden">
                        <button
                            onClick={() => setSidebarOpen(true)}
                            className="p-2 rounded-lg hover:bg-slate-50 text-slate-600 active:bg-slate-100 transition-colors"
                        >
                            <Menu size={24} />
                        </button>
                        <p className={`font-bold text-lg text-text-primary`}>
                            {currentUser?.tenant?.name || t('common.default_clinic_name')}
                        </p>
                    </div>
                    <div className="flex-1 flex max-w-xl mx-auto gap-4 items-center">
                        <GlobalSearch />
                        <div className="hidden md:block">
                            <NotificationBell />
                        </div>
                    </div>
                    <div className="md:hidden">
                        <NotificationBell />
                    </div>
                </header>
                <main className="flex-1 overflow-y-auto p-4 md:p-8 pb-24 md:pb-8">
                    <div className="w-full max-w-[1920px] mx-auto">
                        <Suspense fallback={<LoadingSpinner />}>
                            {children}
                        </Suspense>
                    </div>
                </main>
                <Suspense fallback={null}>
                    <AIChat />
                </Suspense>
            </div>
        </div >
    );
};
export default Layout;

