import { lazy, memo, useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
    Users,
    Calendar,
    Activity,
    TrendingUp,
    Wallet,
    ChevronLeft,
    Home,
    Clock
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { LazyChart } from '@/components/charts/LazyChart';
import { motion } from '@/lib/motion';
import { queryKeys } from '@/lib/queryClient';
import { getTodayPayments, getTodayDebtors } from '@/api';
import { useDashboardStats } from '@/hooks/useDashboard';
import { useAppointments } from '@/hooks/useAppointments';
import { useAuth } from '@/auth/useAuth';
import { useTenantStore } from '@/store/tenant.store';
import { Card, Button, Modal, PageHeader, toast, AdvancedTable } from '@/shared/ui';
import DashboardQuickActions from '@/features/dashboard/DashboardQuickActions';
import {
    DashboardSourceError,
    DashboardStaleWarning,
    DashboardUnavailableNotice,
} from '@/features/dashboard/DashboardStateFeedback';
import {
    buildDashboardSessionScopeKey,
    computeStatusDistribution,
    discardDeniedData,
    formatDashboardCurrency,
    isAuthorizationError,
    isUsableAppointmentsData,
    isUsableStatsData,
    resolveSourceState,
    resolveTodaySectionState,
} from '@/features/dashboard/dashboardDataState';
import PatientModal from '@/features/patients/modals/PatientModal.jsx';

const RevenueChart = lazy(() => import('@/features/dashboard/DashboardCharts').then(module => ({ default: module.RevenueChart })));
const StatusChart = lazy(() => import('@/features/dashboard/DashboardCharts').then(module => ({ default: module.StatusChart })));

// Tracks only the last clinic/actor scope key seen per QueryClient instance (never stores data).
const lastDashboardScopeByClient = new WeakMap();

const GradientCard = memo(({ title, value, subtext, icon: Icon, gradient, onClick }) => (
    <button
        type="button"
        onClick={onClick}
        className={`group relative min-h-36 w-full min-w-0 overflow-hidden rounded-2xl p-3 text-start text-white shadow-medium transition-[box-shadow,transform] duration-300 hover:-translate-y-0.5 hover:shadow-high focus-visible:ring-white sm:min-h-40 sm:rounded-3xl sm:p-5 lg:p-6 ${gradient}`}
    >
        <span className="relative z-10 flex h-full min-w-0 flex-col justify-between">
            <span className="flex items-start justify-between">
                <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/20 backdrop-blur-md sm:h-12 sm:w-12 sm:rounded-2xl">
                    <Icon size={22} className="text-white sm:h-6 sm:w-6" aria-hidden="true" />
                </span>
            </span>
            <span className="mt-3 min-w-0">
                <span className="mb-1 block break-words text-xs font-medium text-white/85 sm:text-sm">{title}</span>
                <strong className="block min-w-0 break-words text-xl font-extrabold tracking-tight text-white sm:text-2xl lg:text-3xl" dir="auto">{value}</strong>
                <span className="mt-2 inline-block max-w-full break-words rounded-lg bg-black/10 px-2 py-1 text-[9px] font-bold uppercase tracking-wide text-white/70 sm:text-[10px] sm:tracking-widest">
                    {subtext}
                </span>
            </span>
        </span>
        <span aria-hidden="true" className="absolute -bottom-10 -end-10 h-32 w-32 rounded-full bg-white/10 blur-3xl transition-transform duration-700 group-hover:scale-125 sm:h-40 sm:w-40" />
    </button>
));
GradientCard.displayName = 'GradientCard';

export default function Dashboard() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { user } = useAuth();
    const tenant = useTenantStore((state) => state.tenant);
    const { t, i18n } = useTranslation();

    const sessionScopeKey = buildDashboardSessionScopeKey({ user, tenant });
    const [activeScopeKey, setActiveScopeKey] = useState(
        () => lastDashboardScopeByClient.get(queryClient) ?? sessionScopeKey,
    );
    const scopeMatches = activeScopeKey === sessionScopeKey;

    const statsQuery = useDashboardStats();
    const appointmentsQuery = useAppointments();
    const { refetch: refetchStats, error: statsError, failureReason: statsFailure } = statsQuery;
    const { refetch: refetchAppointments, error: appointmentsError, failureReason: appointmentsFailure } = appointmentsQuery;
    const isStatsDataRevoked = isAuthorizationError(statsError) || isAuthorizationError(statsFailure);
    const isAppointmentsDataRevoked = isAuthorizationError(appointmentsError) || isAuthorizationError(appointmentsFailure);

    useEffect(() => {
        if (!scopeMatches) {
            queryClient.resetQueries({ queryKey: queryKeys.dashboardStats, exact: true });
            queryClient.resetQueries({ queryKey: queryKeys.appointments, exact: true });
            setActiveScopeKey(sessionScopeKey);
        }
        lastDashboardScopeByClient.set(queryClient, sessionScopeKey);
    }, [scopeMatches, sessionScopeKey, queryClient]);

    useEffect(() => {
        if (isStatsDataRevoked) discardDeniedData(queryClient, queryKeys.dashboardStats);
        if (isAppointmentsDataRevoked) discardDeniedData(queryClient, queryKeys.appointments);
    }, [isStatsDataRevoked, isAppointmentsDataRevoked, queryClient]);

    const [modalOpen, setModalOpen] = useState(false);
    const [modalTitle, setModalTitle] = useState('');
    const [modalData, setModalData] = useState([]);
    const [modalLoading, setModalLoading] = useState(false);
    const [modalType, setModalType] = useState(null);
    const [isPatientModalOpen, setIsPatientModalOpen] = useState(false);

    const uiLanguage = i18n.resolvedLanguage || i18n.language || 'ar';
    const isArabic = String(uiLanguage).toLowerCase().startsWith('ar');

    const formatCurrency = useCallback(
        (amount) => formatDashboardCurrency(amount, uiLanguage),
        [uiLanguage],
    );

    const statsState = useMemo(() => resolveSourceState({
        data: statsQuery.data,
        isPending: statsQuery.isPending,
        isError: statsQuery.isError,
        error: statsQuery.error,
        isFetching: statsQuery.isFetching,
        isUsable: isUsableStatsData,
        scopeMatches,
        isDataRevoked: isStatsDataRevoked,
    }), [
        statsQuery.data,
        statsQuery.isPending,
        statsQuery.isError,
        statsQuery.error,
        statsQuery.isFetching,
        scopeMatches,
        isStatsDataRevoked,
    ]);

    const appointmentsState = useMemo(() => resolveSourceState({
        data: appointmentsQuery.data,
        isPending: appointmentsQuery.isPending,
        isError: appointmentsQuery.isError,
        error: appointmentsQuery.error,
        isFetching: appointmentsQuery.isFetching,
        isUsable: isUsableAppointmentsData,
        scopeMatches,
        isDataRevoked: isAppointmentsDataRevoked,
    }), [
        appointmentsQuery.data,
        appointmentsQuery.isPending,
        appointmentsQuery.isError,
        appointmentsQuery.error,
        appointmentsQuery.isFetching,
        scopeMatches,
        isAppointmentsDataRevoked,
    ]);

    const statsMetrics = useMemo(() => {
        if (!statsState.data) return null;
        return {
            new_patients_today: statsState.data.new_patients_today,
            appointments: statsState.data.total_appointments_today,
            revenue: statsState.data.today_received,
            outstanding: statsState.data.today_outstanding,
            chartData: Array.isArray(statsState.data.revenue_chart) ? statsState.data.revenue_chart : [],
        };
    }, [statsState.data]);

    const todayState = useMemo(
        () => resolveTodaySectionState({ statsState, appointmentsState }),
        [statsState, appointmentsState],
    );

    const statusDistribution = useMemo(
        () => (appointmentsState.data ? computeStatusDistribution(appointmentsState.data, t) : []),
        [appointmentsState.data, t],
    );

    const handleRetryStats = useCallback(() => {
        refetchStats();
    }, [refetchStats]);

    const handleRetryAppointments = useCallback(() => {
        refetchAppointments();
    }, [refetchAppointments]);

    const statsRetryAction = useMemo(() => ({
        key: 'retry-stats',
        label: t('dashboard.retry_stats'),
        loadingLabel: t('dashboard.retrying'),
        loading: statsState.isRetrying,
        onClick: handleRetryStats,
    }), [t, statsState.isRetrying, handleRetryStats]);

    const appointmentsRetryAction = useMemo(() => ({
        key: 'retry-appointments',
        label: t('dashboard.retry_appointments'),
        loadingLabel: t('dashboard.retrying'),
        loading: appointmentsState.isRetrying,
        onClick: handleRetryAppointments,
    }), [t, appointmentsState.isRetrying, handleRetryAppointments]);

    const todayErrorActions = useMemo(() => {
        const actions = [];
        if (todayState.statsFailed) actions.push(statsRetryAction);
        if (todayState.appointmentsFailed) actions.push(appointmentsRetryAction);
        return actions;
    }, [todayState.statsFailed, todayState.appointmentsFailed, statsRetryAction, appointmentsRetryAction]);

    const handleRevenueClick = useCallback(async () => {
        setModalTitle(t('dashboard.daily_income_details'));
        setModalOpen(true);
        setModalLoading(true);
        setModalType('payments');
        try {
            const res = await getTodayPayments();
            setModalData(res.data);
        } catch {
            toast.error(t('common.error_loading_data'));
        } finally {
            setModalLoading(false);
        }
    }, [t]);

    const handleOutstandingClick = useCallback(async () => {
        setModalTitle(t('dashboard.outstanding_today'));
        setModalOpen(true);
        setModalLoading(true);
        setModalType('debtors');
        try {
            const res = await getTodayDebtors();
            setModalData(res.data);
        } catch {
            toast.error(t('common.error_loading_data'));
        } finally {
            setModalLoading(false);
        }
    }, [t]);

    const modalColumns = useMemo(() => {
        const columns = [
            {
                header: t('common.patient', 'Patient'),
                accessorKey: modalType === 'payments' ? 'patient_name' : 'name',
                cell: ({ row }) => (
                    <div className="flex min-w-0 items-center gap-2 sm:gap-3">
                        <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${modalType === 'payments' ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-600'}`}>
                            <span className="text-sm" aria-hidden="true">{modalType === 'payments' ? '💰' : '📈'}</span>
                        </div>
                        <span className="min-w-0 break-words font-bold" dir="auto">{row.original.patient_name || row.original.name}</span>
                    </div>
                )
            }
        ];

        if (modalType === 'payments') {
            columns.push({
                header: t('common.time', 'Time'),
                accessorKey: 'date',
                cell: ({ getValue }) => {
                    const value = getValue();
                    return (
                        <span className="font-medium text-slate-500" dir="ltr">
                            {value ? new Date(value).toLocaleTimeString(isArabic ? 'ar-EG' : 'en-US', { hour: '2-digit', minute: '2-digit' }) : '-'}
                        </span>
                    );
                }
            });
        }

        columns.push({
            header: t('common.amount', 'Amount'),
            accessorKey: 'amount',
            cell: ({ getValue }) => <span className="break-words text-base font-bold text-primary sm:text-lg" dir="auto">{formatCurrency(getValue())}</span>
        });

        return columns;
    }, [modalType, t, formatCurrency, isArabic]);

    const todayCountLabel = useMemo(() => {
        if (todayState.status === 'loading') {
            return t('dashboard.appointments_count', { val: '...' });
        }
        if (todayState.status === 'ready') {
            return t('dashboard.appointments_count', { val: todayState.todaysAppointments.length });
        }
        return t('dashboard.unavailable');
    }, [todayState, t]);

    const todayErrorCopy = useMemo(() => {
        if (todayState.statsFailed && todayState.appointmentsFailed) {
            return {
                title: t('common.error_loading_data'),
                scheduleDesc: t('dashboard.today_both_error_desc'),
                efficiencyDesc: t('dashboard.efficiency_both_error_desc'),
            };
        }
        if (todayState.statsFailed) {
            return {
                title: todayState.statsAuthError ? t('common.access_denied') : t('dashboard.stats_load_error_title'),
                scheduleDesc: todayState.statsAuthError
                    ? t('dashboard.access_denied_stats')
                    : t('dashboard.today_stats_error_desc'),
                efficiencyDesc: todayState.statsAuthError
                    ? t('dashboard.access_denied_stats')
                    : t('dashboard.efficiency_stats_error_desc'),
            };
        }
        return {
            title: todayState.appointmentsAuthError ? t('common.access_denied') : t('dashboard.appointments_load_error_title'),
            scheduleDesc: todayState.appointmentsAuthError
                ? t('dashboard.access_denied_appointments')
                : t('dashboard.appointments_load_error_desc'),
            efficiencyDesc: todayState.appointmentsAuthError
                ? t('dashboard.access_denied_appointments')
                : t('dashboard.efficiency_appointments_error_desc'),
        };
    }, [todayState, t]);

    return (
        <div className="min-w-0 space-y-5 pb-8 animate-in fade-in zoom-in-95 duration-500 sm:space-y-6 sm:pb-10">
            <PageHeader
                title={t('dashboard.welcome', { name: user?.username })}
                subtitle={t('dashboard.clinic_overview_today')}
                breadcrumbs={[{ label: t('sidebar.dashboard'), icon: Home }]}
            />

            <DashboardQuickActions onAddPatient={() => setIsPatientModalOpen(true)} />

            {(statsState.isStale || appointmentsState.isStale) && (
                <div className="space-y-2.5">
                    {statsState.isStale && (
                        <DashboardStaleWarning
                            testId="dashboard-stats-stale-warning"
                            retryTestId="dashboard-retry-stats-stale"
                            message={t('dashboard.stale_stats_warning')}
                            retryLabel={t('dashboard.retry_stats')}
                            retryingLabel={t('dashboard.retrying')}
                            isRetrying={statsState.isRetrying}
                            onRetry={handleRetryStats}
                        />
                    )}
                    {appointmentsState.isStale && (
                        <DashboardStaleWarning
                            testId="dashboard-appointments-stale-warning"
                            retryTestId="dashboard-retry-appointments-stale"
                            message={t('dashboard.stale_appointments_warning')}
                            retryLabel={t('dashboard.retry_appointments')}
                            retryingLabel={t('dashboard.retrying')}
                            isRetrying={appointmentsState.isRetrying}
                            onRetry={handleRetryAppointments}
                        />
                    )}
                </div>
            )}

            <div className="stats-grid grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 lg:gap-6">
                {statsState.status === 'loading' ? (
                    Array.from({ length: 4 }).map((_, index) => (
                        <div key={index} className="flex min-h-36 min-w-0 flex-col justify-between rounded-2xl border border-slate-100 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-800 sm:min-h-40 sm:rounded-3xl sm:p-5">
                            <div className="h-10 w-10 rounded-xl bg-slate-200 animate-pulse dark:bg-slate-700 sm:h-12 sm:w-12" />
                            <div className="space-y-2">
                                <div className="h-3 w-2/3 rounded bg-slate-200 animate-pulse dark:bg-slate-700" />
                                <div className="h-6 w-3/4 rounded bg-slate-200 animate-pulse dark:bg-slate-700" />
                            </div>
                        </div>
                    ))
                ) : statsState.status === 'error' ? (
                    <div className="col-span-2 lg:col-span-4">
                        <DashboardSourceError
                            testId="dashboard-stats-error"
                            title={statsState.isAuthError ? t('common.access_denied') : t('dashboard.stats_load_error_title')}
                            description={statsState.isAuthError ? t('dashboard.access_denied_stats') : t('dashboard.stats_load_error_desc')}
                            actions={[statsRetryAction]}
                        />
                    </div>
                ) : (
                    <>
                        <GradientCard
                            title={t('dashboard.new_patients_today')}
                            value={statsMetrics.new_patients_today}
                            subtext={t('dashboard.registered_today')}
                            icon={Users}
                            gradient="bg-gradient-to-br from-primary to-primary-700"
                            onClick={() => navigate('/patients')}
                        />
                        <GradientCard
                            title={t('dashboard.appointments_today')}
                            value={statsMetrics.appointments}
                            subtext={t('dashboard.confirmed_booking')}
                            icon={Calendar}
                            gradient="bg-gradient-to-br from-teal-500 to-cyan-600"
                            onClick={() => navigate('/appointments')}
                        />
                        <GradientCard
                            title={t('dashboard.daily_income')}
                            value={formatCurrency(statsMetrics.revenue)}
                            subtext={t('dashboard.cash_collection')}
                            icon={Wallet}
                            gradient="bg-gradient-to-br from-emerald-500 to-emerald-700"
                            onClick={handleRevenueClick}
                        />
                        <GradientCard
                            title={t('dashboard.outstanding_today')}
                            value={formatCurrency(statsMetrics.outstanding)}
                            subtext={t('dashboard.to_collect')}
                            icon={Activity}
                            gradient="bg-gradient-to-br from-amber-500 to-orange-600"
                            onClick={handleOutstandingClick}
                        />
                    </>
                )}
            </div>

            <div className="grid min-w-0 grid-cols-1 gap-5 lg:grid-cols-3 lg:gap-8">
                <div className="min-w-0 space-y-5 lg:col-span-2 lg:space-y-8">
                    <Card className="min-w-0 sm:min-h-[400px] lg:min-h-[450px]">
                        <div className="mb-4 flex min-w-0 items-start justify-between gap-3 sm:mb-6 lg:mb-8">
                            <div className="min-w-0">
                                <h3 className="flex min-w-0 items-center gap-2 text-base font-bold text-text-primary sm:text-xl">
                                    <TrendingUp className="shrink-0 text-primary" aria-hidden="true" />
                                    <span className="min-w-0 break-words">{t('dashboard.revenue_analysis')}</span>
                                </h3>
                                <p className="mt-1 break-words text-xs text-text-secondary sm:text-sm">{t('dashboard.revenue_growth')}</p>
                            </div>
                        </div>
                        <div className="h-[230px] min-w-0 w-full sm:h-[280px] lg:h-[320px]">
                            {statsState.status === 'loading' ? (
                                <div className="h-full w-full rounded-2xl bg-slate-100 animate-pulse dark:bg-slate-800/50 sm:rounded-3xl" />
                            ) : statsState.status === 'error' ? (
                                <div className="flex h-full items-center justify-center">
                                    <DashboardSourceError
                                        testId="dashboard-revenue-error"
                                        compact
                                        title={statsState.isAuthError ? t('common.access_denied') : t('dashboard.stats_load_error_title')}
                                        description={statsState.isAuthError ? t('dashboard.access_denied_stats') : t('dashboard.revenue_load_error_desc')}
                                        actions={[statsRetryAction]}
                                    />
                                </div>
                            ) : statsMetrics.chartData.some(point => Number(point.revenue) !== 0) ? (
                                <div className="h-full w-full" style={{ direction: 'ltr' }}>
                                    <LazyChart>
                                        <RevenueChart data={statsMetrics.chartData} formatCurrency={formatCurrency} revenueLabel={t('dashboard.revenue')} />
                                    </LazyChart>
                                </div>
                            ) : (
                                <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-text-secondary">
                                    <div className="flex h-14 w-14 items-center justify-center rounded-full bg-surface-hover text-2xl">📊</div>
                                    <p className="text-sm">{t('dashboard.no_financial_data')}</p>
                                </div>
                            )}
                        </div>
                    </Card>

                    <div className="grid min-w-0 grid-cols-1 gap-4 md:grid-cols-2 lg:gap-6">
                        <Card className="min-w-0">
                            <h4 className="mb-4 flex min-w-0 items-center gap-2 font-bold text-text-primary sm:mb-6">
                                <Activity className="shrink-0 text-primary" size={18} aria-hidden="true" />
                                <span className="break-words">{t('dashboard.status_distribution')}</span>
                            </h4>
                            <div className="min-h-[180px] min-w-0 w-full sm:min-h-[200px]">
                                {appointmentsState.status === 'loading' ? (
                                    <div className="h-[180px] w-full rounded-2xl bg-slate-100 animate-pulse dark:bg-slate-800/50 sm:h-[200px]" />
                                ) : appointmentsState.status === 'error' ? (
                                    <div className="flex min-h-[180px] items-center justify-center sm:min-h-[200px]">
                                        <DashboardSourceError
                                            testId="dashboard-status-error"
                                            compact
                                            title={appointmentsState.isAuthError ? t('common.access_denied') : t('dashboard.appointments_load_error_title')}
                                            description={appointmentsState.isAuthError ? t('dashboard.access_denied_appointments') : t('dashboard.status_load_error_desc')}
                                            actions={[appointmentsRetryAction]}
                                        />
                                    </div>
                                ) : statusDistribution.length > 0 ? (
                                    <div className="h-[180px] w-full sm:h-[200px]" style={{ direction: 'ltr' }}>
                                        <LazyChart>
                                            <StatusChart data={statusDistribution} />
                                        </LazyChart>
                                    </div>
                                ) : (
                                    <div className="flex h-[180px] items-center justify-center text-sm text-text-secondary sm:h-[200px]">
                                        {t('dashboard.no_data')}
                                    </div>
                                )}
                            </div>
                        </Card>

                        <Card className="flex min-w-0 flex-col items-center justify-center bg-gradient-to-br from-primary/5 to-transparent p-4 text-center sm:p-6 lg:p-8">
                            <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary sm:mb-4 sm:h-16 sm:w-16 sm:rounded-3xl">
                                <TrendingUp size={28} aria-hidden="true" />
                            </div>
                            <h4 className="mb-2 break-words text-base font-bold text-text-primary sm:text-lg">{t('dashboard.clinic_efficiency')}</h4>
                            <p className="mb-4 break-words text-xs text-text-secondary sm:mb-6 sm:text-sm">{t('dashboard.efficiency_description')}</p>
                            {todayState.status === 'loading' ? (
                                <div className="w-full space-y-2" data-testid="dashboard-efficiency-loading">
                                    <div className="h-2 w-full rounded-full bg-slate-200 animate-pulse dark:bg-slate-700" />
                                    <div className="flex w-full items-center justify-between gap-2">
                                        <span className="h-3 w-24 rounded bg-slate-200 animate-pulse dark:bg-slate-700" />
                                        <span className="h-3 w-10 rounded bg-slate-200 animate-pulse dark:bg-slate-700" />
                                    </div>
                                </div>
                            ) : todayState.status === 'error' ? (
                                <DashboardSourceError
                                    testId="dashboard-efficiency-error"
                                    compact
                                    title={todayErrorCopy.title}
                                    description={todayErrorCopy.efficiencyDesc}
                                    actions={todayErrorActions}
                                />
                            ) : todayState.status === 'missing_business_date' ? (
                                <DashboardUnavailableNotice
                                    testId="dashboard-efficiency-unavailable"
                                    compact
                                    title={t('dashboard.business_date_unavailable_title')}
                                    description={t('dashboard.business_date_unavailable_efficiency')}
                                    action={statsRetryAction}
                                />
                            ) : (
                                <>
                                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                                        <motion.div initial={{ width: 0 }} animate={{ width: `${todayState.efficiency}%` }} className="h-full bg-primary" />
                                    </div>
                                    <div className="mt-2 flex w-full items-center justify-between gap-2">
                                        <span className="min-w-0 break-words text-[10px] font-bold uppercase tracking-wide text-slate-500">{t('dashboard.efficiency_rate')}</span>
                                        <span className="shrink-0 text-[10px] font-bold uppercase tracking-widest text-primary">{todayState.efficiency}%</span>
                                    </div>
                                </>
                            )}
                        </Card>
                    </div>
                </div>

                <div className="min-w-0 space-y-5 lg:space-y-6">
                    <Card className="relative h-full min-w-0 overflow-hidden transition-shadow duration-300 hover:shadow-lg">
                        <div className="mb-4 flex min-w-0 items-start justify-between gap-2 sm:mb-6">
                            <h3 className="flex min-w-0 items-center gap-2 text-base font-bold text-text-primary sm:text-lg">
                                <Calendar className="shrink-0 text-primary" size={20} aria-hidden="true" />
                                <span className="break-words">{t('dashboard.appointments_today')}</span>
                            </h3>
                            <span
                                data-testid="dashboard-today-count"
                                className="shrink-0 rounded-lg bg-primary/10 px-2 py-1 text-xs font-bold text-primary sm:px-3"
                            >
                                {todayCountLabel}
                            </span>
                        </div>

                        <div
                            data-testid="dashboard-today-list"
                            className="max-h-[420px] min-w-0 space-y-2 overflow-y-auto overscroll-contain pe-1 sm:max-h-[500px] sm:space-y-3"
                        >
                            {todayState.status === 'loading' ? (
                                Array.from({ length: 5 }).map((_, index) => <div key={index} className="h-16 w-full rounded-xl bg-slate-100 animate-pulse dark:bg-slate-800" />)
                            ) : todayState.status === 'error' ? (
                                <DashboardSourceError
                                    testId="dashboard-today-error"
                                    compact
                                    title={todayErrorCopy.title}
                                    description={todayErrorCopy.scheduleDesc}
                                    actions={todayErrorActions}
                                />
                            ) : todayState.status === 'missing_business_date' ? (
                                <DashboardUnavailableNotice
                                    testId="dashboard-today-unavailable"
                                    compact
                                    title={t('dashboard.business_date_unavailable_title')}
                                    description={t('dashboard.business_date_unavailable_schedule')}
                                    action={statsRetryAction}
                                />
                            ) : todayState.todaysAppointments.length > 0 ? (
                                todayState.todaysAppointments.map((appointment) => (
                                    <button
                                        key={appointment.id}
                                        type="button"
                                        onClick={() => navigate('/appointments')}
                                        className="flex min-h-16 w-full min-w-0 items-start gap-3 rounded-2xl border border-border/70 bg-surface-hover p-3 text-start transition-colors hover:border-primary/30 hover:bg-primary/5 sm:p-4"
                                    >
                                        <span className={`mt-1 h-3 w-3 shrink-0 rounded-full ${appointment.status === 'Completed' ? 'bg-emerald-500' : appointment.status === 'Cancelled' ? 'bg-red-500' : 'bg-primary'}`} aria-hidden="true" />
                                        <span className="min-w-0 flex-1">
                                            <span className="flex min-w-0 flex-col gap-1 min-[360px]:flex-row min-[360px]:items-start min-[360px]:justify-between">
                                                <strong className="min-w-0 break-words text-sm text-text-primary" dir="auto">{appointment.patient_name}</strong>
                                                <span className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-border bg-background px-2 py-1 text-xs font-bold text-text-secondary" dir="ltr">
                                                    <Clock size={12} aria-hidden="true" />
                                                    {new Date(appointment.date_time).toLocaleTimeString(isArabic ? 'ar-EG' : 'en-US', { hour: '2-digit', minute: '2-digit' })}
                                                </span>
                                            </span>
                                            <span className="mt-1 line-clamp-2 block break-words text-xs text-text-secondary">{appointment.notes || t('appointments.table.regular_visit')}</span>
                                        </span>
                                    </button>
                                ))
                            ) : (
                                <div className="flex flex-col items-center justify-center py-8 text-center sm:py-12">
                                    <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-surface-hover sm:mb-4">
                                        <Calendar size={28} className="text-text-secondary" aria-hidden="true" />
                                    </div>
                                    <p className="font-medium text-text-secondary">{t('dashboard.no_appointments_today')}</p>
                                    <Button variant="ghost" size="sm" onClick={() => navigate('/appointments')} className="mt-2 min-h-11">
                                        + {t('dashboard.add_new_appointment')}
                                    </Button>
                                </div>
                            )}
                        </div>

                        {(todayState.status === 'ready') && todayState.todaysAppointments.length > 0 && (
                            <Button variant="secondary" className="mt-4 min-h-11 w-full justify-center rounded-2xl sm:mt-6" onClick={() => navigate('/appointments')}>
                                {t('dashboard.view_full_schedule')}
                                <ChevronLeft size={16} className="me-2 rtl:rotate-180" aria-hidden="true" />
                            </Button>
                        )}
                    </Card>
                </div>
            </div>

            <PatientModal isOpen={isPatientModalOpen} onClose={() => setIsPatientModalOpen(false)} />

            <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={modalTitle} size="lg">
                <AdvancedTable
                    data={modalData}
                    columns={modalColumns}
                    isLoading={modalLoading}
                    emptyMessage={t('dashboard.no_data')}
                    pagination={modalData.length > 5}
                    pageSize={5}
                />
            </Modal>
        </div>
    );
}
