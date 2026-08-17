import { Card } from '@/shared/ui';
import { useTranslation } from 'react-i18next';

export default function DeductionsBreakdown({ comprehensiveStats, formatCurrency }) {
    const { t } = useTranslation();

    return (
        <Card className="overflow-hidden">
            <div className="p-6 border-b border-border flex items-center gap-4 bg-surface">
                <div className="w-1.5 h-8 bg-danger rounded-full"></div>
                <h3 className="font-bold text-xl text-text-primary">{t('billing.summary.deductions_title')}</h3>
            </div>
            <div className="p-6 space-y-4">
                {/* Doctor Dues */}
                <div className="p-4 bg-teal-50 dark:bg-teal-900/10 rounded-xl border border-teal-100 dark:border-teal-900/20">
                    <div className="flex items-center justify-between mb-3">
                        <h4 className="font-bold text-teal-700 dark:text-teal-400">{t('billing.summary.doctor_dues')}</h4>
                        <span className="font-bold text-xl text-teal-600">-{formatCurrency(comprehensiveStats?.deductions?.doctor_dues?.total || 0)}</span>
                    </div>
                    {comprehensiveStats?.deductions?.doctor_dues?.details?.map(doc => (
                        <div key={doc.id} className="flex items-center justify-between text-sm py-1 border-t border-teal-100 dark:border-teal-900/20">
                            <span className="text-text-secondary">{doc.name} - {t('billing.summary.commission')} {doc.commission_percent}% + {t('billing.summary.salary')} {doc.fixed_salary}</span>
                            <div className="text-end">
                                <span className="font-bold text-teal-600">{formatCurrency(doc.total_due)}</span>
                                <p className="text-[11px] text-text-secondary mt-0.5">
                                    {t('billing.summary.collected', 'Collected')}: {formatCurrency(doc.collected)} · {t('billing.summary.commission', 'Commission')}: {formatCurrency(doc.commission_amount)}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
                {/* Staff Dues */}
                <div className="p-4 bg-blue-50 dark:bg-blue-900/10 rounded-xl border border-blue-100 dark:border-blue-900/20">
                    <div className="flex items-center justify-between mb-3">
                        <h4 className="font-bold text-blue-700 dark:text-blue-400">{t('billing.summary.staff_dues')}</h4>
                        <span className="font-bold text-xl text-blue-600">-{formatCurrency(comprehensiveStats?.deductions?.staff_dues?.total || 0)}</span>
                    </div>
                    {comprehensiveStats?.deductions?.staff_dues?.details?.map(s => (
                        <div key={s.id} className="flex items-center justify-between text-sm py-1 border-t border-blue-100 dark:border-blue-900/20">
                            <span className="text-text-secondary">{s.name} - {t('billing.summary.salary')} {s.fixed_salary} + ({s.per_appointment_fee} × {s.appointments_in_period} {t('billing.summary.appointment')})</span>
                            <span className="font-bold text-blue-600">{formatCurrency(s.total_due)}</span>
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
                        <span className="font-bold text-xl text-orange-600">-{formatCurrency(comprehensiveStats?.deductions?.lab_costs || 0)}</span>
                    </div>
                </div>
                {/* Expenses */}
                <div className="p-4 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-100 dark:border-red-900/20">
                    <div className="flex items-center justify-between">
                        <h4 className="font-bold text-red-700 dark:text-red-400">{t('billing.summary.other_expenses')}</h4>
                        <span className="font-bold text-xl text-red-600">-{formatCurrency(comprehensiveStats?.deductions?.expenses || 0)}</span>
                    </div>
                </div>
            </div>
        </Card>
    );
}
