import { TrendingUp, Banknote, DollarSign, Calendar } from 'lucide-react';
import { Button, Card, StatCard } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
const SummaryTab = ({ startDate, setStartDate, endDate, setEndDate, comprehensiveStats, loading, getComprehensiveStats, setComprehensiveStats, setLoading }) => {
    const { t } = useTranslation();
    return (
        <div className="space-y-6">
            {/* Date Range Picker */}
            <Card className="flex items-center justify-between p-4">
                <h3 className="font-bold text-text-primary">{t('billing.summary.period')}</h3>
                <div className="flex items-center gap-3 bg-surface p-2 rounded-xl border border-border">
                    <div className="flex items-center gap-2">
                        <Calendar size={16} className="text-text-secondary" />
                        <span className="text-xs font-bold text-text-secondary">{t('billing.summary.from')}</span>
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="bg-transparent border-none text-sm font-bold text-text-primary focus:ring-0 p-0 w-28"
                        />
                    </div>
                    <div className="w-px h-4 bg-border"></div>
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-text-secondary">{t('billing.summary.to')}</span>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="bg-transparent border-none text-sm font-bold text-text-primary focus:ring-0 p-0 w-28"
                        />
                    </div>
                    <Button
                        onClick={async () => {
                            setLoading(true);
                            try {
                                const res = await getComprehensiveStats(startDate, endDate);
                                setComprehensiveStats(res.data);
                            } catch (err) { console.error(err); }
                            finally { setLoading(false); }
                        }}
                        variant="success"
                        size="sm"
                        isLoading={loading}
                    >
                        {t('billing.summary.calculate')}
                    </Button>
                </div>
            </Card>
            {/* Header Cards - Income */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard
                    title={t('billing.summary.total_revenue')}
                    value={`${(comprehensiveStats?.income?.total_revenue || 0).toLocaleString()}`}
                    icon={TrendingUp}
                    color="success"
                />
                <StatCard
                    title={t('billing.summary.total_collected')}
                    value={`${(comprehensiveStats?.income?.total_collected || 0).toLocaleString()}`}
                    icon={Banknote}
                    color="info"
                />
                <StatCard
                    title={t('billing.summary.outstanding')}
                    value={`${(comprehensiveStats?.income?.outstanding || 0).toLocaleString()}`}
                    icon={DollarSign}
                    color="warning"
                />
                <StatCard
                    title={t('billing.summary.patient_count')}
                    value={comprehensiveStats?.income?.unique_patients || 0}
                    icon={Calendar}
                    color="primary"
                />
            </div>
            {/* Deductions Breakdown */}
            <Card className="overflow-hidden">
                <div className="p-6 border-b border-border flex items-center gap-4 bg-surface">
                    <div className="w-1.5 h-8 bg-danger rounded-full"></div>
                    <h3 className="font-black text-xl text-text-primary">{t('billing.summary.deductions_title')}</h3>
                </div>
                <div className="p-6 space-y-4">
                    {/* Doctor Dues */}
                    <div className="p-4 bg-teal-50 dark:bg-teal-900/10 rounded-xl border border-teal-100 dark:border-teal-900/20">
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="font-bold text-teal-700 dark:text-teal-400">{t('billing.summary.doctor_dues')}</h4>
                            <span className="font-black text-xl text-teal-600">-{(comprehensiveStats?.deductions?.doctor_dues?.total || 0).toLocaleString()}</span>
                        </div>
                        {comprehensiveStats?.deductions?.doctor_dues?.details?.map(doc => (
                            <div key={doc.id} className="flex items-center justify-between text-sm py-1 border-t border-teal-100 dark:border-teal-900/20">
                                <span className="text-text-secondary">{doc.name} - {t('billing.summary.commission')} {doc.commission_percent}% + {t('billing.summary.salary')} {doc.fixed_salary}</span>
                                <span className="font-bold text-teal-600">{doc.total_due.toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                    {/* Staff Dues */}
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/10 rounded-xl border border-blue-100 dark:border-blue-900/20">
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="font-bold text-blue-700 dark:text-blue-400">{t('billing.summary.staff_dues')}</h4>
                            <span className="font-black text-xl text-blue-600">-{(comprehensiveStats?.deductions?.staff_dues?.total || 0).toLocaleString()}</span>
                        </div>
                        {comprehensiveStats?.deductions?.staff_dues?.details?.map(s => (
                            <div key={s.id} className="flex items-center justify-between text-sm py-1 border-t border-blue-100 dark:border-blue-900/20">
                                <span className="text-text-secondary">{s.name} - {t('billing.summary.salary')} {s.fixed_salary} + ({s.per_appointment_fee} × {s.appointments_in_period} {t('billing.summary.appointment')})</span>
                                <span className="font-bold text-blue-600">{s.total_due.toLocaleString()}</span>
                            </div>
                        ))}
                        {(!comprehensiveStats?.deductions?.staff_dues?.details?.length) && (
                            <p className="text-sm text-text-muted">{t('billing.summary.no_employees')}</p>
                        )}
                    </div>
                    {/* Lab Costs */}
                    <div className="p-4 bg-orange-50 dark:bg-orange-900/10 rounded-xl border border-orange-100 dark:border-orange-900/20">
                        <div className="flex items-center justify-between">
                            <h4 className="font-bold text-orange-700 dark:text-orange-400">{t('billing.summary.lab_costs')}</h4>
                            <span className="font-black text-xl text-orange-600">-{(comprehensiveStats?.deductions?.lab_costs || 0).toLocaleString()}</span>
                        </div>
                    </div>
                    {/* Expenses */}
                    <div className="p-4 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-100 dark:border-red-900/20">
                        <div className="flex items-center justify-between">
                            <h4 className="font-bold text-red-700 dark:text-red-400">{t('billing.summary.other_expenses')}</h4>
                            <span className="font-black text-xl text-red-600">-{(comprehensiveStats?.deductions?.expenses || 0).toLocaleString()}</span>
                        </div>
                    </div>
                </div>
            </Card>
            {/* Net Profit */}
            <div className={`p-8 rounded-2xl text-center ${(comprehensiveStats?.net_profit || 0) >= 0 ? 'bg-gradient-to-br from-emerald-500 to-emerald-600' : 'bg-gradient-to-br from-red-500 to-red-600'} text-white shadow-xl`}>
                <p className="text-white/80 font-bold mb-2">{t('billing.summary.net_profit_after')}</p>
                <p className="text-5xl font-black">{(comprehensiveStats?.net_profit || 0).toLocaleString()}</p>
                <p className="text-sm text-white/60 mt-3">{t('billing.summary.net_profit_equation')}</p>
            </div>
        </div>
    );
};
export default SummaryTab;
