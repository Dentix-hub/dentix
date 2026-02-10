import { useState, useEffect } from 'react';
import { Banknote, Landmark, CreditCard, Check, Trash2 } from 'lucide-react';
import { api } from '@/api';
export default function PaymentsManager() {
    const [payments, setPayments] = useState([]);
    const [tenants, setTenants] = useState([]);
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        fetchData();
    }, []);
    const fetchData = async () => {
        try {
            setLoading(true);
            const [payRes, tenRes, planRes] = await Promise.all([
                api.get('/api/v1/admin/payments'),
                api.get('/api/v1/admin/tenants'),
                api.get('/api/v1/admin/plans')
            ]);
            setPayments(Array.isArray(payRes.data) ? payRes.data : []);
            setTenants(Array.isArray(tenRes.data) ? tenRes.data : []);
            setPlans(Array.isArray(planRes.data) ? planRes.data : []);
        } catch (err) {
            console.error("Failed to fetch payment data", err);
        } finally {
            setLoading(false);
        }
    };
    const handleDelete = async (id) => {
        if (!window.confirm('هل أنت متأكد من حذف هذا السجل؟')) return;
        try {
            await api.delete(`/api/v1/admin/payments/${id}`);
            setPayments(prev => prev.filter(p => p.id !== id));
            alert('تم حذف السجل بنجاح');
        } catch (err) {
            console.error(err);
            alert('فشل الحذف');
        }
    };
    if (loading) return <div className="p-10 text-center text-slate-500 animate-pulse">جاري تحميل المدفوعات...</div>;
    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-right">
                    <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-sm font-bold uppercase">
                        <tr>
                            <th className="p-6">التاريخ</th>
                            <th className="p-6">العيادة</th>
                            <th className="p-6">الخطة</th>
                            <th className="p-6">المبلغ</th>
                            <th className="p-6">تم الدفع بواسطة</th>
                            <th className="p-6">وسيلة الدفع</th>
                            <th className="p-6">الحالة</th>
                            <th className="p-6">إجراءات</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {(Array.isArray(payments) && payments.length > 0) ? payments.map(payment => (
                            <tr key={payment.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                                <td className="p-6 font-medium text-sm text-slate-600 dark:text-slate-400">
                                    {new Date(payment.payment_date).toLocaleDateString('ar-EG', { year: 'numeric', month: 'long', day: 'numeric' })}
                                </td>
                                <td className="p-6 font-bold text-slate-800 dark:text-slate-200">
                                    {tenants.find(t => t.id === payment.tenant_id)?.name || '-'}
                                </td>
                                <td className="p-6 text-sm font-medium text-slate-600 dark:text-slate-400">
                                    {plans.find(p => p.id === payment.plan_id)?.display_name_ar || '-'}
                                </td>
                                <td className="p-6 font-black text-emerald-600 dark:text-emerald-400">
                                    +{payment.amount.toLocaleString()} ج.م
                                </td>
                                <td className="p-6 text-sm font-bold text-slate-700 dark:text-slate-300">
                                    {payment.paid_by || '-'}
                                </td>
                                <td className="p-6">
                                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold ${payment.payment_method === 'cash' ? 'bg-green-100 text-green-700' :
                                        payment.payment_method === 'bank_transfer' ? 'bg-blue-100 text-blue-700' :
                                            'bg-purple-100 text-purple-700'
                                        }`}>
                                        {payment.payment_method === 'cash' && <Banknote size={14} />}
                                        {payment.payment_method === 'bank_transfer' && <Landmark size={14} />}
                                        {payment.payment_method === 'credit_card' && <CreditCard size={14} />}
                                        {payment.payment_method === 'cash' ? 'نقدي' :
                                            payment.payment_method === 'bank_transfer' ? 'تحويل بنكي' :
                                                'بطاقة ائتمان'}
                                    </span>
                                </td>
                                <td className="p-6">
                                    <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-sm font-bold">
                                        <Check size={16} /> مكتكلة
                                    </div>
                                </td>
                                <td className="p-6">
                                    <button
                                        onClick={() => handleDelete(payment.id)}
                                        className="p-2 text-rose-500 hover:bg-rose-50 rounded-lg transition-colors"
                                        title="حذف الدفعة"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="8" className="p-10 text-center text-slate-500">لا توجد سجلات دفع حتى الآن</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
