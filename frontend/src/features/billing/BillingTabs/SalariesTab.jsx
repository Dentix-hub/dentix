import { Check, Trash2 } from 'lucide-react';
import { Button, Card, Badge, SkeletonBox, EmptyState, DateTimePicker } from '@/shared/ui';

import { useTranslation } from 'react-i18next';

const SalariesTab = ({ salaryMonth, setSalaryMonth, salariesData, salariesLoading, updateEmployeeHireDate, roleLabels, handlePaySalary, deleteSalaryPayment, loadSalaries }) => {
    const { t } = useTranslation();
    return (
        <div className="space-y-6">
            <Card className="flex flex-col md:flex-row items-center justify-between p-6">
                <div>
                    <h2 className="text-xl font-black text-text-primary mb-1">{t('billing.salaries.title')}</h2>
                    <p className="text-sm text-text-secondary">{t('billing.salaries.subtitle')}</p>
                </div>
                <div className="flex items-center gap-4 mt-4 md:mt-0">
                    <label className="font-bold text-text-secondary text-sm">{t('billing.salaries.month_label')}</label>
                    <DateTimePicker
                        mode="month"
                        value={salaryMonth}
                        onChange={(e) => setSalaryMonth(e.target.value)}
                    />
                </div>
            </Card>

            <Card className="overflow-hidden">
                <div className="overflow-x-auto">
                    {salariesLoading ? (
                        <div className="p-6 space-y-4">
                            {[1, 2, 3].map(i => <SkeletonBox key={i} className="h-12 w-full rounded-xl" />)}
                        </div>
                    ) : salariesData.length > 0 ? (
                        <table className="w-full text-right text-sm">
                            <thead className="bg-surface-hover text-text-secondary font-bold text-xs border-b border-border">
                                <tr>
                                    <th className="p-4">{t('billing.salaries.employee')}</th>
                                    <th className="p-4">{t('billing.salaries.hire_date')}</th>
                                    <th className="p-4">{t('billing.salaries.base_salary')}</th>
                                    <th className="p-4">{t('billing.salaries.work_days')}</th>
                                    <th className="p-4">{t('billing.salaries.payable')}</th>
                                    <th className="p-4">{t('billing.salaries.status')}</th>
                                    <th className="p-4">{t('billing.salaries.actions')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {salariesData.map(emp => (
                                    <tr key={emp.id} className="hover:bg-surface-hover transition-colors">
                                        <td className="p-4">
                                            <div className="font-bold text-text-primary">{emp.username}</div>
                                            <div className="text-xs text-text-secondary">{roleLabels[emp.role] || emp.role}</div>
                                        </td>
                                        <td className="p-4 w-40">
                                            <DateTimePicker
                                                mode="date"
                                                value={emp.hire_date || ''}
                                                onChange={(e) => updateEmployeeHireDate(emp.id, e.target.value)}
                                            />
                                        </td>
                                        <td className="p-4 font-bold text-text-primary">{emp.base_salary.toLocaleString()}</td>
                                        <td className="p-4">
                                            {emp.is_new_this_month ? (
                                                <span className="text-warning font-bold text-xs" title="تعيين جديد هذا الشهر">{emp.days_worked} {t('billing.salaries.new_employee_day')}</span>
                                            ) : (
                                                <span className="text-text-secondary text-xs">{t('billing.salaries.full_month')}</span>
                                            )}
                                        </td>
                                        <td className="p-4">
                                            <span className={`font-black ${emp.is_new_this_month ? 'text-warning' : 'text-text-primary'}`}>
                                                {emp.prorated_salary.toLocaleString()}
                                            </span>
                                            {emp.is_new_this_month && <div className="text-[10px] text-warning">{t('billing.salaries.partial_pay')}</div>}
                                        </td>
                                        <td className="p-4">
                                            {emp.is_paid ? (
                                                <Badge variant="success">{t('billing.salaries.paid')}</Badge>
                                            ) : (
                                                <Badge variant="default">{t('billing.salaries.unpaid')}</Badge>
                                            )}
                                        </td>
                                        <td className="p-4">
                                            {emp.is_paid ? (
                                                <div className="flex items-center gap-2">
                                                    <div className="text-xs text-text-secondary">
                                                        <div>{new Date(emp.payment.payment_date).toLocaleDateString()}</div>
                                                        <div className="font-bold">{emp.payment.amount}</div>
                                                    </div>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={async () => {
                                                            if (confirm(t('billing.alerts.cancel_pay_confirm'))) {
                                                                await deleteSalaryPayment(emp.payment.id);
                                                                loadSalaries();
                                                            }
                                                        }}
                                                        className="text-danger hover:bg-red-50 dark:hover:bg-red-900/10"
                                                        title={t('billing.salaries.cancel_pay')}
                                                    >
                                                        <Trash2 size={16} />
                                                    </Button>
                                                </div>
                                            ) : (
                                                <Button
                                                    size="sm"
                                                    onClick={() => handlePaySalary(emp, emp.is_new_this_month)}
                                                >
                                                    {t('billing.salaries.record_pay')}
                                                </Button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <div className="p-8">
                            <EmptyState
                                icon={Check}
                                title={t('billing.salaries.no_employees')}
                                description={t('billing.salaries.no_employees_desc')}
                            />
                        </div>
                    )}
                </div>
            </Card>
        </div>
    );
};

export default SalariesTab;
