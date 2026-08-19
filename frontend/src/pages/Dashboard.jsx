import { memo, useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
    LazyChart
} from '@/components/charts/LazyChart';
import { motion } from '@/lib/motion';
import { getTodayPayments, getTodayDebtors } from '@/api';
import { useDashboardStats } from '@/hooks/useDashboard';
import { useAppointments } from '@/hooks/useAppointments';
import { useAuth } from '@/auth/useAuth';
import { Card, Button, Modal, PageHeader, toast, AdvancedTable } from '@/shared/ui';
import DashboardQuickActions from '@/features/dashboard/DashboardQuickActions';
import PatientModal from '@/features/patients/modals/PatientModal.jsx';
import { selectAppointmentsForBusinessDate } from '@/utils/dateTime';

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
    const { user } = useAuth();
    const { t, i18n } = useTranslation();
    const { data: statsData, isLoading: statsLoading } = useDashboardStats();
    const { data: appointments = [], isLoading: apptsLoading } = useAppointments();
    const loading = statsLoading || apptsLoading;

    const [modalOpen, setModalOpen] = useState(false);
    const [modalTitle, setModalTitle] = useState('');
    const [modalData, setModalData] = useState([]);
    const [modalLoading, setModalLoading] = useState(false);
    const [modalType, setModalType] = useState(null);
    const [isPatientModalOpen, setIsPatientModalOpen] = useState(false);

    const formatCurrency = useCallback((amount) => new Intl.NumberFormat('en-EG', {
        style: 'currency',
        currency: 'EGP',
        maximumFractionDigits: 0
    }).format(amount), []);

    const stats = useMemo(() => {
        const businessDate = statsData?.business_date;
        const todayAppts = selectAppointmentsForBusinessDate(appointments, businessDate);
        const visibleTodayAppts = todayAppts.filter(appointment => appointment.status !== 'Cancelled');
        const completed = visibleTodayAppts.filter(appointment => appointment.status === 'Completed').length;
        const efficiency = visibleTodayAppts.length > 0
            ? Math.round((completed / visibleTodayAppts.length) * 100)
            : 0;

        return {
            new_patients_today: statsData?.new_patients_today ?? 0,
            appointments: statsData?.total_appointments_today ?? 0,
            revenue: statsData?.today_received ?? 0,
            outstanding: statsData?.today_outstanding ?? 0,
            chartData: statsData?.revenue_chart ?? [],
            efficiency,
            todaysAppointments: [...visibleTodayAppts].sort((a, b) => String(a.date_time || '').localeCompare(String(b.date_time || '')))
        };
    }, [statsData, appointments]);

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
                            {value ? new Date(value).toLocaleTimeString(i18n.language === 'ar' ? 'ar-EG' : 'en-US', { hour: '2-digit', minute: '2-digit' }) : '-'}
                        </span>
                    );
                }
            });
        }

        columns.push({
            header: t('common.amount', 'Amount'),
            accessorKey: 'amount',
            cell: ({ getValue }) => <span className="break-words text-base font-bold text-primary sm:text-lg" dir="ltr">{formatCurrency(getValue())}</span>
        });

        return columns;
    }, [modalType, t, formatCurrency, i18n.language]);

    const statusDistribution = useMemo(() => [
        { name: t('appointments.status.completed'), value: appointments.filter(appointment => appointment.status === 'Completed').length, fill: '#10b981' },
        { name: t('appointments.status.scheduled'), value: appointments.filter(appointment => appointment.status === 'Scheduled').length, fill: '#0891B2' },
        { name: t('appointments.status.waiting'), value: appointments.filter(appointment => appointment.status === 'Waiting').length, fill: '#f59e0b' },
        { name: t('appointments.status.cancelled'), value: appointments.filter(appointment => appointment.status === 'Cancelled' || appointment.status === 'No Show').length, fill: '#ef4444' },
    ].filter(item => item.value > 0), [appointments, t]);

    return (
        <div className="min-w-0 space-y-5 pb-8 animate-in fade-in zoom-in-95 duration-500 sm:space-y-6 sm:pb-10">
            <PageHeader
                title={t('dashboard.welcome', { name: user?.username })}
                subtitle={t('dashboard.clinic_overview_today')}
                breadcrumbs={[{ label: t('sidebar.dashboard'), icon: Home }]}
            />

            <DashboardQuickActions onAddPatient={() => setIsPatientModalOpen(true)} />

            <div className="stats-grid grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 lg:gap-6">
                {loading ? (
                    Array.from({ length: 4 }).map((_, index) => (
                        <div key={index} className="flex min-h-36 min-w-0 flex-col justify-between rounded-2xl border border-slate-100 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-800 sm:min-h-40 sm:rounded-3xl sm:p-5">
                            <div className="h-10 w-10 rounded-xl bg-slate-200 animate-pulse dark:bg-slate-700 sm:h-12 sm:w-12" />
                            <div className="space-y-2">
                                <div className="h-3 w-2/3 rounded bg-slate-200 animate-pulse dark:bg-slate-700" />
                                <div className="h-6 w-3/4 rounded bg-slate-200 animate-pulse dark:bg-slate-700" />
                            </div>
                        </div>
                    ))
                ) : (
                    <>
                        <GradientCard
                            title={t('dashboard.new_patients_today')}
                            value={stats.new_patients_today}
                            subtext={t('dashboard.registered_today')}
                            icon={Users}
                            gradient="bg-gradient-to-br from-primary to-primary-700"
                            onClick={() => navigate('/patients')}
                        />
                        <GradientCard
                            title={t('dashboard.appointments_today')}
                            value={stats.appointments}
                            subtext={t('dashboard.confirmed_booking')}
                            icon={Calendar}
                            gradient="bg-gradient-to-br from-teal-500 to-cyan-600"
                            onClick={() => navigate('/appointments')}
                        />
                        <GradientCard
                            title={t('dashboard.daily_income')}
                            value={formatCurrency(stats.revenue)}
                            subtext={t('dashboard.cash_collection')}
                            icon={Wallet}
                            gradient="bg-gradient-to-br from-emerald-500 to-emerald-700"
                            onClick={handleRevenueClick}
                        />
                        <GradientCard
                            title={t('dashboard.outstanding_today')}
                            value={formatCurrency(stats.outstanding)}
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
                        <div className="h-[230px] min-w-0 w-full sm:h-[280px] lg:h-[320px]" style={{ direction: 'ltr' }}>
                            {loading ? (
                                <div className="h-full w-full rounded-2xl bg-slate-100 animate-pulse dark:bg-slate-800/50 sm:rounded-3xl" />
                            ) : stats.chartData.length > 0 ? (
                                <LazyChart>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <AreaChart data={stats.chartData} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
                                            <defs>
                                                <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#0891B2" stopOpacity={0.3} />
                                                    <stop offset="95%" stopColor="#0891B2" stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 9, fontWeight: 700 }} dy={8} minTickGap={18} />
                                            <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 9, fontWeight: 700 }} width={42} />
                                            <Tooltip
                                                contentStyle={{
                                                    backgroundColor: 'rgba(255, 255, 255, 0.98)',
                                                    borderRadius: '14px',
                                                    border: 'none',
                                                    boxShadow: '0 12px 28px rgba(15, 23, 42, 0.16)',
                                                    padding: '10px'
                                                }}
                                                itemStyle={{ color: '#1e293b', fontWeight: '800', fontSize: '12px' }}
                                                formatter={(value) => [formatCurrency(value), t('dashboard.revenue')]}
                                                cursor={{ stroke: '#0891B2', strokeWidth: 2, strokeDasharray: '6 6' }}
                                            />
                                            <Area type="monotone" dataKey="revenue" stroke="#0891B2" strokeWidth={3} fillOpacity={1} fill="url(#colorRevenue)" activeDot={{ r: 6, strokeWidth: 0, fill: '#0891B2' }} />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </LazyChart>
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
                            <div className="h-[180px] min-w-0 w-full sm:h-[200px]" style={{ direction: 'ltr' }}>
                                <LazyChart>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie data={statusDistribution} innerRadius="50%" outerRadius="78%" paddingAngle={5} dataKey="value">
                                                {statusDistribution.map(item => <Cell key={item.name} fill={item.fill} />)}
                                            </Pie>
                                            <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 18px rgba(15,23,42,.12)', fontSize: '12px' }} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </LazyChart>
                            </div>
                        </Card>

                        <Card className="flex min-w-0 flex-col items-center justify-center bg-gradient-to-br from-primary/5 to-transparent p-4 text-center sm:p-6 lg:p-8">
                            <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary sm:mb-4 sm:h-16 sm:w-16 sm:rounded-3xl">
                                <TrendingUp size={28} aria-hidden="true" />
                            </div>
                            <h4 className="mb-2 break-words text-base font-bold text-text-primary sm:text-lg">{t('dashboard.clinic_efficiency')}</h4>
                            <p className="mb-4 break-words text-xs text-text-secondary sm:mb-6 sm:text-sm">{t('dashboard.efficiency_description')}</p>
                            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                                <motion.div initial={{ width: 0 }} animate={{ width: `${stats.efficiency}%` }} className="h-full bg-primary" />
                            </div>
                            <div className="mt-2 flex w-full items-center justify-between gap-2">
                                <span className="min-w-0 break-words text-[10px] font-bold uppercase tracking-wide text-slate-500">{t('dashboard.efficiency_rate')}</span>
                                <span className="shrink-0 text-[10px] font-bold uppercase tracking-widest text-primary">{stats.efficiency}%</span>
                            </div>
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
                            <span className="shrink-0 rounded-lg bg-primary/10 px-2 py-1 text-xs font-bold text-primary sm:px-3">
                                {t('dashboard.appointments_count', { val: loading ? '...' : stats.todaysAppointments.length })}
                            </span>
                        </div>

                        <div className="max-h-[420px] min-w-0 space-y-2 overflow-y-auto overscroll-contain pe-1 sm:max-h-[500px] sm:space-y-3">
                            {loading ? (
                                Array.from({ length: 5 }).map((_, index) => <div key={index} className="h-16 w-full rounded-xl bg-slate-100 animate-pulse dark:bg-slate-800" />)
                            ) : stats.todaysAppointments.length > 0 ? (
                                stats.todaysAppointments.map((appointment) => (
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
                                                    {new Date(appointment.date_time).toLocaleTimeString(i18n.language === 'ar' ? 'ar-EG' : 'en-US', { hour: '2-digit', minute: '2-digit' })}
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

                        {!loading && stats.todaysAppointments.length > 0 && (
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
