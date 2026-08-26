import { useState } from 'react';
import { Search, Shield, ShieldOff, User, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export default function UsersManager({ users = [], onSearch, onToggleStatus, loading = false }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [searchTerm, setSearchTerm] = useState('');

    const handleSearch = (e) => {
        e.preventDefault();
        onSearch(searchTerm);
    };

    const getRoleBadge = (role) => {
        const normalized = String(role || '').toLowerCase();
        let label = role;
        let colorClass = 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';

        if (normalized === 'super_admin') {
            label = t('roles.super_admin', 'مدير النظام العام');
            colorClass = 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800';
        } else if (normalized === 'admin') {
            label = t('roles.admin', 'مدير عيادة');
            colorClass = 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border-blue-200 dark:border-blue-800';
        } else if (normalized === 'doctor') {
            label = t('roles.doctor', 'طبيب');
            colorClass = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800';
        } else if (normalized === 'receptionist') {
            label = t('roles.receptionist', 'موظف استقبال');
            colorClass = 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border-amber-200 dark:border-amber-800';
        } else if (normalized === 'accountant') {
            label = t('roles.accountant', 'محاسب');
            colorClass = 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300 border-purple-200 dark:border-purple-800';
        }

        return (
            <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${colorClass}`}>
                {label}
            </span>
        );
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-500" dir={isRtl ? 'rtl' : 'ltr'}>
            {/* Search Header */}
            <div className="flex flex-col md:flex-row justify-between items-center gap-4 bg-white dark:bg-slate-900 p-4 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800">
                <form onSubmit={handleSearch} className="flex items-center gap-2 w-full md:w-1/2 bg-slate-50 dark:bg-slate-800 p-2 rounded-xl border border-slate-200 dark:border-slate-700 focus-within:border-indigo-500 transition-all">
                    <Search className="text-slate-400 shrink-0 ms-2" size={18} />
                    <input
                        type="text"
                        placeholder={t('super_admin.users.search_placeholder', 'البحث بالاسم أو البريد الإلكتروني...')}
                        className="bg-transparent border-none outline-none w-full font-bold text-slate-700 dark:text-slate-200 placeholder-slate-400 text-start text-sm"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                    <button 
                        type="submit" 
                        disabled={loading}
                        className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 shrink-0 cursor-pointer"
                    >
                        {loading && <Loader2 size={14} className="animate-spin" />}
                        <span>{loading ? t('common.searching', 'جاري البحث...') : t('super_admin.users.search_btn', 'بحث')}</span>
                    </button>
                </form>
            </div>

            {/* Users Table */}
            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                <div className="overflow-x-auto min-h-[280px]">
                    <table className="w-full text-start">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-xs font-bold uppercase tracking-wider text-start">
                                <th className="p-4 text-start">{t('super_admin.users.user_col', 'المستخدم')}</th>
                                <th className="p-4 text-start">{t('super_admin.users.role_col', 'الدور والصلاحية')}</th>
                                <th className="p-4 text-start">{t('super_admin.users.tenant_col', 'العيادة')}</th>
                                <th className="p-4 text-center">{t('super_admin.users.status_col', 'الحالة')}</th>
                                <th className="p-4 text-center">{t('super_admin.users.actions_col', 'الإجراءات')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {users.map((u) => (
                                <tr key={u.id} className={`transition-colors ${!u.is_active ? 'bg-slate-50/50 dark:bg-slate-800/20' : 'hover:bg-slate-50/50 dark:hover:bg-slate-800/50'}`}>
                                    <td className="p-4">
                                        <div className="flex items-center gap-3">
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold shrink-0 ${!u.is_active ? 'bg-slate-200 text-slate-500' : 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/50 dark:text-indigo-400'}`}>
                                                <User size={18} />
                                            </div>
                                            <div className="text-start">
                                                <div className="font-bold text-slate-800 dark:text-slate-200 text-sm">{u.username || u.name || 'User'}</div>
                                                <div className="text-xs text-slate-400 font-medium" dir="ltr">{u.email || '—'}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="p-4 text-start">
                                        {getRoleBadge(u.role)}
                                    </td>
                                    <td className="p-4 font-bold text-slate-700 dark:text-slate-300 text-sm text-start">
                                        {u.tenant_name || (u.tenant_id ? `عيادة #${u.tenant_id}` : t('super_admin.users.system', 'النظام العام'))}
                                    </td>
                                    <td className="p-4 text-center">
                                        <span className={`px-3 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1.5 ${u.is_active
                                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                                            : 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400'
                                            }`}>
                                            <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                                            {u.is_active ? t('super_admin.users.active', 'نشط') : t('super_admin.users.inactive', 'معطل')}
                                        </span>
                                    </td>
                                    <td className="p-4 text-center">
                                        <button
                                            type="button"
                                            onClick={() => onToggleStatus(u.id, u.is_active)}
                                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${u.is_active
                                                ? 'bg-rose-50 hover:bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400'
                                                : 'bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
                                                }`}
                                            title={u.is_active ? t('super_admin.users.deactivate_title', 'تعطيل الحساب') : t('super_admin.users.activate_title', 'تفعيل الحساب')}
                                        >
                                            {u.is_active ? <ShieldOff size={15} /> : <Shield size={15} />}
                                            <span>{u.is_active ? t('super_admin.users.deactivate', 'تعطيل') : t('super_admin.users.activate', 'تفعيل')}</span>
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {!loading && users.length === 0 && (
                                <tr>
                                    <td colSpan="5" className="p-12 text-center text-slate-400 font-bold">
                                        {searchTerm ? t('super_admin.users.no_results', 'لم يتم العثور على مستخدمين يطابقون البحث') : t('super_admin.users.search_instruction', 'لا يوجد مستخدمون لعرضهم')}
                                    </td>
                                </tr>
                            )}
                            {loading && users.length === 0 && (
                                <tr>
                                    <td colSpan="5" className="p-12 text-center text-slate-400 font-bold">
                                        <Loader2 className="animate-spin mx-auto mb-2 text-indigo-500" size={24} />
                                        <span>{t('common.loading', 'جاري تحميل المستخدمين...')}</span>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
