import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, LayoutDashboard, Receipt, Briefcase, TrendingDown } from 'lucide-react';
import toast from 'react-hot-toast';
import DoctorRevenue from '@/features/billing/DoctorRevenue';
import { getFinancialStats, getAllPayments, getExpenses, createExpense, deleteExpense, getStaffRevenue, updateStaffCompensation, getComprehensiveStats, getSalariesStatus, recordSalaryPayment, deleteSalaryPayment, updateHireDate, getLabOrders } from '@/api';
import { getTodayStr } from '@/utils/toothUtils';
import { Card, Button, DataTable, SkeletonBox } from '@/shared/ui';
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
    const [stats, setStats] = useState(null);
    const [payments, setPayments] = useState([]);
    const [expenses, setExpenses] = useState([]);
    const [staff, setStaff] = useState([]);
    const [comprehensiveStats, setComprehensiveStats] = useState(null);
    const [loading, setLoading] = useState(true);
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
    useEffect(() => {
        loadData();
    }, []);
    const loadData = async () => {
        try {
            const [sRes, pRes, eRes, labRes, staffRes, compRes] = await Promise.all([
                getFinancialStats(),
                getAllPayments(),
                getExpenses(),
                getLabOrders(),
                getStaffRevenue(startDate, endDate),
                getComprehensiveStats(startDate, endDate)
            ]);
            setStats(sRes.data);
            setPayments(pRes.data);
            // Merge Expenses and Lab Orders
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
            setExpenses([...manualExpenses, ...labExpenses].sort((a, b) => new Date(b.date) - new Date(a.date)));
            setStaff(staffRes.data.staff || []);
            setComprehensiveStats(compRes.data);
        } catch (err) {
            console.error(err);
            toast.error(t('billing.alerts.load_fail'));
        } finally {
            setLoading(false);
        }
    };
    const handleCreateExpense = async () => {
        if (!newExpense.item_name || !newExpense.cost) return toast.error(t('billing.alerts.enter_item_cost'));
        try {
            await createExpense({ ...newExpense, cost: parseFloat(newExpense.cost) });
            setIsExpenseModalOpen(false);
            setNewExpense({ item_name: '', cost: '', category: 'General', date: getTodayStr(), notes: '' });
            toast.success(t('billing.alerts.expense_add_success'));
            loadData();
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
            loadData();
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
            // Update local state
            setStaff(prev => prev.map(s =>
                s.id === selectedStaff.id
                    ? { ...s, fixed_salary: editStaffSalary, per_appointment_fee: editStaffPerAppointment }
                    : s
            ));
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
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
                <div>
                    <h2 className="text-3xl font-black text-text-primary tracking-tight">{t('billing.title')}</h2>
                    <p className="text-text-secondary mt-1 text-lg font-medium">{t('billing.subtitle')}</p>
                </div>
            </div>
            {/* Tabs */}
            <div className="flex flex-wrap gap-2 p-1.5 bg-surface rounded-2xl w-fit border border-border">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm transition-all ${activeTab === tab.id
                            ? 'bg-background text-primary shadow-sm'
                            : 'text-text-secondary hover:text-text-primary'
                            }`}
                    >
                        <tab.icon size={16} />
                        {tab.label}
                    </button>
                ))}
            </div>
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
                    {/* Sub Tabs */}
                    <div className="flex gap-2 p-1 bg-surface rounded-lg w-fit border border-border">
                        <Button
                            variant={expensesSubTab === 'expenses' ? 'default' : 'ghost'}
                            size="sm"
                            onClick={() => setExpensesSubTab('expenses')}
                        >
                            {t('billing.subtabs.general_expenses')}
                        </Button>
                        <Button
                            variant={expensesSubTab === 'salaries' ? 'default' : 'ghost'}
                            size="sm"
                            onClick={() => setExpensesSubTab('salaries')}
                        >
                            {t('billing.subtabs.salaries')}
                        </Button>
                    </div>
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
                    getComprehensiveStats={getComprehensiveStats}
                    setComprehensiveStats={setComprehensiveStats}
                    setLoading={setLoading}
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

