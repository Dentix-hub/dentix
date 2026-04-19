import { useEffect, useState } from 'react';
import { api } from '@/api';
import TenantsManager from '@/features/admin/SuperAdmin/TenantsManager';
import { Building2, X, Key } from 'lucide-react';
export default function TenantsPage() {
    const [tenants, setTenants] = useState([]);
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    // Shared State for Payment Modal (passed down)
    // In a fuller refactor, Modal state should be handled locally in TenantsManager or global context
    // For now, keeping it here to match TenantsManager props API
    const [showPaymentModal, setShowPaymentModal] = useState(null);
    const [paymentForm, setPaymentForm] = useState({ plan_id: '', amount: '', payment_method: 'cash', notes: '' });
    // Password Reset State
    const [showPasswordResetModal, setShowPasswordResetModal] = useState(null); // {tenantId, tenantName}
    const [tenantUsers, setTenantUsers] = useState([]);
    const [passwordResetForm, setPasswordResetForm] = useState({ user_id: '', new_password: '' });
    const fetchData = async () => {
        setLoading(true);
        try {
            const [tRes, pRes] = await Promise.all([
                api.get('/api/v1/admin/tenants'),
                api.get('/api/v1/admin/plans')
            ]);
            // Ensure we have arrays, even if the API returns unexpected data
            setTenants(Array.isArray(tRes.data) ? tRes.data : []);
            setPlans(Array.isArray(pRes.data) ? pRes.data : []);
        } catch (err) {
            console.error('Error fetching data:', err);
            // Set empty arrays in case of error to prevent the map error
            setTenants([]);
            setPlans([]);
        } finally {
            setLoading(false);
        }
    };
    useEffect(() => {
        fetchData();
    }, []);
    const handlePlanChange = (e, tenantId) => {
        const newPlanId = parseInt(e.target.value);
        if (!newPlanId) return;
        if (window.confirm('هل أنت متأكد من تغيير الخطة؟ سيتم احتساب المدة الجديدة بدءاً من اليوم.')) {
            api.post(`/api/v1/admin/tenants/${tenantId}/assign-plan?plan_id=${newPlanId}`)
                .then(() => fetchData())
                .catch(() => alert('فشل تغيير الخطة'));
        }
    };
    const handleResetPassword = async (tenantId) => {
        try {
            const res = await api.get(`/api/v1/admin/system/tenants/${tenantId}/users`);
            setTenantUsers(res.data.users || []);
            const tenant = tenants.find(t => t.id === tenantId);
            setShowPasswordResetModal({ tenantId, tenantName: tenant?.name || 'العيادة' });
            setPasswordResetForm({ user_id: '', new_password: '' });
        } catch (err) {
            console.error('Error in handleResetPassword:', err);
            alert('فشل تحميل مستخدمي العيادة: ' + (err.response?.data?.detail || err.message));
        }
    };
    const handleSubmitPasswordReset = async () => {
        if (!passwordResetForm.user_id || !passwordResetForm.new_password) {
            return alert('الرجاء اختيار المستخدم وإدخال كلمة المرور الجديدة');
        }
        if (passwordResetForm.new_password.length < 6) {
            return alert('كلمة المرور يجب أن تكون 6 أحرف على الأقل');
        }
        if (!window.confirm('هل أنت متأكد من إعادة تعيين كلمة المرور؟')) return;
        try {
            await api.post(`/api/v1/admin/system/users/${passwordResetForm.user_id}/reset-password`, {
                new_password: passwordResetForm.new_password
            });
            setShowPasswordResetModal(null);
            setPasswordResetForm({ user_id: '', new_password: '' });
            alert('تم إعادة تعيين كلمة المرور بنجاح');
        } catch (err) {
            console.error(err);
            alert('فشل إعادة تعيين كلمة المرور');
        }
    };
    const getDaysRemaining = (endDate) => {
        if (!endDate) return null;
        const days = Math.ceil((new Date(endDate) - new Date()) / (1000 * 60 * 60 * 24));
        return days;
    };
    const handleArchiveTenant = async (tenantId) => {
        if (!window.confirm("هل أنت متأكد من حذف هذه العيادة؟ (يمكنك استعادتها لاحقاً)")) return;
        try {
            await api.delete(`/api/v1/admin/tenants/${tenantId}`);
            fetchData();
            alert("تم الحذف بنجاح");
        } catch (error) {
            alert("فشلت عملية الحذف");
        }
    };
    const handleRestoreTenant = async (tenantId) => {
        if (!window.confirm("هل أنت متأكد من استعادة هذه العيادة؟")) return;
        try {
            await api.post(`/api/v1/admin/tenants/${tenantId}/restore`);
            fetchData();
            alert("تمت الاستعادة بنجاح");
        } catch (error) {
            alert("فشلت عملية الاستعادة");
        }
    };
    const handlePermanentDelete = async (tenantId) => {
        if (!window.confirm("تحذير: هذا الإجراء سيقوم بحذف العيادة وجميع بياناتها (المرضى، المواعيد، المستخدمين) بشكل نهائي ولا يمكن التراجع عنه!\n\nهل أنت متأكد تماماً؟")) return;
        try {
            await api.delete(`/api/v1/admin/tenants/${tenantId}/permanent`);
            fetchData();
            alert("تم الحذف النهائي بنجاح");
        } catch (error) {
            console.error(error);
            alert("فشلت عملية الحذف النهائي");
        }
    };
    if (loading) return <div className="p-8 text-center text-slate-500">جاري تحميل العيادات...</div>;
    return (
        <div className="space-y-6 animate-fade-in-up">
            <div className="flex items-center gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="bg-indigo-50 dark:bg-indigo-900/20 p-4 rounded-2xl text-indigo-600 dark:text-indigo-400">
                    <Building2 size={32} />
                </div>
                <div>
                    <h1 className="text-2xl font-black text-slate-800 dark:text-white">إدارة العيادات</h1>
                    <p className="text-slate-500 dark:text-slate-400 font-medium mt-1">التحكم في العيادات المشتركة وحالتها</p>
                </div>
            </div>
            <TenantsManager
                tenants={tenants}
                plans={plans}
                handlePlanChange={handlePlanChange}
                setShowPaymentModal={setShowPaymentModal}
                setPaymentForm={setPaymentForm}
                getDaysRemaining={getDaysRemaining}
                handleArchiveTenant={handleArchiveTenant}
                handleRestoreTenant={handleRestoreTenant}
                handlePermanentDelete={handlePermanentDelete}
                onResetPassword={handleResetPassword}
            />
            {/* Payment Modal Logic would arguably live here or in parent, but strict refactor suggests placing it where triggered. 
                However, for speed, assuming TenantsPage focuses on List. 
                If existing TenantsManager expects to trigger a modal relative to 'SuperAdmin.jsx', we might need to adapt it. 
                Currently TenantsManager accepts setShowPaymentModal.
            */}
            {/* Password Reset Modal */}
            {showPasswordResetModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 w-full max-w-lg shadow-2xl space-y-6">
                        <div className="flex justify-between items-center">
                            <div>
                                <h3 className="text-xl font-bold text-slate-800 dark:text-white">إعادة تعيين كلمة المرور</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">{showPasswordResetModal.tenantName}</p>
                            </div>
                            <button
                                onClick={() => setShowPasswordResetModal(null)}
                                className="p-2 bg-slate-100 dark:bg-slate-800 rounded-full hover:bg-slate-200"
                            >
                                <X size={20} />
                            </button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">المستخدم</label>
                                <select
                                    value={passwordResetForm.user_id}
                                    onChange={(e) => setPasswordResetForm({ ...passwordResetForm, user_id: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-amber-500 outline-none font-bold"
                                >
                                    <option value="">اختر المستخدم</option>
                                    {tenantUsers.map(u => (
                                        <option key={u.id} value={u.id}>
                                            {u.username || u.email || 'Unknown User'} ({u.email}) - {u.role}
                                            {!u.is_active && ' [معطل]'}
                                            {u.account_locked_until && ' [مقفل]'}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-slate-500 mb-1.5">كلمة المرور الجديدة</label>
                                <input
                                    type="text"
                                    value={passwordResetForm.new_password}
                                    onChange={(e) => setPasswordResetForm({ ...passwordResetForm, new_password: e.target.value })}
                                    placeholder="أدخل كلمة المرور الجديدة (6 أحرف على الأقل)"
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-amber-500 outline-none font-bold"
                                />
                                <p className="text-xs text-slate-400 mt-2">💡 سيتم إلغاء قفل الحساب وتفعيله تلقائياً</p>
                            </div>
                            <button
                                onClick={handleSubmitPasswordReset}
                                className="w-full py-4 bg-amber-500 hover:bg-amber-600 text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg shadow-amber-500/20 text-lg hover:scale-[1.02] transition-all"
                            >
                                <Key size={20} />
                                إعادة تعيين كلمة المرور
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

