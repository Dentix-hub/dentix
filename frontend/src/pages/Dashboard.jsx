import { useState, useMemo, memo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Users, Calendar, Activity, Clock,
    TrendingUp, Wallet, Stethoscope, ChevronLeft
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
    AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts';
import { getTodayPayments, getTodayDebtors } from '@/api';
import { useDashboardStats } from '@/hooks/useDashboard';
import { useAppointments } from '@/hooks/useAppointments';
import { useAuth } from '@/auth/useAuth';
import { Card, Button, Modal } from '@/shared/ui';
// Memoized Gradient Card - prevents re-renders when parent state changes
const GradientCard = memo(({ title, value, subtext, icon: Icon, gradient, onClick }) => (
    <div
        onClick={onClick}
        className={`relative overflow-hidden rounded-2xl p-6 text-white shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-[1.02] cursor-pointer group ${gradient}`}
    >
        <div className="relative z-10 flex flex-col h-full justify-between">
            <div className="flex justify-between items-start">
                <div className="p-3 bg-white/20 backdrop-blur-md rounded-2xl">
                    <Icon size={24} className="text-white" />
                </div>
            </div>
            <div className="mt-4">
                <p className="text-white/80 text-sm font-medium mb-1">{title}</p>
                <h3 className="text-3xl font-black tracking-tight">{value}</h3>
                <p className="text-white/60 text-xs mt-2 font-medium bg-black/10 inline-block px-2 py-1 rounded-lg">
                    {subtext}
                </p>
            </div>
        </div>
        <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl group-hover:scale-150 transition-transform duration-700"></div>
    </div>
));
GradientCard.displayName = 'GradientCard';
export default function Dashboard() {
    const navigate = useNavigate();
    const { user } = useAuth();
    const { t } = useTranslation();
    // Use cached hooks instead of direct API calls
    const { data: statsData, isLoading: statsLoading } = useDashboardStats();
    const { data: appointments = [], isLoading: apptsLoading } = useAppointments();
    const loading = statsLoading || apptsLoading;
    // Derive stats from cached data
    const stats = useMemo(() => ({
        new_patients_today: statsData?.new_patients_today || 0,
        appointments: statsData?.total_appointments_today || 0,
        revenue: statsData?.today_received || 0,
        outstanding: statsData?.outstanding || 0,
        chartData: statsData?.revenue_chart || []
    }), [statsData]);
    // Filter today's appointments from cached data
    const todaysAppointments = useMemo(() => {
        if (!Array.isArray(appointments)) return [];
        const today = new Date().toISOString().split('T')[0];
        return appointments
            .filter(app => app.date_time?.startsWith(today) && app.status !== 'Cancelled')
            .sort((a, b) => new Date(a.date_time) - new Date(b.date_time));
    }, [appointments]);
    // Modal State
    const [modalOpen, setModalOpen] = useState(false);
    const [modalTitle, setModalTitle] = useState('');
    const [modalData, setModalData] = useState([]);
    const [modalLoading, setModalLoading] = useState(false);
    const [modalType, setModalType] = useState(null);
    const formatCurrency = useCallback((amount) => {
        return new Intl.NumberFormat('en-EG', { style: 'currency', currency: 'EGP', maximumFractionDigits: 0 }).format(amount);
    }, []);
    const handleRevenueClick = useCallback(async () => {
        setModalTitle(t('dashboard.daily_income_details'));
        setModalOpen(true);
        setModalLoading(true);
        setModalType('payments');
        try {
            const res = await getTodayPayments();
            setModalData(res.data);
        } catch (err) { /* Silent */ }
        finally { setModalLoading(false); }
    }, [t]);
    const handleOutstandingClick = useCallback(async () => {
        setModalTitle(t('dashboard.outstanding_today'));
        setModalOpen(true);
        setModalLoading(true);
        setModalType('debtors');
        try {
            const res = await getTodayDebtors();
            setModalData(res.data);
        } catch (err) { /* Silent */ }
        finally { setModalLoading(false); }
    }, [t]);
    return (
        <div className="space-y-8 animate-in fade-in zoom-in-95 duration-500 pb-10">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-center gap-4 bg-surface/50 backdrop-blur-sm p-6 rounded-2xl border border-border">
                <div className="flex items-center gap-4 w-full md:w-auto">
                    <div className="w-14 h-14 bg-gradient-to-tr from-indigo-500 to-teal-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                        <Stethoscope size={28} />
                    </div>
                    <div>
                        {loading ? (
                            <div className="space-y-2 w-48">
                                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full animate-pulse"></div>
                                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4 animate-pulse"></div>
                            </div>
                        ) : (
                            <>
                                <h1 className="text-2xl font-black text-text-primary tracking-tight">
                                    {t('dashboard.welcome', { name: user?.username })}
                                </h1>
                                <p className="text-text-secondary text-sm font-medium">
                                    {t('dashboard.clinic_overview_today')}
                                </p>
                            </>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-3 w-full md:w-auto">
                    <div className="px-5 py-3 bg-surface-hover rounded-2xl font-bold text-text-secondary text-sm flex items-center gap-2 border border-border">
                        <Clock size={18} className="text-primary" />
                        {new Date().toLocaleDateString(t('language.switch_to_en') === 'English' ? 'ar-EG' : 'en-US', { weekday: 'long', day: 'numeric', month: 'long' })}
                    </div>
                </div>
            </div>
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 stats-grid">
                {loading ? (
                    Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center gap-4">
                            <div className="w-14 h-14 bg-slate-200 rounded-xl animate-pulse"></div>
                            <div className="flex-1 space-y-2">
                                <div className="h-3 bg-slate-200 rounded w-1/2 animate-pulse"></div>
                                <div className="h-5 bg-slate-200 rounded w-3/4 animate-pulse"></div>
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
                            gradient="bg-gradient-to-br from-blue-500 to-blue-600"
                            onClick={() => navigate('/patients')}
                        />
                        <GradientCard
                            title={t('dashboard.appointments_today')}
                            value={stats.appointments}
                            subtext={t('dashboard.confirmed_booking')}
                            icon={Calendar}
                            gradient="bg-gradient-to-br from-teal-500 to-teal-600"
                            onClick={() => navigate('/appointments')}
                        />
                        <GradientCard
                            title={t('dashboard.daily_income')}
                            value={formatCurrency(stats.revenue)}
                            subtext={t('dashboard.cash_collection')}
                            icon={Wallet}
                            gradient="bg-gradient-to-br from-emerald-500 to-emerald-600"
                            onClick={handleRevenueClick}
                        />
                        <GradientCard
                            title={t('dashboard.outstanding_dues')}
                            value={formatCurrency(stats.outstanding)}
                            subtext={t('dashboard.to_collect')}
                            icon={Activity}
                            gradient="bg-gradient-to-br from-amber-500 to-amber-600"
                            onClick={handleOutstandingClick}
                        />
                    </>
                )}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Chart Section */}
                <div className="lg:col-span-2 space-y-8">
                    <Card className="min-h-[400px]">
                        <div className="flex justify-between items-center mb-8">
                            <div>
                                <h3 className="text-xl font-bold text-text-primary flex items-center gap-2">
                                    <TrendingUp className="text-primary" />
                                    {t('dashboard.revenue_analysis')}
                                </h3>
                                <p className="text-sm text-text-secondary mt-1">{t('dashboard.revenue_growth')}</p>
                            </div>
                        </div>
                        <div className="h-[300px] w-full" style={{ direction: 'ltr' }}>
                            {loading ? (
                                <div className="h-full w-full bg-slate-100 rounded-2xl animate-pulse"></div>
                            ) : stats.chartData.length > 0 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={stats.chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                                        <defs>
                                            <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                                                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12, fontWeight: 600 }} dy={10} />
                                        <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12, fontWeight: 600 }} />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.9)', borderRadius: '16px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}
                                            itemStyle={{ color: '#1e293b', fontWeight: 'bold' }}
                                            formatter={(value) => formatCurrency(value)}
                                            cursor={{ stroke: '#6366f1', strokeWidth: 2, strokeDasharray: '4 4' }}
                                        />
                                        <Area
                                            type="monotone"
                                            dataKey="revenue"
                                            stroke="#6366f1"
                                            strokeWidth={4}
                                            fillOpacity={1}
                                            fill="url(#colorRevenue)"
                                            activeDot={{ r: 8, strokeWidth: 0, fill: '#4f46e5' }}
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-text-secondary gap-4">
                                    <div className="w-16 h-16 bg-surface-hover rounded-full flex items-center justify-center text-3xl">
                                        📊
                                    </div>
                                    <p>{t('dashboard.no_financial_data')}</p>
                                </div>
                            )}
                        </div>
                    </Card>
                </div>
                {/* Left Sidebar: Timeline */}
                <div className="space-y-6">
                    <Card className="h-full relative overflow-hidden transition-all duration-300 hover:shadow-lg">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="font-bold text-lg text-text-primary flex items-center gap-2">
                                <Calendar className="text-primary" size={20} />
                                {t('dashboard.appointments_today')}
                            </h3>
                            <span className="bg-primary/10 text-primary px-3 py-1 rounded-lg text-xs font-bold">
                                {t('dashboard.appointments_count', { count: loading ? '...' : todaysAppointments.length })}
                            </span>
                        </div>
                        <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                            {loading ? (
                                <div className="space-y-3">
                                    {Array.from({length: 5}).map((_, i) => (
                                        <div key={i} className="h-10 bg-slate-100 rounded-lg animate-pulse w-full"></div>
                                    ))}
                                </div>
                            ) : todaysAppointments.length > 0 ? todaysAppointments.map((appt) => (
                                <div
                                    key={appt.id}
                                    className="relative pl-4 border-r-2 border-border pr-4 py-1 group cursor-pointer"
                                    onClick={() => navigate('/appointments')}
                                >
                                    {/* Timeline Dot */}
                                    <div className={`absolute -right-[9px] top-3 w-4 h-4 rounded-full border-2 border-background ${appt.status === 'Completed' ? 'bg-emerald-500' :
                                        appt.status === 'Cancelled' ? 'bg-red-500' : 'bg-primary'
                                        }`}></div>
                                    <div className="bg-surface-hover p-4 rounded-xl group-hover:bg-primary/5 transition-colors">
                                        <div className="flex justify-between items-start mb-1">
                                            <h4 className="font-bold text-text-primary">{appt.patient_name}</h4>
                                            <span className="text-xs font-bold font-mono text-text-secondary bg-background px-2 py-1 rounded-md border border-border">
                                                {new Date(appt.date_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        </div>
                                        <p className="text-xs text-text-secondary line-clamp-1">
                                            {appt.notes || 'زيارة عادية - كشف'}
                                        </p>
                                    </div>
                                </div>
                            )) : (
                                <div className="flex flex-col items-center justify-center py-12 text-center">
                                    <div className="bg-surface-hover p-4 rounded-full mb-4">
                                        <Calendar size={32} className="text-text-secondary" />
                                    </div>
                                    <p className="text-text-secondary font-medium">{t('dashboard.no_appointments_today')}</p>
                                    <Button variant="ghost" size="sm" onClick={() => navigate('/appointments')} className="mt-2">
                                        + {t('dashboard.add_new_appointment')}
                                    </Button>
                                </div>
                            )}
                        </div>
                        {!loading && todaysAppointments.length > 0 && (
                            <Button
                                variant="secondary"
                                className="w-full mt-6"
                                onClick={() => navigate('/appointments')}
                            >
                                {t('dashboard.view_full_schedule')}
                                <ChevronLeft size={16} className="mr-2" />
                            </Button>
                        )}
                    </Card>
                </div>
            </div>
            {/* Reusable Modal for Revenue/Debtors */}
            <Modal
                isOpen={modalOpen}
                onClose={() => setModalOpen(false)}
                title={modalTitle}
                size="md"
            >
                <div className="space-y-3">
                    {modalLoading ? (
                        <div className="flex flex-col gap-3">
                            <div className="animate-pulse bg-slate-200 dark:bg-slate-700/50 rounded-xl h-[4rem] w-full" />
                            <div className="animate-pulse bg-slate-200 dark:bg-slate-700/50 rounded-xl h-[4rem] w-full" />
                            <div className="animate-pulse bg-slate-200 dark:bg-slate-700/50 rounded-xl h-[4rem] w-full" />
                        </div>
                    ) : modalData.length > 0 ? modalData.map((item, idx) => (
                        <div key={idx} className="flex justify-between items-center p-4 bg-surface-hover rounded-2xl border border-border">
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-xl flex items-center justify-center w-10 h-10 ${modalType === 'payments' ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-600'}`}>
                                    <span className="text-xl leading-none">
                                        {modalType === 'payments' ? '💰' : '📈'}
                                    </span>
                                </div>
                                <div>
                                    <p className="font-bold text-text-primary">{item.patient_name || item.name}</p>
                                    <p className="text-xs text-text-secondary">{new Date(item.date || new Date()).toLocaleTimeString()}</p>
                                </div>
                            </div>
                            <span className="font-black text-lg dir-ltr text-text-primary">{formatCurrency(item.amount)}</span>
                        </div>
                    )) : (
                        <div className="text-center py-8">
                            <p className="text-text-secondary">{t('dashboard.no_data')}</p>
                        </div>
                    )}
                </div>
            </Modal>
        </div>
    );
}
const ActionButton = ({ icon: Icon, label, color, onClick }) => (
    <button
        onClick={onClick}
        className={`${color} text-white p-4 rounded-2xl shadow-lg shadow-indigo-500/20 hover:scale-105 transition-all flex flex-col items-center justify-center gap-2 group`}
    >
        <div className="bg-white/20 p-2 rounded-full group-hover:rotate-12 transition-transform">
            <Icon size={24} />
        </div>
        <span className="font-bold text-sm whitespace-nowrap">{label}</span>
    </button>
);

