import { useState, useEffect } from 'react';
import { X, Key } from 'lucide-react';
import { api } from '@/api';
export default function PasswordResetModal({ tenant, onClose }) {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [form, setForm] = useState({ user_id: '', new_password: '' });
    useEffect(() => {
        if (tenant?.id) {
            fetchTenantUsers();
        }
    }, [tenant]);
    const fetchTenantUsers = async () => {
        try {
            setLoading(true);
            const res = await api.get(`/api/v1/admin/tenants/${tenant.id}/users`); // Corrected path
            setUsers(res.data.users || []);
        } catch (err) {
            console.error("Failed to fetch users", err);
            alert("فشل تحميل مستخدمي العيادة");
        } finally {
            setLoading(false);
        }
    };
    const handleSubmit = async () => {
        if (!form.user_id || !form.new_password) {
            return alert('الرجاء اختيار المستخدم وإدخال كلمة المرور الجديدة');
        }
        if (form.new_password.length < 6) {
            return alert('كلمة المرور يجب أن تكون 6 أحرف على الأقل');
        }
        if (!window.confirm('هل أنت متأكد من إعادة تعيين كلمة المرور؟')) return;
        try {
            setSubmitting(true);
            await api.post(`/api/v1/admin/system/users/${form.user_id}/reset-password`, {
                new_password: form.new_password
            });
            alert('تم إعادة تعيين كلمة المرور بنجاح');
            onClose();
        } catch (err) {
            console.error(err);
            alert('فشل إعادة تعيين كلمة المرور');
        } finally {
            setSubmitting(false);
        }
    };
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
            <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 w-full max-w-lg shadow-2xl space-y-6">
                <div className="flex justify-between items-center">
                    <div>
                        <h3 className="text-xl font-bold text-slate-800 dark:text-white">إعادة تعيين كلمة المرور</h3>
                        <p className="text-slate-500 dark:text-slate-400 text-sm">
                            {tenant.name}
                            {form.user_id && (
                                <span className="text-amber-600 dark:text-amber-400 font-bold mr-1">
                                    {' '}→{' '}
                                    {users.find(u => String(u.id) === form.user_id)?.username ||
                                        users.find(u => String(u.id) === form.user_id)?.email ||
                                        'مستخدم'}
                                </span>
                            )}
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 bg-slate-100 dark:bg-slate-800 rounded-full hover:bg-slate-200"
                    >
                        <X size={20} />
                    </button>
                </div>
                <div className="space-y-4">
                    {loading ? (
                        <div className="p-4 text-center text-slate-500">جاري تحميل المستخدمين...</div>
                    ) : (
                        <div>
                            <label className="block text-sm font-bold text-slate-500 mb-1.5">المستخدم</label>
                            {users.length === 0 ? (
                                <div className="w-full px-4 py-3 rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700 text-amber-700 dark:text-amber-400 text-sm font-bold">
                                    ⚠️ لا يوجد مستخدمين مسجلين لهذه العيادة
                                </div>
                            ) : (
                                <select
                                    value={form.user_id}
                                    onChange={(e) => setForm({ ...form, user_id: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-amber-500 outline-none font-bold"
                                >
                                    <option value="">اختر المستخدم</option>
                                    {users.map(u => (
                                        <option key={u.id} value={u.id}>
                                            {u.username || u.email || `مستخدم #${u.id}`} - {u.role}
                                            {!u.is_active && ' [معطل]'}
                                        </option>
                                    ))}
                                </select>
                            )}
                        </div>
                    )}
                    <div>
                        <label className="block text-sm font-bold text-slate-500 mb-1.5">كلمة المرور الجديدة</label>
                        <input
                            type="text"
                            value={form.new_password}
                            onChange={(e) => setForm({ ...form, new_password: e.target.value })}
                            placeholder="أدخل كلمة المرور الجديدة (6 أحرف على الأقل)"
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:ring-2 focus:ring-amber-500 outline-none font-bold"
                            disabled={users.length === 0}
                        />
                        <p className="text-xs text-slate-400 mt-2">💡 سيتم إلغاء قفل الحساب وتفعيله تلقائياً</p>
                    </div>
                    <button
                        onClick={handleSubmit}
                        disabled={users.length === 0 || submitting}
                        className={`w-full py-4 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg text-lg transition-all ${users.length === 0 || submitting
                            ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                            : 'bg-amber-500 hover:bg-amber-600 text-white shadow-amber-500/20 hover:scale-[1.02]'
                            }`}
                    >
                        <Key size={20} />
                        {submitting ? 'جاري التنفيذ...' : 'إعادة تعيين كلمة المرور'}
                    </button>
                </div>
            </div>
        </div>
    );
}
