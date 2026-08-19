import { useEffect, Suspense, lazy, useCallback, useRef, useState } from 'react';
import logger from '@/utils/logger';
import { motion } from '@/lib/motion';
import { useLocation, Link, useNavigate, Outlet } from 'react-router-dom';
import {
    Home,
    Banknote,
    Calendar,
    Menu,
    Settings as SettingsIcon,
    Package,
    LineChart,
    Globe,
    LogOut,
    Shield,
    Sun,
    Moon,
    FlaskConical,
    Brain,
    HelpCircle,
    AlertTriangle,
    Building2,
    ChevronRight,
    ChevronLeft,
    UserCog,
    Users2,
    User
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useHotkeys } from 'react-hotkeys-hook';
import { useAuth } from '@/auth/useAuth';
import GlobalSearch from '@/shared/ui/GlobalSearch';
import LoadingSpinner from '@/shared/ui/LoadingSpinner';
import NotificationBell from '@/shared/ui/NotificationBell';
import GlobalBanner from '@/shared/ui/GlobalBanner';
import SubscriptionBanner from '@/shared/ui/SubscriptionBanner';
import CommandPalette from '@/shared/ui/CommandPalette';
import SuperAdminCommandPalette from '@/features/admin/SuperAdmin/SuperAdminCommandPalette';
import { usePatients, usePrefetchPatients } from '@/hooks/usePatients';
import { useAppointments, usePrefetchAppointments } from '@/hooks/useAppointments';
import { usePrefetchDashboard } from '@/hooks/useDashboard';
import Tooltip from '@/shared/ui/Tooltip';
import KeyboardShortcutsModal from '@/shared/ui/modals/KeyboardShortcutsModal';
import ErrorBoundary from '@/shared/ui/ErrorBoundary';
import GlobalErrorFallback from '@/shared/ui/GlobalErrorFallback';
import { useUIStore } from '@/store/ui.store';
import { useTenantStore } from '@/store/tenant.store';
import { API_URL } from '@/api';

const AIChat = lazy(() => import('@/features/ai/AIChat'));
const DESKTOP_BREAKPOINT = 1024;

const Layout = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const { t, i18n } = useTranslation();
    const { sidebarOpen, setSidebarOpen, darkMode: isDarkMode, toggleDarkMode } = useUIStore();
    const { tenant } = useTenantStore();
    const { user: currentUser, logout } = useAuth();
    const [logoError, setLogoError] = useState(false);
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const [isDesktop, setIsDesktop] = useState(() => typeof window !== 'undefined' && window.innerWidth >= DESKTOP_BREAKPOINT);
    const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
    const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
    const menuButtonRef = useRef(null);
    const previousSidebarOpenRef = useRef(sidebarOpen);

    const role = currentUser?.role || 'doctor';
    const isAdmin = role === 'admin';
    const isSuperAdmin = role === 'super_admin';

    useEffect(() => {
        logger.log(`[LAYOUT] Rendering Layout (Path: ${location.pathname})`);
        if (!isDesktop) setSidebarOpen(false);
    }, [location.pathname, isDesktop, setSidebarOpen]);

    useEffect(() => {
        const handleResize = () => {
            const nextIsDesktop = window.innerWidth >= DESKTOP_BREAKPOINT;
            setIsDesktop(nextIsDesktop);
            setSidebarOpen(nextIsDesktop);
        };
        window.addEventListener('resize', handleResize);
        handleResize();
        return () => window.removeEventListener('resize', handleResize);
    }, [setSidebarOpen]);

    useEffect(() => {
        if (isDesktop || !sidebarOpen) return undefined;
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = previousOverflow;
        };
    }, [isDesktop, sidebarOpen]);

    useEffect(() => {
        const wasOpen = previousSidebarOpenRef.current;
        previousSidebarOpenRef.current = sidebarOpen;
        if (!isDesktop && wasOpen && !sidebarOpen) {
            menuButtonRef.current?.focus?.({ preventScroll: true });
        }
    }, [isDesktop, sidebarOpen]);

    const { data: patientsData } = usePatients({ enabled: !isSuperAdmin });
    const { data: appointmentsData } = useAppointments({ enabled: !isSuperAdmin });
    const patients = patientsData || [];
    const appointments = appointmentsData || [];

    useHotkeys('g+p', () => navigate('/patients'), { preventDefault: true });
    useHotkeys('g+a', () => navigate('/appointments'), { preventDefault: true });
    useHotkeys('g+b', () => navigate('/finance'), { preventDefault: true });
    useHotkeys('g+d', () => navigate('/'), { preventDefault: true });
    useHotkeys('g+s', () => navigate('/settings'), { preventDefault: true });
    useHotkeys('g+i', () => navigate('/inventory'), { preventDefault: true });

    useEffect(() => {
        const handleKeyDown = (event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
                event.preventDefault();
                setIsCommandPaletteOpen(prev => !prev);
            }
            if (event.key === '?' && !['INPUT', 'TEXTAREA'].includes(event.target.tagName)) {
                event.preventDefault();
                setIsShortcutsOpen(true);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    useEffect(() => {
        if (isSuperAdmin && location.pathname === '/') {
            navigate('/admin', { replace: true });
        }
    }, [isSuperAdmin, location.pathname, navigate]);

    let navItems = [];
    if (isSuperAdmin) {
        navItems = [
            { icon: Shield, label: t('sidebar.dashboard'), path: '/admin' },
            { icon: Home, label: t('sidebar.settings'), path: '/admin/tenants' },
            { icon: UserCog, label: t('sidebar.users'), path: '/admin/users' },
            { icon: Banknote, label: t('sidebar.billing'), path: '/admin/finance' },
            { icon: HelpCircle, label: t('sidebar.contact'), path: '/admin/messages' },
            { icon: Brain, label: t('sidebar.ai'), path: '/ai/stats' },
            { icon: AlertTriangle, label: t('sidebar.error_log'), path: '/admin/system/logs' },
            { icon: SettingsIcon, label: t('sidebar.settings'), path: '/admin/settings' },
        ];
    } else {
        navItems = [
            { icon: Home, label: t('sidebar.dashboard'), path: '/' },
            { icon: Calendar, label: t('sidebar.appointments'), path: '/appointments' },
            { icon: Users2, label: t('sidebar.patients'), path: '/patients' },
            { icon: Package, label: t('sidebar.inventory'), path: '/inventory' },
        ];

        const canAccessFinance = isAdmin || role === 'manager' || role === 'accountant' || role === 'receptionist' || role === 'doctor';
        if (canAccessFinance) {
            navItems.push({ icon: Banknote, label: t('sidebar.finance', 'المالية'), path: '/finance' });
        }

        if (isAdmin) {
            navItems.push({ icon: LineChart, label: t('sidebar.reports'), path: '/analytics' });
            navItems.push(
                { icon: UserCog, label: t('sidebar.users'), path: '/users' },
                { icon: SettingsIcon, label: t('sidebar.settings'), path: '/settings' },
            );
        }

        let hasLabPermission = isAdmin;
        if (!isAdmin && currentUser?.permissions) {
            try {
                const perms = typeof currentUser.permissions === 'string'
                    ? JSON.parse(currentUser.permissions)
                    : currentUser.permissions;
                if (Array.isArray(perms) && perms.includes('manage_lab')) hasLabPermission = true;
            } catch {
                // Preserve current behavior when legacy permission payloads are malformed.
            }
        }
        if (hasLabPermission) {
            navItems.push({ icon: FlaskConical, label: t('sidebar.labs'), path: '/labs' });
        }
    }

    const getSubscriptionStatus = () => {
        if (!tenant?.subscription_end_date) return null;
        const now = new Date();
        const endDate = new Date(tenant.subscription_end_date);
        const daysLeft = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));

        if (daysLeft < 0) {
            const graceDate = tenant.grace_period_until ? new Date(tenant.grace_period_until) : null;
            if (graceDate && now <= graceDate) {
                const graceDaysLeft = Math.ceil((graceDate - now) / (1000 * 60 * 60 * 24));
                return { text: t('sidebar.subscription.grace_period', { count: graceDaysLeft }), color: 'text-amber-500 animate-pulse' };
            }
            return { text: t('sidebar.subscription.expired'), color: 'text-red-500 font-black' };
        }
        if (daysLeft === 0) return { text: t('sidebar.subscription.ends_today'), color: 'text-amber-500' };
        if (daysLeft <= 7) return { text: t('sidebar.subscription.days_left', { count: daysLeft }), color: 'text-amber-500' };
        return { text: t('sidebar.subscription.days_left', { count: daysLeft }), color: 'text-text-secondary' };
    };
    const subStatus = getSubscriptionStatus();

    const prefetchPatients = usePrefetchPatients();
    const prefetchAppointments = usePrefetchAppointments();
    const prefetchDashboard = usePrefetchDashboard();
    const handlePrefetch = useCallback((path) => {
        switch (path) {
            case '/':
                prefetchDashboard?.();
                break;
            case '/patients':
                prefetchPatients?.();
                break;
            case '/appointments':
                prefetchAppointments?.();
                break;
            default:
                break;
        }
    }, [prefetchPatients, prefetchAppointments, prefetchDashboard]);

    const sidebarWidthClass = isDesktop && isSidebarCollapsed
        ? 'w-20'
        : 'w-[min(18rem,calc(100vw-1rem))] lg:w-72';

    return (
        <div className="flex h-[100dvh] min-h-0 w-full min-w-0 flex-col bg-background">
            <div className="relative z-[60] shrink-0">
                <GlobalBanner />
                <SubscriptionBanner />
            </div>

            {isSuperAdmin ? (
                <SuperAdminCommandPalette
                    isOpen={isCommandPaletteOpen}
                    onClose={() => setIsCommandPaletteOpen(false)}
                />
            ) : (
                <CommandPalette
                    isOpen={isCommandPaletteOpen}
                    onClose={() => setIsCommandPaletteOpen(false)}
                    patients={patients}
                    appointments={appointments}
                />
            )}
            <KeyboardShortcutsModal
                isOpen={isShortcutsOpen}
                onClose={() => setIsShortcutsOpen(false)}
            />

            <div className="relative flex min-h-0 min-w-0 flex-1">
                {sidebarOpen && !isDesktop && (
                    <button
                        type="button"
                        aria-label={t('common.close_menu', 'Close menu')}
                        className="absolute inset-0 z-40 bg-black/50"
                        onClick={() => setSidebarOpen(false)}
                    />
                )}

                <aside
                    data-sidebar
                    aria-label={t('common.main_navigation', 'Main navigation')}
                    aria-hidden={!isDesktop && !sidebarOpen}
                    className={`
                        absolute inset-y-0 start-0 z-50 flex min-w-0 flex-col border-e border-border/50 bg-white shadow-2xl shadow-black/5
                        transition-[transform,width] duration-300 ease-in-out dark:bg-slate-900 lg:static lg:translate-x-0
                        ${sidebarOpen ? 'translate-x-0' : 'ltr:-translate-x-full rtl:translate-x-full'}
                        ${sidebarWidthClass}
                    `}
                >
                    <button
                        type="button"
                        onClick={() => setIsSidebarCollapsed(prev => !prev)}
                        aria-label={t('common.toggle_sidebar', 'Toggle Sidebar')}
                        className="absolute -end-3 top-8 z-40 hidden h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 lg:flex rtl:rotate-180"
                    >
                        {isSidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
                    </button>

                    <div className="flex shrink-0 flex-col items-center justify-center border-b border-border p-3 transition-all duration-300 sm:p-4">
                        <div className={`${isDesktop && isSidebarCollapsed ? 'h-12' : 'h-20 sm:h-28'} mb-2 flex w-full items-center justify-center overflow-hidden transition-all duration-300`}>
                            {!logoError ? (
                                <img
                                    src={tenant?.logo && tenant.logo !== 'null'
                                        ? (tenant.logo.startsWith('http') || tenant.logo.startsWith('/') ? tenant.logo : `${API_URL}/${tenant.logo}`)
                                        : '/logo.webp'}
                                    alt={t('common.logo')}
                                    onError={(event) => {
                                        if (event.target.src.includes('/logo.webp')) setLogoError(true);
                                        else event.target.src = '/logo.webp';
                                    }}
                                    className="max-h-16 max-w-full object-contain"
                                />
                            ) : (
                                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary sm:h-16 sm:w-16">
                                    <Building2 size={isDesktop && isSidebarCollapsed ? 24 : 36} className="transition-all" />
                                </div>
                            )}
                        </div>

                        {!(isDesktop && isSidebarCollapsed) && (
                            <div className="flex w-full min-w-0 flex-col items-center animate-in fade-in zoom-in duration-300">
                                <p
                                    id="sidebar-clinic-name"
                                    className="max-w-full break-words bg-gradient-to-r from-primary-600 to-blue-800 bg-clip-text text-center text-sm font-extrabold tracking-tight text-transparent dark:from-sky-400 dark:to-blue-500 sm:text-base"
                                >
                                    {isSuperAdmin ? t('sidebar.system_admin') : (tenant?.name || t('common.default_clinic_name'))}
                                </p>
                                {tenant && (
                                    <div className="mt-2 text-center text-xs">
                                        <span className={`rounded-full px-2 py-1 font-bold ${tenant.plan === 'premium' ? 'bg-amber-500/20 text-amber-600' : tenant.plan === 'basic' ? 'bg-blue-500/20 text-blue-600' : 'bg-surface-hover text-text-secondary'}`}>
                                            {tenant.plan === 'premium'
                                                ? t('sidebar.subscription.plan_premium')
                                                : tenant.plan === 'basic'
                                                    ? t('sidebar.subscription.plan_basic')
                                                    : t('sidebar.subscription.plan_trial')}
                                        </span>
                                        {subStatus && <p className={`mt-1 ${subStatus.color}`}>{subStatus.text}</p>}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    <nav className="flex min-h-0 flex-1 flex-col space-y-1 overflow-y-auto overscroll-contain p-3 sm:space-y-2 sm:p-4">
                        {navItems.map((item) => {
                            const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
                            const Icon = item.icon;
                            const link = (
                                <Link
                                    key={item.path}
                                    id={`nav-${item.path.replace(/\//g, '') || 'dashboard'}`}
                                    to={item.path}
                                    onClick={() => {
                                        if (!isDesktop) setSidebarOpen(false);
                                    }}
                                    onMouseEnter={() => handlePrefetch(item.path)}
                                    onFocus={() => handlePrefetch(item.path)}
                                    className={`relative flex min-h-11 items-center gap-3 rounded-2xl px-3 py-2.5 transition-all duration-300 group sm:px-4 sm:py-3 ${isActive ? 'bg-primary/10 font-bold text-primary shadow-inner' : 'font-medium text-slate-700 hover:bg-surface-hover hover:text-primary dark:text-slate-200'}`}
                                >
                                    {isActive && <div className="absolute start-0 top-1/2 h-8 w-1 -translate-y-1/2 rounded-e-full bg-primary" />}
                                    <Icon size={21} className={`shrink-0 transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`} aria-hidden="true" />
                                    {!(isDesktop && isSidebarCollapsed) && <span className="min-w-0 break-words text-sm animate-in fade-in">{item.label}</span>}
                                </Link>
                            );

                            if (isDesktop && isSidebarCollapsed) {
                                return (
                                    <Tooltip key={item.path} content={item.label} side={i18n.language === 'ar' ? 'left' : 'right'}>
                                        {link}
                                    </Tooltip>
                                );
                            }
                            return link;
                        })}

                        <div className="mt-auto border-t border-border/50 pt-4">
                            {!(isDesktop && isSidebarCollapsed) && currentUser && (
                                <div className="mb-4 flex min-w-0 items-center gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-800/50">
                                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 font-bold text-primary">
                                        {currentUser.name ? currentUser.name.charAt(0).toUpperCase() : <User size={20} />}
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <p className="truncate text-sm font-bold text-slate-800 dark:text-slate-200">{currentUser.name || t('sidebar.user')}</p>
                                        <p className="truncate text-xs capitalize text-slate-500">{currentUser.role}</p>
                                    </div>
                                </div>
                            )}

                            <div className={`grid ${isDesktop && isSidebarCollapsed ? 'grid-cols-1 gap-2' : 'grid-cols-2 gap-3'} mb-3`}>
                                <button
                                    type="button"
                                    onClick={() => i18n.changeLanguage(i18n.language === 'ar' ? 'en' : 'ar')}
                                    className="flex min-h-11 items-center justify-center rounded-2xl bg-surface-hover text-slate-600 transition-all hover:bg-primary/10 hover:text-primary dark:text-slate-300"
                                    title={t('common.language')}
                                    aria-label={t('common.language')}
                                >
                                    <Globe size={20} aria-hidden="true" />
                                </button>
                                <button
                                    type="button"
                                    onClick={toggleDarkMode}
                                    className="flex min-h-11 items-center justify-center rounded-2xl bg-surface-hover text-slate-600 transition-all hover:bg-amber-400/10 hover:text-amber-500 dark:text-slate-300"
                                    title={isDarkMode ? t('sidebar.mode.light') : t('sidebar.mode.dark')}
                                    aria-label={isDarkMode ? t('sidebar.mode.light') : t('sidebar.mode.dark')}
                                >
                                    {isDarkMode ? <Sun size={20} aria-hidden="true" /> : <Moon size={20} aria-hidden="true" />}
                                </button>
                            </div>

                            <Link
                                to="/support"
                                onClick={() => {
                                    if (!isDesktop) setSidebarOpen(false);
                                }}
                                className={`flex min-h-11 w-full items-center justify-center gap-3 rounded-2xl px-4 py-2.5 text-slate-600 transition-colors hover:bg-indigo-50 hover:text-indigo-600 dark:text-slate-300 dark:hover:bg-indigo-500/10 dark:hover:text-indigo-400 lg:justify-start ${location.pathname === '/support' ? 'bg-indigo-50 font-bold text-indigo-600 dark:bg-indigo-900/20' : 'font-medium'}`}
                            >
                                <HelpCircle size={21} className="shrink-0" aria-hidden="true" />
                                {!(isDesktop && isSidebarCollapsed) && <span className="text-sm font-medium animate-in fade-in">{t('common.help_support')}</span>}
                            </Link>

                            <button
                                type="button"
                                onClick={() => logout()}
                                className="mt-2 flex min-h-11 w-full items-center justify-center gap-3 rounded-2xl px-4 py-2.5 text-red-500 transition-colors hover:bg-red-50 hover:text-red-600 lg:justify-start"
                            >
                                <LogOut size={21} className="shrink-0" aria-hidden="true" />
                                {!(isDesktop && isSidebarCollapsed) && <span className="text-sm font-bold animate-in fade-in">{t('sidebar.logout')}</span>}
                            </button>

                            {!isAdmin && !isSuperAdmin && !(isDesktop && isSidebarCollapsed) && (
                                <div className="mt-4 rounded-xl bg-surface-hover p-3 text-center sm:p-4">
                                    <p className="text-xs text-text-secondary">{t('sidebar.limited_account')}</p>
                                </div>
                            )}
                        </div>
                    </nav>
                </aside>

                <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-background/50">
                    <header className="sticky top-0 z-30 flex min-h-16 shrink-0 items-center gap-2 border-b border-border/60 bg-surface/95 px-2.5 py-2 shadow-sm backdrop-blur-xl sm:px-4 md:px-6 lg:px-8">
                        <div className="flex min-w-0 shrink items-center gap-1.5 lg:hidden sm:gap-2">
                            <button
                                ref={menuButtonRef}
                                type="button"
                                onClick={() => setSidebarOpen(true)}
                                aria-label={t('common.open_menu', 'Open Menu')}
                                aria-expanded={sidebarOpen}
                                className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-slate-600 transition-colors hover:bg-slate-100 active:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800"
                            >
                                <Menu size={23} aria-hidden="true" />
                            </button>
                            <p className="hidden max-w-[11rem] truncate text-sm font-bold text-text-primary min-[430px]:block sm:max-w-[14rem] sm:text-base" dir="auto">
                                {tenant?.name || currentUser?.tenant?.name || t('common.default_clinic_name')}
                            </p>
                        </div>

                        <div className="mx-auto flex min-w-0 flex-1 items-center justify-end gap-2 sm:max-w-xl sm:gap-3">
                            <GlobalSearch />
                            <div className="hidden lg:block">
                                <NotificationBell />
                            </div>
                        </div>
                        <div className="shrink-0 lg:hidden">
                            <NotificationBell />
                        </div>
                    </header>

                    <main className="relative min-h-0 min-w-0 flex-1 overflow-y-auto px-3 py-4 sm:p-4 lg:p-8" id="main-content">
                        <ErrorBoundary fallback={<GlobalErrorFallback />}>
                            <Suspense fallback={
                                <div className="flex min-h-[50dvh] items-center justify-center">
                                    <LoadingSpinner variant="page" />
                                </div>
                            }>
                                <motion.div
                                    key={location.pathname}
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.2, ease: 'easeOut' }}
                                    className="min-h-full min-w-0"
                                >
                                    <Outlet />
                                </motion.div>
                            </Suspense>
                        </ErrorBoundary>
                    </main>

                    <Suspense fallback={null}>
                        <AIChat />
                    </Suspense>
                </div>
            </div>
        </div>
    );
};

export default Layout;
