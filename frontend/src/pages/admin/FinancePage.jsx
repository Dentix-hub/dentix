import { useEffect, useState, useCallback } from 'react';
import logger from '@/utils/logger';
import { useTranslation } from 'react-i18next';
import {
    api,
    deleteSubscriptionPayment,
    getSubscriptionPayments,
    getSubscriptionPlans,
    recordSubscriptionPayment,
    updateSubscriptionPlan,
} from '@/api';
import PaymentsManager from '@/features/admin/SuperAdmin/PaymentsManager';
import PlansManager from '@/features/admin/SuperAdmin/PlansManager';
import ActiveSubscriptions from '@/features/admin/SuperAdmin/ActiveSubscriptions';
import FinanceReports from '@/features/admin/SuperAdmin/FinanceReports';
import { CreditCard, PlusCircle, Banknote, Landmark, User, Calendar } from 'lucide-react';
import { DateTimePicker, toast, Modal, ConfirmDialog } from '@/shared/ui';

export default function FinancePage() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    const [activeTab, setActiveTab] = useState('payments'); // payments, subscriptions, plans, reports
    const [payments, setPayments] = useState([]);
    const [tenants, setTenants] = useState([]);
    const [plans, setPlans] = useState([]);
    
    // Payment Modal State
    const [showPaymentModal, setShowPaymentModal] = useState(false);
    const [paymentForm, setPaymentForm] = useState({
        tenant_id: '',
        plan_id: '',
        amount: '',
        payment_method: 'cash',
        paid_by: '',
        payment_date: new Date().toISOString().split('T')[0],
        notes: ''
    });
    const [tenantUsers, setTenantUsers] = useState([]);
    
    // Delete payment state
    const [paymentToDelete, setPaymentToDelete] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);

    // Plans Editing State
    const [editingPlan, setEditingPlan] = useState(null);
    const [editedPlanData, setEditedPlanData] = useState({});
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState(false);

    const fetchData = useCallback(async () => {
        setLoading(true);
        const [paymentsResult, tenantsResult, plansResult] = await Promise.allSettled([
            getSubscriptionPayments(),
            api.get('/api/v1/admin/tenants'),
            getSubscriptionPlans(),
        ]);

        if (paymentsResult.status === 'fulfilled') {
            setPayments(Array.isArray(paymentsResult.value?.data?.data) 
                ? paymentsResult.value.data.data 
                : (Array.isArray(paymentsResult.value?.data) ? paymentsResult.value.data : []));
        } else {
            logger.error('Failed to load subscription payments:', paymentsResult.reason);
        }

        if (tenantsResult.status === 'fulfilled') {
            setTenants(Array.isArray(tenantsResult.value?.data?.data) 
                ? tenantsResult.value.data.data 
                : (Array.isArray(tenantsResult.value?.data) ? tenantsResult.value.data : []));
        } else {
            logger.error('Failed to load tenants:', tenantsResult.reason);
        }

        if (plansResult.status === 'fulfilled') {
            setPlans(Array.isArray(plansResult.value?.data?.data) 
                ? plansResult.value.data.data 
                : (Array.isArray(plansResult.value?.data) ? plansResult.value.data : []));
        } else {
            logger.error('Failed to load subscription plans:', plansResult.reason);
        }

        setLoading(false);
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleSavePlan = async (planId) => {
        try {
            await updateSubscriptionPlan(planId, editedPlanData);
            setEditingPlan(null);
            setEditedPlanData({});
            fetchData();
            toast.success(t('super_admin.plans.save_success') || 'تم حفظ الخطة بنجاح');
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || t('super_admin.plans.error_saving') || 'فشل التعديل';
            toast.error(errorMsg);
        }
    };

    const handleClinicChange = async (tenantId) => {
        setPaymentForm(prev => ({ ...prev, tenant_id: tenantId, paid_by: '' }));
        if (!tenantId) {
            setTenantUsers([]);
            return;
        }
        try {
            const res = await api.get(`/api/v1/admin/system/tenants/${tenantId}/users`);
            const users = res?.data?.users || res?.data?.data?.users || res?.data || [];
            setTenantUsers(Array.isArray(users) ? users : []);
        } catch (err) {
            logger.error('Failed to fetch tenant users:', err);
            setTenantUsers([]);
        }
    };

    const handleRecordPayment = async (e) => {
        if (e && typeof e.preventDefault === 'function') {
            e.preventDefault();
        }
        if (processing) return;

        if (!paymentForm.tenant_id) {
            toast.error(t('super_admin.payments.error_select_tenant') || 'الرجاء اختيار العيادة');
            return;
        }
        if (!paymentForm.plan_id) {
            toast.error(t('super_admin.payments.error_select_plan') || 'الرجاء اختيار الخطة');
            return;
        }

        const amountNum = Number(paymentForm.amount);
        if (isNaN(amountNum) || !isFinite(amountNum) || amountNum <= 0) {
            toast.error(t('super_admin.payments.error_invalid_amount') || 'الرجاء إدخال مبلغ صحيح أكبر من الصفر');
            return;
        }

        if (!paymentForm.payment_date || isNaN(new Date(paymentForm.payment_date).getTime())) {
            toast.error(t('super_admin.payments.error_invalid_date') || 'الرجاء تحديد تاريخ دفع صحيح');
            return;
        }

        setProcessing(true);
        try {
            const payload = {
                ...paymentForm,
                tenant_id: parseInt(paymentForm.tenant_id, 10),
                plan_id: parseInt(paymentForm.plan_id, 10),
                amount: amountNum,
            };
            await recordSubscriptionPayment(payload);
            setShowPaymentModal(false);
            setPaymentForm({
                tenant_id: '',
                plan_id: '',
                amount: '',
                payment_method: 'cash',
                paid_by: '',
                payment_date: new Date().toISOString().split('T')[0],
                notes: ''
            });
            fetchData();
            toast.success(t('super_admin.payments.success_recorded') || 'تم تسجيل الدفعة بنجاح');
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.response?.data?.message || err.message || t('super_admin.payments.error_recording') || 'فشل تسجيل الدفعة';
            toast.error(errorMsg);
        } finally {
            setProcessing(false);
        }
    };

    const handleConfirmDeletePayment = async () => {
        if (!paymentToDelete) return;
        setIsDeleting(true);
        try {
            await deleteSubscriptionPayment(paymentToDelete);
            setPaymentToDelete(null);
            fetchData();
            toast.success(t('super_admin.payments.success_deleted') || 'تم حذف الدفعة بنجاح');
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || t('super_admin.payments.error_deleting') || 'فشل حذف الدفعة';
            toast.error(errorMsg);
        } finally {
            setIsDeleting(false);
        }
    };

    const getDaysRemaining = (endDate) => {
        if (!endDate) return null;
        const days = Math.ceil((new Date(endDate) - new Date()) / (1000 * 60 * 60 * 24));
        return days;
    };

    if (loading) return (
        <div className="p-8 text-center text-slate-500 font-bold animate-pulse">
            {t('super_admin.finance.loading') || 'جاري تحميل البيانات المالية...'}
        </div>
    );

    return (
        <div className="space-y-6 animate-fade-in-up" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-4">
                    <div className="bg-emerald-50 dark:bg-emerald-900/20 p-4 rounded-2xl text-emerald-600 dark:text-emerald-400">
                        <CreditCard size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white">{t('super_admin.finance.title') || 'الإدارة المالية'}</h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">{t('super_admin.finance.subtitle') || 'المدفوعات وخطط الاشتراك'}</p>
                    </div>
                </div>
                <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
                    <button
                        onClick={() => setActiveTab('payments')}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'payments' ? 'bg-white dark:bg-slate-700 shadow text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'}`}
                    >
                        {t('super_admin.finance.tabs.payments') || 'المدفوعات'}
                    </button>
                    <button
                        onClick={() => setActiveTab('subscriptions')}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'subscriptions' ? 'bg-white dark:bg-slate-700 shadow text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'}`}
                    >
                        {t('super_admin.finance.tabs.subscriptions') || 'الاشتراكات'}
                    </button>
                    <button
                        onClick={() => setActiveTab('plans')}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'plans' ? 'bg-white dark:bg-slate-700 shadow text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'}`}
                    >
                        {t('super_admin.finance.tabs.plans') || 'الخطط'}
                    </button>
                    <button
                        onClick={() => setActiveTab('reports')}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'reports' ? 'bg-white dark:bg-slate-700 shadow text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'}`}
                    >
                        {t('super_admin.finance.tabs.reports') || 'التقارير'}
                    </button>
                </div>
                <button
                    onClick={() => {
                        setShowPaymentModal(true);
                        if (plans.length > 0) {
                            setPaymentForm(prev => ({ 
                                ...prev, 
                                plan_id: plans[0].id, 
                                amount: plans[0].price != null ? plans[0].price : '' 
                            }));
                        }
                    }}
                    className="flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold shadow-lg shadow-emerald-500/30 transition-all transform hover:scale-105"
                >
                    <PlusCircle size={20} />
                    {t('super_admin.payments.record_button') || 'تسجيل دفعة'}
                </button>
            </div>

            {activeTab === 'payments' ? (
                <PaymentsManager
                    payments={payments}
                    tenants={tenants}
                    plans={plans}
                    onDelete={(id) => setPaymentToDelete(id)}
                />
            ) : activeTab === 'subscriptions' ? (
                <ActiveSubscriptions
                    tenants={tenants}
                    plans={plans}
                    getDaysRemaining={getDaysRemaining}
                />
            ) : activeTab === 'plans' ? (
                <PlansManager
                    plans={plans}
                    editingPlan={editingPlan}
                    setEditingPlan={setEditingPlan}
                    editedPlanData={editedPlanData}
                    setEditedPlanData={setEditedPlanData}
                    handleSavePlan={handleSavePlan}
                    onRefresh={fetchData}
                />
            ) : (
                <FinanceReports />
            )}

            {/* Accessible Shared Payment Modal */}
            <Modal
                isOpen={showPaymentModal}
                onClose={() => !processing && setShowPaymentModal(false)}
                title={t('super_admin.payments.modal_title') || 'تسجيل دفعة جديدة'}
                maxWidth="max-w-xl"
            >
                <form onSubmit={handleRecordPayment} className="space-y-6" dir={isRtl ? 'rtl' : 'ltr'}>
                    <p className="text-slate-500 dark:text-slate-400 text-sm">
                        {t('super_admin.payments.modal_subtitle') || 'أضف تفاصيل الدفعة المالية للعيادة'}
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Clinic Selection */}
                        <div className="space-y-2">
                            <label htmlFor="payment_tenant_select" className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                                <PlusCircle size={16} /> {t('super_admin.tenants.title') || 'العيادة'}
                            </label>
                            <select
                                id="payment_tenant_select"
                                value={paymentForm.tenant_id}
                                onChange={(e) => handleClinicChange(e.target.value)}
                                className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                            >
                                <option value="">{t('super_admin.payments.select_clinic') || 'اختر العيادة'}</option>
                                {(Array.isArray(tenants) ? tenants : []).map(t => (
                                    <option key={t.id} value={t.id}>{t.name}</option>
                                ))}
                            </select>
                        </div>

                        {/* Plan Selection */}
                        <div className="space-y-2">
                            <label htmlFor="payment_plan_select" className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                                <CreditCard size={16} /> {t('super_admin.tenants.plan') || 'الخطة'}
                            </label>
                            <select
                                id="payment_plan_select"
                                value={paymentForm.plan_id}
                                onChange={(e) => {
                                    const pid = parseInt(e.target.value, 10);
                                    const p = plans.find(pl => pl.id === pid);
                                    setPaymentForm(prev => ({ 
                                        ...prev, 
                                        plan_id: pid, 
                                        amount: p?.price != null ? p.price : '' 
                                    }));
                                }}
                                className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                            >
                                {(Array.isArray(plans) ? plans : []).map(p => (
                                    <option key={p.id} value={p.id}>
                                        {isRtl ? p.display_name_ar : (p.display_name_en || p.name)} ({p.price} {t('super_admin.finance.currency') || 'ج.م'})
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Amount */}
                        <div className="space-y-2">
                            <label htmlFor="payment_amount_input" className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                                <Banknote size={16} /> {t('super_admin.payments.amount_col') || 'المبلغ المدفوع'}
                            </label>
                            <input
                                id="payment_amount_input"
                                type="number"
                                step="any"
                                min="0"
                                value={paymentForm.amount}
                                onChange={(e) => setPaymentForm(prev => ({ ...prev, amount: e.target.value }))}
                                className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                placeholder="0.00"
                            />
                        </div>

                        {/* Paid By (Users) */}
                        <div className="space-y-2">
                            <label htmlFor="payment_paid_by_select" className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                                <User size={16} /> {t('super_admin.payments.paid_by_col') || 'تم الدفع بواسطة'}
                            </label>
                            <select
                                id="payment_paid_by_select"
                                value={paymentForm.paid_by}
                                onChange={(e) => setPaymentForm(prev => ({ ...prev, paid_by: e.target.value }))}
                                className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                disabled={!paymentForm.tenant_id}
                            >
                                <option value="">{t('super_admin.payments.select_user') || 'اختر المستخدم'}</option>
                                {(Array.isArray(tenantUsers) ? tenantUsers : []).map(u => (
                                    <option key={u.id} value={u.username}>{u.username} ({u.role})</option>
                                ))}
                            </select>
                        </div>


                        {/* Payment Date */}
                        <div className="space-y-2">
                            <label className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                                <Calendar size={16} /> {t('super_admin.payments.date_col') || 'تاريخ الدفع'}
                            </label>
                            <DateTimePicker
                                mode="date"
                                value={paymentForm.payment_date}
                                onChange={(e) => setPaymentForm(prev => ({ ...prev, payment_date: e?.target?.value || e }))}
                            />
                        </div>

                        {/* Payment Method */}
                        <div className="space-y-2">
                            <label className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                                <Landmark size={16} /> {t('super_admin.payments.method_col') || 'وسيلة الدفع'}
                            </label>
                            <div className="grid grid-cols-3 gap-2">
                                {[
                                    { id: 'cash', label: t('super_admin.payments.cash') || 'نقدي', icon: Banknote },
                                    { id: 'bank_transfer', label: t('super_admin.payments.bank_transfer') || 'تحويل', icon: Landmark },
                                    { id: 'credit_card', label: t('super_admin.payments.credit_card') || 'بطاقة', icon: CreditCard }
                                ].map(method => (
                                    <button
                                        key={method.id}
                                        type="button"
                                        onClick={() => setPaymentForm(prev => ({ ...prev, payment_method: method.id }))}
                                        className={`flex flex-col items-center justify-center gap-1 p-2 rounded-xl border-2 transition-all ${paymentForm.payment_method === method.id
                                            ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400'
                                            : 'border-slate-100 dark:border-slate-800 text-slate-500 hover:border-slate-300'
                                            }`}
                                    >
                                        <method.icon size={16} />
                                        <span className="text-xs font-bold">{method.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Notes */}
                    <div className="space-y-2">
                        <label className="text-sm font-bold text-slate-700 dark:text-slate-300">
                            {t('common.notes') || 'ملاحظات إضافية'}
                        </label>
                        <textarea
                            value={paymentForm.notes}
                            onChange={(e) => setPaymentForm(prev => ({ ...prev, notes: e.target.value }))}
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none font-medium min-h-[80px]"
                            placeholder={t('super_admin.payments.notes_placeholder') || 'أضف أي ملاحظات هنا...'}
                        />
                    </div>

                    <div className="flex justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
                        <button
                            type="button"
                            onClick={() => setShowPaymentModal(false)}
                            disabled={processing}
                            className="px-6 py-3 rounded-xl font-bold text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        >
                            {t('common.cancel') || 'إلغاء'}
                        </button>
                        <button
                            type="submit"
                            disabled={processing}
                            className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-400 text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/30 transition-all"
                        >
                            {processing ? (t('common.saving') || 'جاري الحفظ...') : (
                                <>
                                    <PlusCircle size={18} />
                                    {t('super_admin.payments.submit_button') || 'تأكيد وحفظ الدفعة'}
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </Modal>

            {/* Accessible Confirmation Dialog for Payment Deletion */}
            <ConfirmDialog
                isOpen={Boolean(paymentToDelete)}
                onClose={() => setPaymentToDelete(null)}
                onConfirm={handleConfirmDeletePayment}
                title={t('super_admin.payments.delete_title') || 'حذف الدفعة'}
                message={t('super_admin.payments.delete_confirm_msg') || 'هل أنت متأكد من حذف هذه الدفعة المالية؟ لا يمكن التراجع عن هذا الإجراء.'}
                confirmText={t('common.delete') || 'حذف'}
                cancelText={t('common.cancel') || 'إلغاء'}
                variant="danger"
                isLoading={isDeleting}
            />
        </div>
    );
}
