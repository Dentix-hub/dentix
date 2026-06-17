import { useEffect, useState } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import { toast } from '@/shared/ui';
import { Building2, X, Key } from 'lucide-react';
import TenantsManager from '@/features/admin/SuperAdmin/TenantsManager';
import TenantDetailPanel from '@/features/admin/SuperAdmin/TenantDetailPanel';
import { getToken, getAdminToken, setAdminToken, removeAdminToken } from '@/utils';

export default function TenantsPage() {
    const [tenants, setTenants] = useState([]);
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedTenantId, setSelectedTenantId] = useState(null);

    // Shared State for Payment Modal (passed down)
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
                api.get('/api/v1/admin/subscriptions/plans')
            ]);
            setTenants(Array.isArray(tRes.data) ? tRes.data : []);
            setPlans(Array.isArray(pRes.data) ? pRes.data : []);
        } catch (err) {
            logger.error('Error fetching data:', err);
            setTenants([]);
            setPlans([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleImpersonate = async (tenantId, userId) => {
        try {
            const url = userId
                ? `/api/v1/admin/tenants/${tenantId}/impersonate?user_id=${userId}`
                : `/api/v1/admin/tenants/${tenantId}/impersonate`;

            const res = await api.post(url);
            const { access_token } = res.data;

            // Save original admin token to return later (stored in sessionStorage for impersonation only)
            const currentToken = getToken(); // Returns null with httpOnly cookies
            // Admin token is stored in sessionStorage for this special case
            const existingAdminToken = getAdminToken();
            if (!existingAdminToken) {
                // We can't read the httpOnly cookie, so we rely on the backend to handle the swap
                // For now, mark that we're in impersonation mode
                setAdminToken('impersonating');
            }

            // The backend sets new httpOnly cookies for the impersonated user
            // We just redirect - cookies handle the auth
            toast.success('جاري الدخول للنظام...');

            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1000);
        } catch (err) {
            toast.error('فشل عملية الدخول: ' + (err.response?.data?.detail || err.message));
        }
    };

    const handlePlanChange = (e, tenantId) => {
        const newPlanId = parseInt(e.target.value);
        if (!newPlanId) return;
        if (window.confirm('هل أنت متأكد من تغيير الخطة؟ سيتم احتساب المدة الجديدة بدءاً من اليوم.')) {
            api.post(`/api/v1/admin/tenants/${tenantId}/assign-plan?plan_id=${newPlanId}`)
                .then(() => fetchData())
                .catch(() => toast.error('فشل تغيير الخطة'));
        }
    };

    const handleResetPassword = async (tenantId) => {
        try {
            const res = await api.get(`/api/v1/admin/tenants/${tenantId}/users`);
            setTenantUsers(res.data.users || []);
            const tenant = tenants.find(t => t.id === tenantId);
            setShowPasswordResetModal({ tenantId, tenantName: tenant?.name || 'العيادة' });
            setPasswordResetForm({ user_id: '', new_password: '' });
        } catch (err) {
            logger.error('Error in handleResetPassword:', err);
            toast.error('فشل تحميل مستخدمي العيادة');
        }
    };
    const handleSubmitPasswordReset = async () => {
        if (!passwordResetForm.user_id || !passwordResetForm.new_password) {
            return toast.error('الرجاء اختيار المستخدم وإدخال كلمة المرور الجديدة');
        }
        if (passwordResetForm.new_password.length < 6) {
            return toast.error('كلمة المرور يجب أن تكون 6 أحرف على الأقل');
        }
        if (!window.confirm('هل أنت متأكد من إعادة تعيين كلمة المرور؟')) return;
        try {
            await api.post(`/api/v1/admin/system/users/${passwordResetForm.user_id}/reset-password`, {
                new_password: passwordResetForm.new_password
            });
            setShowPasswordResetModal(null);
            setPasswordResetForm({ user_id: '', new_password: '' });
            toast.success('تم إعادة تعيين كلمة المرور بنجاح');
        } catch (err) {
            logger.error(err);
            toast.error('فشل إعادة تعيين كلمة المرور');
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
            toast.success("تم الحذف بنجاح");
        } catch (error) {
            toast.error("فشلت عملية الحذف");
        }
    };
    const handleRestoreTenant = async (tenantId) => {
        if (!window.confirm("هل أنت متأكد من استعادة هذه العيادة؟")) return;
        try {
            await api.post(`/api/v1/admin/tenants/${tenantId}/restore`);
            fetchData();
            toast.success("تمت الاستعادة بنجاح");
        } catch (error) {
            toast.error("فشلت عملية الاستعادة");
        }
    };
    const handlePermanentDelete = async (tenantId) => {
        if (!window.confirm("تحذير: هذا الإجراء سيقوم بحذف العيادة وجميع بياناتها (المرضى، المواعيد، المستخدمين) بشكل نهائي ولا يمكن التراجع عنه!\n\nهل أنت متأكد تماماً؟")) return;
        try {
            await api.delete(`/api/v1/admin/tenants/${tenantId}/permanent`);
            fetchData();
            toast.success("تم الحذف النهائي بنجاح");
        } catch (error) {
            logger.error(error);
            toast.error("فشلت عملية الحذف النهائي");
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
                    <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white">إدارة العيادات</h1>
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
                onSelectTenant={(id) => setSelectedTenantId(id)}
            />

            <TenantDetailPanel
                tenantId={selectedTenantId}
                onClose={() => setSelectedTenantId(null)}
                onImpersonate={handleImpersonate}
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
                                <p className="text-xs text-slate-500 mt-2">💡 سيتم إلغاء قفل الحساب وتفعيله تلقائياً</p>
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