import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
    Users,
    DollarSign,
    CheckCircle2,
    Clock,
    AlertCircle,
    Settings,
    Trash2,
    PlusCircle,
    Calendar,
    Sparkles,
} from 'lucide-react';
import { usePayroll } from '../payroll/hooks/usePayroll';
import { useFinancePermissions } from '../useFinancePermissions';
import MetricCard from '../components/MetricCard';
import FilterBar from '../components/FilterBar';
import MonthPicker from '../payroll/components/MonthPicker';
import DataTable from '../components/DataTable';
import Money from '../components/Money';
import SalaryPaymentDrawer from '../payroll/components/SalaryPaymentDrawer';
import StaffSettingsDrawer from '../payroll/components/StaffSettingsDrawer';

/**
 * Payroll V2 Workspace (§16 MASTER_SPEC).
 * Manages monthly employee salaries, prorating, partial/full payments, and staff compensation rules.
 */
export default function PayrollPage() {
    const { t } = useTranslation();
    const { canWriteFinance, canConfigFinance } = useFinancePermissions();

    const {
        month,
        employees,
        totalPayable,
        totalPaid,
        totalRemaining,
        employeeCount,
        search,
        isLoading,
        isError,
        refetch,
        setMonth,
        updateSearch,
        recordPayment,
        isRecording,
        deletePayment,
        isDeleting,
        updateStaffRules,
        isUpdatingRules,
    } = usePayroll();

    const [selectedEmployeeForPayment, setSelectedEmployeeForPayment] = useState(null);
    const [selectedEmployeeForRules, setSelectedEmployeeForRules] = useState(null);

    // Status Helper
    const getStatusInfo = (emp) => {
        const status = emp.status || (emp.is_paid ? 'paid' : (emp.payment?.is_partial ? 'partial' : 'unpaid'));
        if (status === 'unpaid') {
            return {
                label: t('finance.payroll.status_unpaid', 'غير مسدد'),
                colorClass: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
                icon: Clock,
            };
        }
        if (status === 'partial') {
            return {
                label: t('finance.payroll.status_partial', 'مسدد جزئياً'),
                colorClass: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
                icon: AlertCircle,
            };
        }
        return {
            label: t('finance.payroll.status_paid', 'مسدد بالكامل'),
            colorClass: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
            icon: CheckCircle2,
        };
    };

    // Columns Definition for DataTable
    const columns = [
        {
            id: 'employee',
            header: t('finance.payroll.employee_name', 'الموظف'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <span className="font-bold text-text-primary block">{row.username}</span>
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-muted font-medium text-text-secondary inline-block">
                        {row.role}
                    </span>
                </div>
            ),
        },
        {
            id: 'base_salary',
            header: t('finance.payroll.base_salary', 'الراتب الأساسي'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.base_salary} size="sm" />
            ),
        },
        {
            id: 'prorating',
            header: t('finance.payroll.days_count', 'الأيام المحتسبة'),
            sortable: false,
            width: '130px',
            cell: (row) => (
                <div className="text-xs text-text-secondary">
                    {row.is_new_this_month ? (
                        <span className="text-primary font-semibold block">
                            {row.days_worked} / {row.days_in_month} {t('common.days', 'يوم')}
                        </span>
                    ) : (
                        <span>{row.days_in_month} {t('common.days', 'يوم')}</span>
                    )}
                </div>
            ),
        },
        {
            id: 'payable',
            header: t('finance.payroll.payable', 'المستحق'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.payable_amount !== undefined ? row.payable_amount : row.prorated_salary} size="sm" />
            ),
        },
        {
            id: 'paid',
            header: t('finance.payroll.paid', 'المسدد'),
            align: 'end',
            sortable: false,
            cell: (row) => {
                const paidAmount = row.paid_amount !== undefined ? row.paid_amount : (row.payment ? row.payment.amount : 0);
                return <Money amount={paidAmount} size="sm" colored />;
            },
        },
        {
            id: 'remaining',
            header: t('finance.payroll.remaining', 'المتبقي'),
            align: 'end',
            sortable: false,
            cell: (row) => {
                const rem = row.remaining_amount !== undefined ? row.remaining_amount : Math.max(0, (row.payable_amount || row.prorated_salary || 0) - (row.paid_amount || 0));
                return <Money amount={rem} size="sm" colored />;
            },
        },
        {
            id: 'status',
            header: t('common.status', 'الحالة'),
            align: 'center',
            sortable: false,
            width: '130px',
            cell: (row) => {
                const status = getStatusInfo(row);
                const StatusIcon = status.icon;
                return (
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${status.colorClass}`}>
                        <StatusIcon className="w-3.5 h-3.5" />
                        <span>{status.label}</span>
                    </span>
                );
            },
        },
        {
            id: 'actions',
            header: t('common.actions', 'إجراءات'),
            align: 'end',
            sortable: false,
            width: '130px',
            cell: (row) => (
                <div className="flex items-center justify-end gap-1.5">
                    {canWriteFinance && (!row.payment || row.payment.is_partial) && (
                        <button
                            type="button"
                            onClick={() => setSelectedEmployeeForPayment(row)}
                            className="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-500/10 transition-colors"
                            title={t('finance.payroll.pay_salary', 'صرف الراتب')}
                        >
                            <DollarSign className="w-4 h-4" />
                        </button>
                    )}
                    {canWriteFinance && row.payment && (
                        <button
                            type="button"
                            onClick={async () => {
                                if (window.confirm(t('finance.payroll.confirm_delete_payment', 'هل أنت متأكد من حذف وإلغاء تسجيل هذا الصرف؟'))) {
                                    await deletePayment(row.payment.id);
                                }
                            }}
                            className="p-1.5 rounded-lg text-destructive hover:bg-destructive/10 transition-colors"
                            title={t('finance.payroll.cancel_payment', 'إلغاء الصرف')}
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    )}
                    {canConfigFinance && (
                        <button
                            type="button"
                            onClick={() => setSelectedEmployeeForRules(row)}
                            className="p-1.5 rounded-lg text-text-secondary hover:text-primary hover:bg-primary/10 transition-colors"
                            title={t('finance.payroll.edit_salary_rules', 'تعديل قاعدة الراتب')}
                        >
                            <Settings className="w-4 h-4" />
                        </button>
                    )}
                </div>
            ),
        },
    ];

    // Mobile Card Render
    const renderMobileCard = (row) => {
        const status = getStatusInfo(row);
        const StatusIcon = status.icon;
        const payableAmount = row.payable_amount !== undefined ? row.payable_amount : (row.prorated_salary || 0);
        const paidAmount = row.paid_amount !== undefined
            ? row.paid_amount
            : (row.payment ? row.payment.amount : 0);
        const rem = row.remaining_amount !== undefined
            ? row.remaining_amount
            : Math.max(0, payableAmount - paidAmount);

        return (
            <div
                key={row.id}
                className="p-4 rounded-xl border border-border bg-card space-y-3 shadow-xs"
            >
                <div className="flex items-start justify-between">
                    <div className="space-y-0.5">
                        <span className="text-sm font-bold text-text-primary block">{row.username}</span>
                        <span className="text-[11px] text-text-secondary">{row.role}</span>
                    </div>
                    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${status.colorClass}`}>
                        <StatusIcon className="w-3 h-3" />
                        <span>{status.label}</span>
                    </span>
                </div>

                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border/40 text-[11px]">
                    <div>
                        <span className="text-text-secondary block">{t('finance.payroll.payable', 'المستحق')}</span>
                        <Money amount={payableAmount} size="xs" />
                    </div>
                    <div>
                        <span className="text-text-secondary block">{t('finance.payroll.paid', 'المسدد')}</span>
                        <Money amount={paidAmount} colored size="xs" />
                    </div>
                    <div className="text-end">
                        <span className="text-text-secondary block">{t('finance.payroll.remaining', 'المتبقي')}</span>
                        <Money amount={rem} colored size="xs" />
                    </div>
                </div>

                <div className="pt-2 border-t border-border/40 flex items-center justify-between">
                    {canConfigFinance ? (
                        <button
                            type="button"
                            onClick={() => setSelectedEmployeeForRules(row)}
                            className="text-xs font-semibold text-text-secondary hover:text-primary flex items-center gap-1"
                        >
                            <Settings className="w-3.5 h-3.5" />
                            <span>{t('finance.payroll.edit_rules', 'تعديل الراتب')}</span>
                        </button>
                    ) : <span />}

                    <div className="flex items-center gap-2">
                        {canWriteFinance && (!row.payment || row.payment.is_partial) && (
                            <button
                                type="button"
                                onClick={() => setSelectedEmployeeForPayment(row)}
                                className="px-3 py-1.5 bg-primary text-white rounded-lg text-xs font-bold shadow-xs hover:bg-primary/90 flex items-center gap-1"
                            >
                                <DollarSign className="w-3.5 h-3.5" />
                                <span>{t('finance.payroll.pay_action', 'صرف')}</span>
                            </button>
                        )}
                        {canWriteFinance && row.payment && (
                            <button
                                type="button"
                                onClick={async () => {
                                    if (window.confirm(t('finance.payroll.confirm_delete_payment', 'هل أنت متأكد من حذف وإلغاء تسجيل هذا الصرف؟'))) {
                                        await deletePayment(row.payment.id);
                                    }
                                }}
                                className="p-1.5 text-destructive hover:bg-destructive/10 rounded-lg text-xs"
                                title={t('finance.payroll.cancel_payment', 'إلغاء')}
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="space-y-6">
            {/* Top Month Controls & Month Summary */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
                <MonthPicker
                    month={month}
                    onChange={setMonth}
                />
            </div>

            {/* Headline Metrics Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard
                    title={t('finance.payroll.total_payable', 'إجمالي الرواتب المستحقة')}
                    amount={totalPayable}
                    scope="period"
                    subtitle={`${employeeCount} ${t('finance.payroll.employees_count', 'موظف مسجل')}`}
                    icon={Users}
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.payroll.total_paid', 'إجمالي الرواتب المسددة')}
                    amount={totalPaid}
                    scope="period"
                    subtitle={t('finance.payroll.paid_sub', 'مجموع المسدد فعلياً خلال هذا الشهر')}
                    icon={CheckCircle2}
                    colored
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.payroll.total_remaining', 'المتبقي للصرف')}
                    amount={totalRemaining}
                    scope="period"
                    subtitle={t('finance.payroll.remaining_sub', 'مستحقات معلقة لم تصرف بعد')}
                    icon={Clock}
                    colored
                    isLoading={isLoading}
                />
            </div>

            {/* Filter Bar */}
            <FilterBar
                searchValue={search}
                onSearchChange={updateSearch}
                searchPlaceholder={t('finance.payroll.search_placeholder', 'البحث باسم الموظف...')}
                filters={[]}
                activeFilters={{}}
                onFilterChange={() => {}}
                onClearFilters={() => updateSearch('')}
            />

            {/* Data Table */}
            <DataTable
                columns={columns}
                data={employees}
                keyField="id"
                isLoading={isLoading}
                isError={isError}
                onRetry={refetch}
                renderMobileCard={renderMobileCard}
                emptyMessage={t('finance.payroll.no_employees', 'لا يوجد موظفون مسجلون في كشف المرتبات')}
            />

            {/* Salary Payment Drawer */}
            <SalaryPaymentDrawer
                employee={selectedEmployeeForPayment}
                month={month}
                isOpen={Boolean(selectedEmployeeForPayment)}
                onClose={() => setSelectedEmployeeForPayment(null)}
                onSave={async (paymentData) => {
                    await recordPayment(paymentData);
                    setSelectedEmployeeForPayment(null);
                }}
                isSaving={isRecording}
            />

            {/* Staff Rules Drawer */}
            <StaffSettingsDrawer
                employee={selectedEmployeeForRules}
                isOpen={Boolean(selectedEmployeeForRules)}
                onClose={() => setSelectedEmployeeForRules(null)}
                onSave={async (ruleData) => {
                    await updateStaffRules(ruleData);
                    setSelectedEmployeeForRules(null);
                }}
                isSaving={isUpdatingRules}
            />
        </div>
    );
}
