import { useEffect, useState } from 'react';
import { api } from '@/api';
import PaymentsManager from '@/features/admin/SuperAdmin/PaymentsManager';
import PlansManager from '@/features/admin/SuperAdmin/PlansManager';
import ActiveSubscriptions from '@/features/admin/SuperAdmin/ActiveSubscriptions';
import { CreditCard, PlusCircle, X, Banknote, Landmark, User, Calendar } from 'lucide-react';
export default function FinancePage() {
    const [activeTab, setActiveTab] = useState('payments'); // payments, plans, subscriptions
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
    // Plans Editing State
    const [editingPlan, setEditingPlan] = useState(null);
    const [editedPlanData, setEditedPlanData] = useState({});
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState(false);
    const fetchData = async () => {
        setLoading(true);
        try {
            const [payRes, tenRes, planRes] = await Promise.all([
                api.get('/api/v1/admin/payments'),
                api.get('/api/v1/admin/tenants'), // Needed for filtering payments
                api.get('/api/v1/admin/plans')
            ]);
            setPayments(Array.isArray(payRes.data) ? payRes.data : []);
            setTenants(Array.isArray(tenRes.data) ? tenRes.data : []);
            setPlans(Array.isArray(planRes.data) ? planRes.data : []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };
    useEffect(() => {
        fetchData();
    }, []);
    const handleSavePlan = async (planId) => {
        try {
            await api.put(`/admin/plans/${planId}`, editedPlanData);
            setEditingPlan(null);
            setEditedPlanData({});
            fetchData();
        } catch (err) {
            alert('فشل التعديل');
        }
    };
    const handleClinicChange = async (tenantId) => {
        setPaymentForm(prev => ({ ...prev, tenant_id: tenantId, paid_by: '' }));
        if (!tenantId) {
            setTenantUsers([]);
            return;
        }
        try {
            const res = await api.get(`/admin/system/tenants/${tenantId}/users`);
            // Ensure we always set an array, even if API returns unexpected data
            setTenantUsers(Array.isArray(res.data.users) ? res.data.users : []);
        } catch (err) {
            console.error(err);
            setTenantUsers([]); // Set empty array on error
        }
    };
    const handleRecordPayment = async () => {
        if (!paymentForm.tenant_id || !paymentForm.plan_id || !paymentForm.amount) {
            alert('الرجاء إكمال البيانات الأساسية');
            return;
        }
        setProcessing(true);
        try {
            await api.post('/api/v1/admin/payments', paymentForm);
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
            alert('تم تسجيل الدفعة بنجاح');
        } catch (err) {
            alert('فشل تسجيل الدفعة');
        } finally {
            setProcessing(false);
        }
    };
    const getDaysRemaining = (endDate) => {
        if (!endDate) return null;
        const days = Math.ceil((new Date(endDate) - new Date()) / (1000 * 60 * 60 * 24));
        return days;
    };
    if (loading) return <div className="p-8 text-center text-slate-500">جاري تحميل البيانات المالية...</div>;
    return (
        <div className="space-y-6 animate-fade-in-up">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-4">
                    <div className="bg-emerald-50 dark:bg-emerald-900/20 p-4 rounded-2xl text-emerald-600 dark:text-emerald-400">
                        <CreditCard size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-black text-slate-800 dark:text-white">الإدارة المالية</h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">المدفوعات وخطط الاشتراك</p>
                    </div>
                </div>
                <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
                    <button
                        onClick={() => setActiveTab('payments')}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'payments' ? 'bg-white dark:bg-slate-700 shadow text-emerald-600' : 'text-slate-500'}`}
                    >
                        المدفوعات
                    </button>
                    <button
                        onClick={() => setActiveTab('subscriptions')}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'subscriptions' ? 'bg-white dark:bg-slate-700 shadow text-emerald-600' : 'text-slate-500'}`}
                    >
                        الاشتراكات
                    </button>
                    <button
                        onClick={() => setActiveTab('plans')}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'plans' ? 'bg-white dark:bg-slate-700 shadow text-emerald-600' : 'text-slate-500'}`}
                    >
                        الخطط
                    </button>
                </div>
                <button
                    onClick={() => {
                        setShowPaymentModal(true);
                        if (plans.length > 0) {
                            setPaymentForm(prev => ({ ...prev, plan_id: plans[0].id, amount: plans[0].price }));
                        }
                    }}
                    className="flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold shadow-lg shadow-emerald-500/30 transition-all transform hover:scale-105"
                >
                    <PlusCircle size={20} />
                    تسجيل دفعة
                </button>
            </div>
            {activeTab === 'payments' ? (
                <PaymentsManager
                    payments={payments}
                    tenants={tenants}
                    plans={plans}
                    onDelete={async (id) => {
                        if (!window.confirm('هل أنت متأكد من حذف هذه الدفعة؟')) return;
                        try {
                            await api.delete(`/admin/payments/${id}`);
                            fetchData();
                            alert('تم حذف الدفعة بنجاح');
                        } catch (err) {
                            alert('فعل الحذف');
                        }
                    }}
                />
            ) : activeTab === 'subscriptions' ? (
                <ActiveSubscriptions
                    tenants={tenants}
                    plans={plans}
                    getDaysRemaining={getDaysRemaining}
                />
            ) : (
                <PlansManager
                    plans={plans}
                    editingPlan={editingPlan}
                    setEditingPlan={setEditingPlan}
                    editedPlanData={editedPlanData}
                    setEditedPlanData={setEditedPlanData}
                    handleSavePlan={handleSavePlan}
                    onRefresh={fetchData}
                />
            )}
            {/* Enhanced Payment Modal */}
            {showPaymentModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 w-full max-w-xl shadow-2xl space-y-6">
                        <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-4">
                            <div>
                                <h3 className="text-xl font-bold text-slate-800 dark:text-white">تسجيل دفعة جديدة</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">أضف تفاصيل الدفعة المالية للعيادة</p>
                            </div>
                            <button
                                onClick={() => setShowPaymentModal(false)}
                                className="p-2 bg-slate-100 dark:bg-slate-800 rounded-full hover:bg-slate-200"
                            >
                                <X size={20} />
                            </button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Clinic Selection */}
                            <div className="space-y-2">
                                <label className="flex items-center gap-2 text-sm font-bold text-slate-500">
                                    <PlusCircle size={16} /> العيادة
                                </label>
                                <select
                                    value={paymentForm.tenant_id}
                                    onChange={(e) => handleClinicChange(e.target.value)}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                >
                                    <option value="">اختر العيادة</option>
                                    {(Array.isArray(tenants) ? tenants : []).map(t => (
                                        <option key={t.id} value={t.id}>{t.name}</option>
                                    ))}
                                </select>
                            </div>
                            {/* Plan Selection */}
                            <div className="space-y-2">
                                <label className="flex items-center gap-2 text-sm font-bold text-slate-500">
                                    <CreditCard size={16} /> الخطة
                                </label>
                                <select
                                    value={paymentForm.plan_id}
                                    onChange={(e) => {
                                        const pid = parseInt(e.target.value);
                                        const p = plans.find(pl => pl.id === pid);
                                        setPaymentForm({ ...paymentForm, plan_id: pid, amount: p ? p.price : '' });
                                    }}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                >
                                    {(Array.isArray(plans) ? plans : []).map(p => (
                                        <option key={p.id} value={p.id}>{p.display_name_ar} ({p.price} ج.م)</option>
                                    ))}
                                </select>
                            </div>
                            {/* Amount */}
                            <div className="space-y-2">
                                <label className="flex items-center gap-2 text-sm font-bold text-slate-500">
                                    <Banknote size={16} /> المبلغ المدفوع
                                </label>
                                <input
                                    type="number"
                                    value={paymentForm.amount}
                                    onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                />
                            </div>
                            {/* Paid By (Users) */}
                            <div className="space-y-2">
                                <label className="flex items-center gap-2 text-sm font-bold text-slate-500">
                                    <User size={16} /> تم الدفع بواسطة
                                </label>
                                <select
                                    value={paymentForm.paid_by}
                                    onChange={(e) => setPaymentForm({ ...paymentForm, paid_by: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                    disabled={!paymentForm.tenant_id}
                                >
                                    <option value="">اختر المستخدم</option>
                                    {(Array.isArray(tenantUsers) ? tenantUsers : []).map(u => (
                                        <option key={u.id} value={u.username}>{u.username} ({u.role === 'manager' ? 'مدير' : 'طبيب'})</option>
                                    ))}
                                </select>
                            </div>
                            {/* Payment Date */}
                            <div className="space-y-2">
                                <label className="flex items-center gap-2 text-sm font-bold text-slate-500">
                                    <Calendar size={16} /> تاريخ الدفع
                                </label>
                                <input
                                    type="date"
                                    value={paymentForm.payment_date}
                                    onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-bold"
                                />
                            </div>
                            {/* Payment Method */}
                            <div className="space-y-2">
                                <label className="flex items-center gap-2 text-sm font-bold text-slate-500">
                                    <Landmark size={16} /> وسيلة الدفع
                                </label>
                                <div className="grid grid-cols-3 gap-2">
                                    {[
                                        { id: 'cash', label: 'نقدي', icon: Banknote },
                                        { id: 'bank_transfer', label: 'تحويل', icon: Landmark },
                                        { id: 'credit_card', label: 'بطاقة', icon: CreditCard }
                                    ].map(method => (
                                        <button
                                            key={method.id}
                                            type="button"
                                            onClick={() => setPaymentForm({ ...paymentForm, payment_method: method.id })}
                                            className={`flex flex-col items-center justify-center gap-1 p-2 rounded-xl border-2 transition-all ${paymentForm.payment_method === method.id
                                                ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600'
                                                : 'border-slate-100 dark:border-slate-800 text-slate-400 hover:border-slate-300'
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
                            <label className="text-sm font-bold text-slate-500">ملاحظات إضافية</label>
                            <textarea
                                value={paymentForm.notes}
                                onChange={(e) => setPaymentForm({ ...paymentForm, notes: e.target.value })}
                                className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-emerald-500 outline-none font-medium min-h-[80px]"
                                placeholder="أضف أي ملاحظات هنا..."
                            ></textarea>
                        </div>
                        <button
                            onClick={handleRecordPayment}
                            disabled={processing}
                            className="w-full py-4 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-400 text-white rounded-2xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/30 text-lg hover:scale-[1.02] transition-all"
                        >
                            {processing ? 'جاري الحفظ...' : (
                                <>
                                    <PlusCircle size={20} />
                                    تأكيد وحفظ الدفعة
                                </>
                            )}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
