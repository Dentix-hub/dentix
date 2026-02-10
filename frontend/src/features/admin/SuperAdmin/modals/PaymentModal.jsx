import { useState, useEffect } from 'react';
import { X, Banknote, Landmark, CreditCard, PlusCircle } from 'lucide-react';
import { api } from '@/api';
export default function PaymentModal({ tenant, onClose, onSuccess }) {
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState({
        plan_id: '',
        amount: '',
        payment_method: 'cash',
        notes: ''
    });
    useEffect(() => {
        fetchPlans();
    }, []);
    const fetchPlans = async () => {
        try {
            const res = await api.get('/api/v1/admin/plans'); // Corrected path
            setPlans(Array.isArray(res.data) ? res.data : []);
        } catch (err) {
            console.error("Failed to fetch plans", err);
        }
    };
    const handleSubmit = async () => {
        if (!form.plan_id || !form.amount) return alert('الرجاء اختيار الخطة والمبلغ');
        try {
            setLoading(true);
            await api.post('/api/v1/admin/payments', {
                ...form,
                tenant_id: tenant.id
            });
            onSuccess?.();
            onClose();
            alert('تم تسجيل الدفعة بنجاح');
        } catch (err) {
            console.error(err);
            alert('فشل تسجيل الدفعة');
        } finally {
            setLoading(false);
        }
    };
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
            <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 w-full max-w-lg shadow-2xl space-y-6">
                <div className="flex justify-between items-center">
                    <div>
                        <h3 className="text-xl font-bold text-slate-800 dark:text-white">تسجيل دفعة جديدة</h3>
                        <p className="text-slate-500 dark:text-slate-400 text-sm">{tenant.name}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 bg-slate-100 dark:bg-slate-800 rounded-full hover:bg-slate-200"
                    >
                        <X size={20} />
                    </button>
                </div>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-bold text-slate-500 mb-1.5">خطة الاشتراك</label>
                        <select
                            value={form.plan_id}
                            onChange={(e) => {
                                const pid = parseInt(e.target.value);
                                const p = plans.find(pl => pl.id === pid);
                                setForm({ ...form, plan_id: pid, amount: p ? p.price : '' });
                            }}
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
                        >
                            <option value="">اختر الخطة</option>
                            {plans.map(p => (
                                <option key={p.id} value={p.id}>{p.display_name_ar} ({p.price} ج.م)</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-bold text-slate-500 mb-1.5">المبلغ المدفوع</label>
                        <input
                            type="number"
                            value={form.amount}
                            onChange={(e) => setForm({ ...form, amount: e.target.value })}
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none font-bold"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-bold text-slate-500 mb-1.5">وسيلة الدفع</label>
                        <div className="grid grid-cols-3 gap-3">
                            {[
                                { id: 'cash', label: 'نقدي', icon: Banknote },
                                { id: 'bank_transfer', label: 'تحويل', icon: Landmark },
                                { id: 'credit_card', label: 'بطاقة', icon: CreditCard }
                            ].map(method => (
                                <button
                                    key={method.id}
                                    onClick={() => setForm({ ...form, payment_method: method.id })}
                                    className={`flex flex-col items-center justify-center gap-2 p-3 rounded-xl border-2 transition-all ${form.payment_method === method.id
                                        ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600'
                                        : 'border-slate-100 dark:border-slate-800 text-slate-400 hover:border-slate-300'
                                        }`}
                                >
                                    <method.icon size={20} />
                                    <span className="text-xs font-bold">{method.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                    <button
                        onClick={handleSubmit}
                        disabled={loading}
                        className={`w-full py-4 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg text-lg transition-all ${loading
                            ? 'bg-slate-300 cursor-not-allowed'
                            : 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-emerald-500/20 hover:scale-[1.02]'}`}
                    >
                        <PlusCircle size={20} />
                        {loading ? 'جاري الحفظ...' : 'حفظ العملية'}
                    </button>
                </div>
            </div>
        </div>
    );
}
