import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, Link } from 'react-router-dom';
import {
    ArrowLeft,
    ArrowRight,
    Stethoscope,
    Calendar,
    Settings,
    FileSpreadsheet,
    FlaskConical,
    Activity,
} from 'lucide-react';
import { useDoctorDetails } from '../compensation/hooks/useDoctorDetails';
import { useFinancePermissions } from '../useFinancePermissions';
import DateRangePicker from '../components/DateRangePicker';
import DataTable from '../components/DataTable';
import Money from '../components/Money';
import DoctorCompensationEquation from '../compensation/components/DoctorCompensationEquation';
import DoctorSettingsDrawer from '../compensation/components/DoctorSettingsDrawer';

/**
 * Routed Doctor Finance Detail Page (§22 MASTER_SPEC).
 * Displays full treatment/lab breakdown, case timeline, and entitlement formula.
 */
export default function DoctorDetailPage() {
    const { doctorId } = useParams();
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const { canConfigFinance } = useFinancePermissions();

    const {
        data,
        from,
        to,
        isLoading,
        isError,
        refetch,
        updateDateRange,
        updateCompensation,
        isUpdating,
    } = useDoctorDetails(doctorId);

    const [activeTab, setActiveTab] = useState('treatments');
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    const treatments = data?.treatments || [];
    const labOrders = data?.lab_orders || [];

    // Treatment Columns
    const treatmentColumns = [
        {
            id: 'patient_name',
            header: t('patients.patient_name', 'المريض'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <span className="font-bold text-text-primary block">{row.patient_name}</span>
                    <span className="text-[11px] text-text-secondary">{row.procedure || '—'}</span>
                </div>
            ),
        },
        {
            id: 'date',
            header: t('finance.expenses.date', 'التاريخ'),
            sortable: false,
            width: '130px',
            cell: (row) => (
                <span className="font-mono text-xs text-text-secondary">
                    {row.date ? new Date(row.date).toLocaleDateString('ar-EG') : '—'}
                </span>
            ),
        },
        {
            id: 'cost',
            header: t('finance.metrics.invoiced', 'القيمة'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.cost} size="sm" />
            ),
        },
        {
            id: 'discount',
            header: t('finance.metrics.discount', 'الخصم'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.discount} size="sm" colored />
            ),
        },
        {
            id: 'net',
            header: t('finance.metrics.net_invoiced', 'الصافي'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.net} size="sm" />
            ),
        },
    ];

    // Lab Order Columns
    const labColumns = [
        {
            id: 'patient_name',
            header: t('patients.patient_name', 'المريض'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <span className="font-bold text-text-primary block">{row.patient_name}</span>
                    <span className="text-[11px] text-text-secondary">{row.work_type || '—'}</span>
                </div>
            ),
        },
        {
            id: 'date',
            header: t('finance.expenses.date', 'التاريخ'),
            sortable: false,
            width: '130px',
            cell: (row) => (
                <span className="font-mono text-xs text-text-secondary">
                    {row.date ? new Date(row.date).toLocaleDateString('ar-EG') : '—'}
                </span>
            ),
        },
        {
            id: 'cost',
            header: t('finance.expenses.lab_total', 'تكلفة المعمل'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.cost} size="sm" colored />
            ),
        },
    ];

    return (
        <div className="space-y-6">
            {/* Navigation Header */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <Link
                        to={`/finance/compensation?from=${from}&to=${to}`}
                        className="p-2 rounded-xl bg-card border border-border text-text-secondary hover:text-text-primary hover:bg-muted/60 transition-colors"
                        aria-label={t('common.back', 'رجوع')}
                    >
                        {isRtl ? <ArrowRight className="w-5 h-5" /> : <ArrowLeft className="w-5 h-5" />}
                    </Link>
                    <div>
                        <h2 className="text-xl font-black text-text-primary flex items-center gap-2">
                            <Stethoscope className="w-5 h-5 text-primary" />
                            <span>{data?.doctor_name || t('finance.compensation.doctor_details', 'تفاصيل حساب الطبيب')}</span>
                        </h2>
                        <p className="text-xs text-text-secondary">
                            {t('finance.compensation.doctor_details_sub', 'كشف حساب الحالات العلاجية ومطالبات المعامل')}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <DateRangePicker
                        value={{ from, to }}
                        onChange={updateDateRange}
                    />

                    {canConfigFinance && (
                        <button
                            type="button"
                            onClick={() => setIsSettingsOpen(true)}
                            className="p-2.5 rounded-xl bg-card border border-border text-text-secondary hover:text-primary hover:bg-primary/5 transition-colors"
                            title={t('finance.compensation.edit_rules', 'تعديل القواعد')}
                        >
                            <Settings className="w-4 h-4" />
                        </button>
                    )}
                </div>
            </div>

            {/* Compensation Visual Equation */}
            <DoctorCompensationEquation
                collected={data?.collected || 0}
                labCost={data?.lab_cost || 0}
                commissionPercent={data?.commission_percent || 0}
                fixedSalary={data?.fixed_salary || 0}
                totalDue={data?.total_due || 0}
            />

            {/* Tabs & Case Drill-down Table */}
            <div className="space-y-4">
                <div className="flex items-center gap-2 border-b border-border pb-1">
                    <button
                        type="button"
                        onClick={() => setActiveTab('treatments')}
                        className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-xl transition-all ${
                            activeTab === 'treatments'
                                ? 'bg-primary text-white shadow-sm'
                                : 'text-text-secondary hover:text-text-primary hover:bg-muted/40'
                        }`}
                    >
                        <FileSpreadsheet className="w-4 h-4" />
                        <span>{t('appointments.treatments_count', 'الحالات العلاجية المنفذة')} ({treatments.length})</span>
                    </button>

                    <button
                        type="button"
                        onClick={() => setActiveTab('labs')}
                        className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-xl transition-all ${
                            activeTab === 'labs'
                                ? 'bg-primary text-white shadow-sm'
                                : 'text-text-secondary hover:text-text-primary hover:bg-muted/40'
                        }`}
                    >
                        <FlaskConical className="w-4 h-4" />
                        <span>{t('finance.expenses.lab_total', 'مطالبات المعامل')} ({labOrders.length})</span>
                    </button>
                </div>

                {activeTab === 'treatments' ? (
                    <DataTable
                        columns={treatmentColumns}
                        data={treatments}
                        keyField="id"
                        isLoading={isLoading}
                        isError={isError}
                        onRetry={refetch}
                        emptyMessage={t('appointments.no_treatments_period', 'لا توجد علاجات منفذة لهذا الطبيب في هذه الفترة')}
                    />
                ) : (
                    <DataTable
                        columns={labColumns}
                        data={labOrders}
                        keyField="id"
                        isLoading={isLoading}
                        isError={isError}
                        onRetry={refetch}
                        emptyMessage={t('finance.expenses.no_labs_period', 'لا توجد طلبات معامل مسجلة لهذا الطبيب في هذه الفترة')}
                    />
                )}
            </div>

            {/* Doctor Settings Drawer */}
            <DoctorSettingsDrawer
                doctor={data ? { doctor_id: doctorId, doctor_name: data.doctor_name, commission_percent: data.commission_percent, fixed_salary: data.fixed_salary } : null}
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                onSave={async (formData) => {
                    await updateCompensation(formData);
                    setIsSettingsOpen(false);
                }}
                isSaving={isUpdating}
            />
        </div>
    );
}
