import { useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
    Users,
    AlertTriangle,
    Eye,
    Plus,
} from 'lucide-react';
import { usePatientAccounts } from '../patient-accounts/hooks/usePatientAccounts';
import { useFinancePermissions } from '../useFinancePermissions';
import MetricCard from '../components/MetricCard';
import FilterBar from '../components/FilterBar';
import DataTable from '../components/DataTable';
import Money from '../components/Money';
import PatientStatementDrawer from '../patient-accounts/components/PatientStatementDrawer';
import RecordPaymentModal from '../payments/components/RecordPaymentModal';

/**
 * Patient Accounts & Receivables Page (§11 MASTER_SPEC).
 * The patientId route segment owns statement state so refresh/back/deep links
 * reproduce the same patient account instead of relying on transient React state.
 */
export default function PatientAccountsPage() {
    const { t } = useTranslation();
    const { patientId: routePatientId } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    const { canWriteFinance } = useFinancePermissions();

    const {
        items,
        totalCount,
        allTimeOutstanding,
        search,
        from,
        to,
        outstandingOnly,
        currentPage,
        pageSize,
        isLoading,
        isError,
        refetch,
        updateSearch,
        updateFilter,
        setPage,
        createPayment,
        isCreating,
    } = usePatientAccounts(20);

    const [selectedPatient, setSelectedPatient] = useState(null);
    const [recordPaymentForPatient, setRecordPaymentForPatient] = useState(null);
    const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);

    const baseRoute = '/finance/patient-accounts';
    const openStatement = (patient) => {
        if (!patient?.patient_id) return;
        setSelectedPatient(patient);
        navigate(
            {
                pathname: `${baseRoute}/${patient.patient_id}`,
                search: location.search,
            },
            { state: { financeStatementFromList: true } },
        );
    };

    const closeStatement = () => {
        setSelectedPatient(null);
        if (location.state?.financeStatementFromList) {
            navigate(-1);
            return;
        }
        navigate(
            { pathname: baseRoute, search: location.search },
            { replace: true },
        );
    };

    const openPaymentFromStatement = (patient) => {
        setSelectedPatient(null);
        setRecordPaymentForPatient(patient);
        setIsRecordModalOpen(true);
        navigate(
            { pathname: baseRoute, search: location.search },
            { replace: true },
        );
    };

    const columns = [
        {
            id: 'file_number',
            header: t('patients.file_number', 'رقم الملف'),
            sortable: false,
            width: '100px',
            cell: (row) => (
                <span className="font-mono font-bold text-text-primary">
                    #{row.file_number || row.patient_id}
                </span>
            ),
        },
        {
            id: 'patient_name',
            header: t('patients.patient_name', 'اسم المريض'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <button
                        type="button"
                        onClick={() => openStatement(row)}
                        className="block text-start font-bold text-text-primary transition-colors hover:text-primary"
                    >
                        {row.patient_name}
                    </button>
                    {row.patient_phone && (
                        <span className="font-mono text-[11px] text-text-secondary" dir="ltr">
                            {row.patient_phone}
                        </span>
                    )}
                </div>
            ),
        },
        {
            id: 'total_invoiced',
            header: t('finance.metrics.invoiced', 'المحتسب'),
            align: 'end',
            sortable: false,
            cell: (row) => <Money amount={row.total_invoiced} size="sm" />,
        },
        {
            id: 'total_paid',
            header: t('finance.metrics.collected', 'المسدد'),
            align: 'end',
            sortable: false,
            cell: (row) => <Money amount={row.total_paid} colored size="sm" />,
        },
        {
            id: 'all_time_outstanding',
            header: t('finance.receivables.total_debt', 'المديونية القائمة'),
            align: 'end',
            sortable: false,
            cell: (row) => <Money amount={row.all_time_outstanding} colored size="sm" />,
        },
        {
            id: 'actions',
            header: t('common.actions', 'إجراءات'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <div className="flex items-center justify-end gap-1.5">
                    <button
                        type="button"
                        onClick={() => openStatement(row)}
                        className="rounded-lg p-1.5 text-text-secondary transition-colors hover:bg-primary/10 hover:text-primary"
                        title={t('finance.receivables.view_statement', 'عرض كشف الحساب')}
                    >
                        <Eye className="h-4 w-4" />
                    </button>
                    {canWriteFinance && row.all_time_outstanding > 0 && (
                        <button
                            type="button"
                            onClick={() => {
                                setRecordPaymentForPatient(row);
                                setIsRecordModalOpen(true);
                            }}
                            className="rounded-lg p-1.5 text-text-secondary transition-colors hover:bg-emerald-500/10 hover:text-emerald-600"
                            title={t('finance.payments.record_btn', 'تسجيل دفعة')}
                        >
                            <Plus className="h-4 w-4" />
                        </button>
                    )}
                </div>
            ),
        },
    ];

    const renderMobileCard = (row) => (
        <div
            key={row.patient_id}
            onClick={() => openStatement(row)}
            className="cursor-pointer space-y-3 rounded-xl border border-border bg-card p-4 shadow-xs transition-all hover:border-primary/30"
        >
            <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                    <span className="font-mono text-xs font-bold text-text-secondary">
                        #{row.file_number || row.patient_id}
                    </span>
                    <p className="text-sm font-bold text-text-primary">{row.patient_name}</p>
                </div>
                <div className="text-end">
                    <span className="block text-[10px] font-semibold text-text-secondary">
                        {t('finance.receivables.total_debt', 'المديونية')}
                    </span>
                    <Money amount={row.all_time_outstanding} colored size="sm" />
                </div>
            </div>

            <div className="grid grid-cols-2 gap-2 border-t border-border/50 pt-2 text-xs">
                <div>
                    <span className="text-text-secondary">{t('finance.metrics.invoiced', 'المحتسب')}: </span>
                    <Money amount={row.total_invoiced} size="xs" />
                </div>
                <div className="text-end">
                    <span className="text-text-secondary">{t('finance.metrics.collected', 'المسدد')}: </span>
                    <Money amount={row.total_paid} colored size="xs" />
                </div>
            </div>
        </div>
    );

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <MetricCard
                    title={t('finance.obligations.patient_debt', 'إجمالي الديون التراكمية على المرضى')}
                    amount={allTimeOutstanding}
                    scope="all_time"
                    subtitle={t('finance.receivables.total_clinic_debt_sub', 'مجموع الذمم غير المسددة لجميع المرضى عبر العيادة')}
                    icon={AlertTriangle}
                    colored
                    isLoading={isLoading}
                />
                <MetricCard
                    title={t('finance.receivables.active_accounts_count', 'إجمالي حسابات المرضى المالية')}
                    amount={totalCount}
                    isCurrency={false}
                    scope="all_time"
                    subtitle={t('finance.receivables.active_accounts_sub', 'المرضى الذين يمتلكون سجلات علاجية أو دفعات')}
                    icon={Users}
                    isLoading={isLoading}
                />
            </div>

            <div className="space-y-3">
                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={() => updateFilter('all')}
                        className={`rounded-xl px-4 py-2 text-xs font-bold transition-all ${
                            !outstandingOnly
                                ? 'bg-primary text-white shadow-sm'
                                : 'border border-border bg-card text-text-secondary hover:text-text-primary'
                        }`}
                    >
                        {t('finance.receivables.filter_all', 'جميع الحسابات')}
                    </button>
                    <button
                        type="button"
                        onClick={() => updateFilter('debtors')}
                        className={`flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-bold transition-all ${
                            outstandingOnly
                                ? 'bg-amber-600 text-white shadow-sm'
                                : 'border border-border bg-card text-text-secondary hover:text-text-primary'
                        }`}
                    >
                        <AlertTriangle className="h-3.5 w-3.5" />
                        <span>{t('finance.receivables.filter_debtors', 'المدينون فقط')}</span>
                    </button>
                </div>

                <FilterBar
                    searchValue={search}
                    onSearchChange={updateSearch}
                    searchPlaceholder={t('finance.receivables.search_placeholder', 'البحث برقم الملف، اسم المريض، أو رقم الهاتف...')}
                    filters={[]}
                    activeFilters={{}}
                    onFilterChange={() => {}}
                    onClearFilters={() => {
                        updateSearch('');
                        updateFilter('all');
                    }}
                />
            </div>

            <DataTable
                columns={columns}
                data={items}
                keyField="patient_id"
                isLoading={isLoading}
                isError={isError}
                onRetry={refetch}
                renderMobileCard={renderMobileCard}
                emptyMessage={
                    outstandingOnly
                        ? t('finance.receivables.no_debtors', 'لا يوجد مرضى عليهم مديونيات قائمة')
                        : t('finance.receivables.no_accounts', 'لا توجد حسابات مرضى مسجلة')
                }
                page={currentPage}
                pageSize={pageSize}
                totalItems={totalCount}
                onPageChange={setPage}
            />

            <PatientStatementDrawer
                patient={selectedPatient}
                patientId={routePatientId}
                from={from}
                to={to}
                isOpen={Boolean(routePatientId)}
                onClose={closeStatement}
                onRecordPayment={openPaymentFromStatement}
            />

            <RecordPaymentModal
                isOpen={isRecordModalOpen}
                initialPatientId={recordPaymentForPatient?.patient_id || recordPaymentForPatient?.id || ''}
                onClose={() => {
                    setIsRecordModalOpen(false);
                    setRecordPaymentForPatient(null);
                }}
                onSubmit={createPayment}
                isSubmitting={isCreating}
            />
        </div>
    );
}
