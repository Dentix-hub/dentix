import { CheckCircle2, AlertCircle, Clock } from 'lucide-react';
const ActiveSubscriptions = ({ tenants, plans, getDaysRemaining }) => {
    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-right">
                    <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-sm font-bold uppercase tracking-wider">
                        <tr>
                            <th className="p-6">العيادة</th>
                            <th className="p-6">الخطة الحالية</th>
                            <th className="p-6">السعر</th>
                            <th className="p-6">المدة المتبقية</th>
                            <th className="p-6">تاريخ الانتهاء</th>
                            <th className="p-6">الحالة</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {(Array.isArray(tenants) ? tenants : []).map((tenant) => {
                            const daysLeft = getDaysRemaining(tenant.subscription_end_date);
                            const plan = plans.find(p => p.id === tenant.plan_id);
                            const isActive = tenant.is_active && (daysLeft === null || daysLeft > 0);
                            return (
                                <tr key={tenant.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                                    <td className="p-6">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold">
                                                {tenant.name.charAt(0)}
                                            </div>
                                            <span className="font-bold text-slate-800 dark:text-slate-200">{tenant.name}</span>
                                        </div>
                                    </td>
                                    <td className="p-6">
                                        <span className="font-medium text-slate-600 dark:text-slate-400">
                                            {plan?.display_name_ar || 'تجريبية'}
                                        </span>
                                    </td>
                                    <td className="p-6">
                                        <span className="font-black text-emerald-600 dark:text-emerald-400">
                                            {plan?.price?.toLocaleString() || 0} ج.م
                                        </span>
                                    </td>
                                    <td className="p-6">
                                        {daysLeft !== null ? (
                                            <div className={`flex items-center gap-2 font-bold ${daysLeft < 7 ? 'text-rose-500' : 'text-slate-600 dark:text-slate-400'}`}>
                                                <Clock size={16} />
                                                {daysLeft} يوم
                                            </div>
                                        ) : (
                                            <span className="text-slate-400 text-2xl">∞</span>
                                        )}
                                    </td>
                                    <td className="p-6 font-medium text-slate-600 dark:text-slate-400">
                                        {tenant.subscription_end_date ? new Date(tenant.subscription_end_date).toLocaleDateString('ar-EG') : '-'}
                                    </td>
                                    <td className="p-6">
                                        <span className={`px-4 py-1.5 rounded-full text-xs font-bold inline-flex items-center gap-1.5 ${isActive
                                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                                            : 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400'}`}>
                                            {isActive ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                                            {isActive ? 'نشط' : 'منتهي'}
                                        </span>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
export default ActiveSubscriptions;