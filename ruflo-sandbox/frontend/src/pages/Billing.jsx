import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, LayoutDashboard, Receipt, Briefcase, TrendingDown, Home } from 'lucide-react';
import DoctorRevenue from '@/features/billing/DoctorRevenue';
import { getFinancialStats, getAllPayments, getExpenses, createExpense, deleteExpense, getStaffRevenue, updateStaffCompensation, getComprehensiveStats, getSalariesStatus, recordSalaryPayment, deleteSalaryPayment, updateHireDate, getLabOrders } from '@/api';
import { getTodayStr } from '@/utils/toothUtils';
import { Card, Button, DataTable, SkeletonBox, PageHeader, TabGroup, toast } from '@/shared/ui';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
// Import extracted components
import ExpensesTab from '@/features/billing/BillingTabs/ExpensesTab';
import ExpenseModal from '@/features/billing/BillingTabs/ExpenseModal';
import StaffTab from '@/features/billing/BillingTabs/StaffTab';
import StaffModal from '@/features/billing/BillingTabs/StaffModal';
import SalariesTab from '@/features/billing/BillingTabs/SalariesTab';
import PaymentsTab from '@/features/billing/BillingTabs/PaymentsTab';
import SummaryTab from '@/features/billing/BillingTabs/SummaryTab';
import { useTranslation } from 'react-i18next';
export default function Billing() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState('doctors');
    const [expensesSubTab, setExpensesSubTab] = useState('expenses'); // 'expenses' or 'salaries'
    // Expense Modal
    const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
    const [newExpense, setNewExpense] = useState({ item_name: '', cost: '', category: 'General', date: getTodayStr(), notes: '' });
    // Staff Profile Modal
    const [staffModalOpen, setStaffModalOpen] = useState(false);
    const [selectedStaff, setSelectedStaff] = useState(null);
    const [editStaffSalary, setEditStaffSalary] = useState(0);
    const [editStaffPerAppointment, setEditStaffPerAppointment] = useState(0);
    const [savingStaff, setSavingStaff] = useState(false);
    // Date range: 1 month from today by default
    const today = new Date();
    const oneMonthAgo = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate()).toISOString().split('T')[0];
    const [startDate, setStartDate] = useState(oneMonthAgo);
    const [endDate, setEndDate] = useState(today.toISOString().split('T')[0]);
    // Salaries state
    const [salaryMonth, setSalaryMonth] = useState(today.toISOString().slice(0, 7));
    const [salariesData, setSalariesData] = useState([]);
    const [salariesLoading, setSalariesLoading] = useState(false);
    const { data, isLoading: loading } = useQuery({
        queryKey: ['billing_data', startDate, endDate],
        queryFn: async () => {
            const [sRes, pRes, eRes, labRes, staffRes, compRes] = await Promise.all([
                getFinancialStats(),
                getAllPayments(),
                getExpenses(),
                getLabOrders(),
                getStaffRevenue(startDate, endDate),
                getComprehensiveStats(startDate, endDate)
            ]);
            
            const manualExpenses = eRes.data.map(e => ({ ...e, type: 'manual' }));
            const labExpenses = (labRes.data || []).map(order => ({
                id: `lab-${order.id}`,
                original_id: order.id,
                item_name: `معمل: ${order.work_type} (${order.patient_name}) - ${order.laboratory_name}`,
                category: 'Laboratory',
                date: order.order_date,
                cost: order.cost,
                type: 'lab_order'
            }));

            return {
                stats: sRes.data,
                payments: pRes.data,
                expenses: [...manualExpenses, ...labExpenses].sort((a, b) => new Date(b.date) - new Date(a.date)),
                staff: staffRes.data.staff || [],
                comprehensiveStats: compRes.data
            };
        }
    });

    const stats = data?.stats;
    const payments = data?.payments || [];
    const expenses = data?.expenses || [];
    const staff = data?.staff || [];
    const comprehensiveStats = data?.comprehensiveStats;
    const handleCreateExpense = async () => {
        if (!newExpense.item_name || !newExpense.cost) return toast.error(t('billing.alerts.enter_item_cost'));
        try {
            await createExpense({ ...newExpense, cost: parseFloat(newExpense.cost) });
            setIsExpenseModalOpen(false);
            setNewExpense({ item_name: '', cost: '', category: 'General', date: getTodayStr(), notes: '' });
            toast.success(t('billing.alerts.expense_add_success'));
            queryClient.invalidateQueries(['billing_data']);
        } catch (err) {
            toast.error(t('billing.alerts.expense_add_fail'));
        }
    };
    const handleDeleteExpense = async (id) => {
        if (String(id).startsWith('lab-')) {
            return toast.error(t('billing.alerts.lab_delete_error'));
        }
        if (!confirm(t('billing.alerts.delete_expense_confirm'))) return;
        try {
            await deleteExpense(id);
            toast.success(t('billing.alerts.expense_delete_success'));
            queryClient.invalidateQueries(['billing_data']);
        } catch (err) {
            console.error(err);
            toast.error(t('billing.alerts.delete_error'));
        }
    };
    const openStaffProfile = (staffMember) => {
        setSelectedStaff(staffMember);
        setEditStaffSalary(staffMember.fixed_salary || 0);
        setEditStaffPerAppointment(staffMember.per_appointment_fee || 0);
        setStaffModalOpen(true);
    };
    const saveStaffCompensation = async () => {
        if (!selectedStaff) return;
        setSavingStaff(true);
        try {
            await updateStaffCompensation(selectedStaff.id, 0, editStaffSalary, editStaffPerAppointment);
            queryClient.invalidateQueries(['billing_data']);
            setStaffModalOpen(false);
            toast.success(t('billing.alerts.save_success'));
        } catch (err) {
            console.error(err);
            toast.error(t('billing.alerts.save_fail'));
        } finally {
            setSavingStaff(false);
        }
    };
    const loadSalaries = async () => {
        setSalariesLoading(true);
        try {
            const res = await getSalariesStatus(salaryMonth);
            setSalariesData(res.data.employees || []);
        } catch (err) {
            console.error(err);
            toast.error(t('billing.alerts.salaries_load_fail'));
        } finally {
            setSalariesLoading(false);
        }
    };
    const handlePaySalary = async (employee, isPartial = false) => {
        const amount = isPartial ? employee.prorated_salary : employee.base_salary;
        if (!confirm(`${t('billing.alerts.pay_confirm_prefix')} ${amount} ${t('billing.alerts.pay_confirm_suffix')} ${employee.username}?`)) return;
        try {
            await recordSalaryPayment(employee.id, salaryMonth, amount, isPartial, isPartial ? employee.days_worked : null, null);
            toast.success(t('billing.alerts.pay_success'));
            loadSalaries();
        } catch (err) {
            console.error(err);
            toast.error(err.response?.data?.error || t('billing.alerts.pay_fail'));
        }
    };
    const updateEmployeeHireDate = async (userId, date) => {
        try {
            await updateHireDate(userId, date); // Use the imported function directly
            toast.success(t('billing.alerts.hire_date_success'));
            loadSalaries();
        } catch (err) {
            console.error(err);
            toast.error(t('billing.alerts.hire_date_fail'));
        }
    };
    // UseEffect for salary month change
    useEffect(() => {
        if (activeTab === 'expenses' && expensesSubTab === 'salaries') {
            loadSalaries();
        }
    }, [activeTab, expensesSubTab, salaryMonth]);
    if (loading) return (
        <div className="space-y-6">
            <div className="flex gap-4">
                <SkeletonBox className="h-10 w-32" />
                <SkeletonBox className="h-10 w-32" />
            </div>
            <SkeletonBox className="h-[400px] w-full rounded-2xl" />
        </div>
    );
    const tabs = [
        { id: 'doctors', label: t('billing.tabs.doctors'), icon: Users },
        { id: 'staff', label: t('billing.tabs.staff'), icon: Briefcase },
        //{ id: 'salaries', label: 'المرتبات', icon: CreditCard }, // Merged into expenses
        { id: 'expenses', label: t('billing.tabs.expenses'), icon: TrendingDown },
        { id: 'summary', label: t('billing.tabs.summary'), icon: LayoutDashboard },
        { id: 'payments', label: t('billing.tabs.payments'), icon: Receipt },
    ];
    const roleLabels = {
        assistant: t('billing.roles.assistant'),
        receptionist: t('billing.roles.receptionist'),
        accountant: t('billing.roles.accountant'),
        nurse: t('billing.roles.nurse')
    };
    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <PageHeader
                title={t('billing.title')}
                subtitle={t('billing.subtitle')}
                breadcrumbs={[
                    { label: t('nav.home', 'Home'), icon: Home, path: '/' },
                    { label: t('billing.title') }
                ]}
            />
            <TabGroup
                variant="pill"
                tabs={tabs}
                activeTab={activeTab}
                onChange={setActiveTab}
            />
            {/* Tab Content */}
            {activeTab === 'doctors' && <DoctorRevenue />}
            {activeTab === 'staff' && (
                <StaffTab
                    staff={staff}
                    roleLabels={roleLabels}
                    openStaffProfile={openStaffProfile}
                />
            )}
            {activeTab === 'expenses' && (
                <div className="space-y-4">
                    <TabGroup
                        variant="underline"
                        tabs={[
                            { id: 'expenses', label: t('billing.subtabs.general_expenses') },
                            { id: 'salaries', label: t('billing.subtabs.salaries') }
                        ]}
                        activeTab={expensesSubTab}
                        onChange={setExpensesSubTab}
                        className="mb-4"
                    />
                    {expensesSubTab === 'expenses' ? (
                        <ExpensesTab
                            expenses={expenses}
                            stats={stats}
                            setIsExpenseModalOpen={setIsExpenseModalOpen}
                            handleDeleteExpense={handleDeleteExpense}
                        />
                    ) : (
                        <SalariesTab
                            salaryMonth={salaryMonth}
                            setSalaryMonth={setSalaryMonth}
                            salariesData={salariesData}
                            salariesLoading={salariesLoading}
                            updateEmployeeHireDate={updateEmployeeHireDate}
                            roleLabels={roleLabels}
                            handlePaySalary={handlePaySalary}
                            deleteSalaryPayment={deleteSalaryPayment}
                            loadSalaries={loadSalaries}
                        />
                    )}
                </div>
            )}
            {activeTab === 'summary' && (
                <SummaryTab
                    startDate={startDate}
                    setStartDate={setStartDate}
                    endDate={endDate}
                    setEndDate={setEndDate}
                    comprehensiveStats={comprehensiveStats}
                    loading={loading}
                />
            )}
            {activeTab === 'payments' && (
                <PaymentsTab
                    payments={payments}
                    navigate={navigate}
                />
            )}
            {/* Modals */}
            <ExpenseModal
                isOpen={isExpenseModalOpen}
                onClose={() => setIsExpenseModalOpen(false)}
                newExpense={newExpense}
                setNewExpense={setNewExpense}
                handleCreateExpense={handleCreateExpense}
            />
            <StaffModal
                isOpen={staffModalOpen}
                onClose={() => setStaffModalOpen(false)}
                selectedStaff={selectedStaff}
                roleLabels={roleLabels}
                editStaffSalary={editStaffSalary}
                setEditStaffSalary={setEditStaffSalary}
                editStaffPerAppointment={editStaffPerAppointment}
                setEditStaffPerAppointment={setEditStaffPerAppointment}
                saveStaffCompensation={saveStaffCompensation}
                savingStaff={savingStaff}
            />
        </div>
    );
}

