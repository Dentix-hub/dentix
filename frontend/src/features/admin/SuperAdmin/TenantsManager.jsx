import { useState, useEffect } from 'react';
import { Edit3, Clock, Trash2, Key, DollarSign } from 'lucide-react';
import { api } from '@/api';
import PaymentModal from './modals/PaymentModal';
import PasswordResetModal from './modals/PasswordResetModal';
export default function TenantsManager() {
    const [tenants, setTenants] = useState([]);
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showPaymentModal, setShowPaymentModal] = useState(null);
    const [showPasswordResetModal, setShowPasswordResetModal] = useState(null);
    useEffect(() => {
        fetchData();
    }, []);
    const fetchData = async () => {
        try {
            setLoading(true);
            const [tenantsRes, plansRes] = await Promise.all([
                api.get('/api/v1/admin/tenants'),
                api.get('/api/v1/admin/plans')
            ]);
            setTenants(Array.isArray(tenantsRes.data) ? tenantsRes.data : []);
            setPlans(Array.isArray(plansRes.data) ? plansRes.data : []);
        } catch (error) {
            console.error("Failed to fetch data", error);
        } finally {
            setLoading(false);
        }
    };
    const handlePlanChange = async (e, tenantId) => {
        const newPlanId = parseInt(e.target.value);
        if (!newPlanId) return;
        if (window.confirm('هل أنت متأكد من تغيير الخطة؟ سيتم احتساب المدة الجديدة بدءاً من اليوم.')) {
            try {
                await api.post(`/api/v1/admin/tenants/${tenantId}/assign-plan?plan_id=${newPlanId}`);
                fetchData();
                alert('تم تغيير الخطة بنجاح');
            } catch (err) {
                console.error(err);
                alert('فشل تغيير الخطة');
            }
        }
    };
    const handleArchiveTenant = async (tenantId) => {
        if (!window.confirm("هل أنت متأكد من أرشفة هذه العيادة؟ ستختفي من القائمة النشطة ويتم تعطيل دخول المستخدمين.")) return;
        try {
            await api.delete(`/api/v1/admin/tenants/${tenantId}`);
            fetchData();
            alert("تمت الأرشفة بنجاح");
        } catch (error) {
            console.error(error);
            alert("فشلت عملية الأرشفة");
        }
    };
    const handleRestoreTenant = async (tenantId) => {
        if (!window.confirm("هل أنت متأكد من استعادة هذه العيادة؟")) return;
        try {
            await api.post(`/api/v1/admin/tenants/${tenantId}/restore`);
            fetchData();
            alert("تمت الاستعادة بنجاح");
        } catch (error) {
            console.error(error);
            alert("فشلت عملية الاستعادة");
        }
    };
    const handlePermanentDelete = async (tenantId) => {
        if (!window.confirm("تحذير: هذا الإجراء لا يمكن التراجع عنه! سيتم حذف كل بيانات العيادة بما فيها المرضى والملفات. هل أنت متأكد تماماً؟")) return;
        try {
            await api.delete(`/api/v1/admin/tenants/${tenantId}/permanent`);
            fetchData();
            alert("تم الحذف النهائي بنجاح");
        } catch (error) {
            console.error(error);
            alert("فشل الحذف النهائي: " + (error.response?.data?.detail || error.message));
        }
    };
    const getDaysRemaining = (endDate) => {
        if (!endDate) return null;
        const days = Math.ceil((new Date(endDate) - new Date()) / (1000 * 60 * 60 * 24));
        return days;
    };
    if (loading) return <div className="p-10 text-center text-slate-500 animate-pulse">جاري تحميل العيادات...</div>;
    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-right">
                    <thead>
                        <tr className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-sm font-bold uppercase tracking-wider">
                            <th className="p-6">العيادة</th>
                            <th className="p-6">خطة الاشتراك</th>
                            <th className="p-6">حالة الاشتراك</th>
                            <th className="p-6">المدة المتبقية</th>
                            <th className="p-6">إجمالي المدفوعات</th>
                            <th className="p-6 text-center">إجراءات سريعة</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {tenants.map((tenant) => {
                            const daysLeft = getDaysRemaining(tenant.subscription_end_date);
                            const isDeleted = tenant.is_deleted;
                            return (
                                <tr key={tenant.id} className={`transition-colors ${isDeleted ? 'bg-red-50 dark:bg-red-900/10' : 'hover:bg-slate-50/50 dark:hover:bg-slate-800/50'}`}>
                                    <td className="p-6 font-bold text-slate-800 dark:text-slate-200">
                                        <div className="flex items-center gap-3">
                                            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${isDeleted ? 'bg-red-100 text-red-600' : 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/50 dark:text-indigo-400'}`}>
                                                {tenant.name.charAt(0)}
                                            </div>
                                            <div>
                                                {tenant.name}
                                                {isDeleted && <span className="mr-2 text-xs text-red-500 font-bold">(مؤرشف)</span>}
                                            </div>
                                        </div>
                                    </td>
                                    <td className="p-6">
                                        {!isDeleted ? (
                                            <div className="relative">
                                                <select
                                                    value={tenant.plan_id || ''}
                                                    onChange={(e) => handlePlanChange(e, tenant.id)}
                                                    className="appearance-none w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 py-2 pr-4 pl-10 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium cursor-pointer"
                                                >
                                                    <option value="" disabled>اختر خطة</option>
                                                    {plans.map(p => (
                                                        <option key={p.id} value={p.id}>{p.display_name_ar}</option>
                                                    ))}
                                                </select>
                                                <Edit3 size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                                            </div>
                                        ) : (
                                            <span className="text-slate-400">-</span>
                                        )}
                                    </td>
                                    <td className="p-6">
                                        <span className={`px-4 py-1.5 rounded-full text-xs font-bold inline-flex items-center gap-1.5 ${tenant.is_active && (!daysLeft || daysLeft > 0)
                                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                                            : 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400'
                                            }`}>
                                            <span className={`w-2 h-2 rounded-full ${tenant.is_active && (!daysLeft || daysLeft > 0) ? 'bg-emerald-500' : 'bg-rose-500'
                                                }`} />
                                            {tenant.is_active && (!daysLeft || daysLeft > 0) ? 'نشط' : 'منتهي/معطل'}
                                        </span>
                                    </td>
                                    <td className="p-6">
                                        {daysLeft !== null ? (
                                            <div className={`flex items-center gap-2 font-bold ${daysLeft < 7 ? 'text-rose-500' : 'text-slate-600 dark:text-slate-400'
                                                }`}>
                                                <Clock size={16} />
                                                {daysLeft} يوم
                                            </div>
                                        ) : (
                                            <span className="text-slate-400 text-2xl">∞</span>
                                        )}
                                    </td>
                                    <td className="p-6 font-bold text-emerald-600 dark:text-emerald-400">{tenant.total_revenue?.toLocaleString() || 0} ج.م</td>
                                    <td className="p-6 text-center flex items-center justify-center gap-2">
                                        {!isDeleted ? (
                                            <>
                                                <button
                                                    onClick={() => setShowPaymentModal(tenant)}
                                                    className="inline-flex items-center gap-2 px-3 py-2 bg-indigo-100 hover:bg-indigo-200 text-indigo-600 rounded-xl text-xs font-bold transition-all"
                                                    title="تسجيل دفعة"
                                                >
                                                    <DollarSign size={16} />
                                                </button>
                                                <button
                                                    onClick={() => setShowPasswordResetModal(tenant)}
                                                    className="inline-flex items-center gap-2 px-3 py-2 bg-amber-100 hover:bg-amber-200 text-amber-600 rounded-xl text-xs font-bold transition-all"
                                                    title="إعادة تعيين كلمة المرور"
                                                >
                                                    <Key size={16} />
                                                </button>
                                                <button
                                                    onClick={() => handleArchiveTenant(tenant.id)}
                                                    className="inline-flex items-center gap-2 px-3 py-2 bg-rose-100 hover:bg-rose-200 text-rose-600 rounded-xl text-xs font-bold transition-all"
                                                    title="حذف العيادة"
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            </>
                                        ) : (
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => handleRestoreTenant(tenant.id)}
                                                    className="inline-flex items-center gap-2 px-3 py-2 bg-emerald-100 hover:bg-emerald-200 text-emerald-600 rounded-xl text-xs font-bold transition-all"
                                                >
                                                    استعادة
                                                </button>
                                                <button
                                                    onClick={() => handlePermanentDelete(tenant.id)}
                                                    className="inline-flex items-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-red-500/30"
                                                    title="حذف نهائي (لا يمكن التراجع عنه)"
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                        {tenants.length === 0 && (
                            <tr>
                                <td colSpan="6" className="p-10 text-center text-slate-500">لا توجد عيادات مسجلة حتى الآن</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
            {/* Modals */}
            {showPaymentModal && (
                <PaymentModal
                    tenant={showPaymentModal}
                    onClose={() => setShowPaymentModal(null)}
                    onSuccess={fetchData}
                />
            )}
            {showPasswordResetModal && (
                <PasswordResetModal
                    tenant={showPasswordResetModal}
                    onClose={() => setShowPasswordResetModal(null)}
                />
            )}
        </div>
    );
};
