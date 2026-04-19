
import React, { useState } from 'react';
import { Search, Power, Edit, MoreVertical, Shield, ShieldOff, User } from 'lucide-react';

const UsersManager = ({ users, onSearch, onToggleStatus, loading }) => {
    const [searchTerm, setSearchTerm] = useState('');

    const handleSearch = (e) => {
        e.preventDefault();
        onSearch(searchTerm);
    };

    return (
        <div className="space-y-6 animate-fade-in-up">
            {/* Search Header */}
            <div className="flex flex-col md:flex-row justify-between items-center gap-4 bg-white dark:bg-slate-900 p-4 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800">
                <form onSubmit={handleSearch} className="flex items-center gap-2 w-full md:w-1/2 bg-slate-50 dark:bg-slate-800 p-2 px-4 rounded-xl border-2 border-transparent focus-within:border-indigo-500 transition-all">
                    <Search className="text-slate-400" size={20} />
                    <input
                        type="text"
                        placeholder="بحث عن مستخدم (اسم، بريد، هاتف)..."
                        className="bg-transparent border-none outline-none w-full font-bold text-slate-700 dark:text-slate-200 placeholder-slate-400"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                    <button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-1.5 rounded-lg text-sm font-bold transition-all disabled:opacity-50" disabled={loading}>
                        بحث
                    </button>
                </form>
            </div>

            {/* Users Table */}
            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                <div className="overflow-x-auto min-h-[300px]">
                    <table className="w-full text-right">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-sm font-bold uppercase tracking-wider">
                                <th className="p-4">المستخدم</th>
                                <th className="p-4">الدور</th>
                                <th className="p-4">العيادة</th>
                                <th className="p-4">الحالة</th>
                                <th className="p-4 text-center">الإجراءات</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {users.map((user) => (
                                <tr key={user.id} className={`transition-colors ${!user.is_active ? 'bg-slate-50 dark:bg-slate-800/20' : 'hover:bg-slate-50/50 dark:hover:bg-slate-800/50'}`}>
                                    <td className="p-4">
                                        <div className="flex items-center gap-3">
                                            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${!user.is_active ? 'bg-slate-200 text-slate-500' : 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/50 dark:text-indigo-400'}`}>
                                                <User size={18} />
                                            </div>
                                            <div>
                                                <div className="font-bold text-slate-800 dark:text-slate-200">{user.username}</div>
                                                <div className="text-xs text-slate-500">{user.email || 'No Email'}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="p-4">
                                        <span className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs font-bold text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                                            {user.role}
                                        </span>
                                    </td>
                                    <td className="p-4 font-bold text-slate-700 dark:text-slate-300">
                                        {user.tenant_name || 'System'}
                                    </td>
                                    <td className="p-4">
                                        <span className={`px-3 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1.5 ${user.is_active
                                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                                            : 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400'
                                            }`}>
                                            <span className={`w-1.5 h-1.5 rounded-full ${user.is_active ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                                            {user.is_active ? 'نشط' : 'معطل'}
                                        </span>
                                    </td>
                                    <td className="p-4 text-center">
                                        <button
                                            onClick={() => onToggleStatus(user.id, user.is_active)}
                                            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${user.is_active
                                                ? 'bg-rose-100 hover:bg-rose-200 text-rose-600'
                                                : 'bg-emerald-100 hover:bg-emerald-200 text-emerald-600'
                                                }`}
                                            title={user.is_active ? 'تعطيل الحساب' : 'تفعيل الحساب'}
                                        >
                                            {user.is_active ? <ShieldOff size={16} /> : <Shield size={16} />}
                                            {user.is_active ? 'تعطيل' : 'تفعيل'}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {!loading && users.length === 0 && (
                                <tr>
                                    <td colSpan="5" className="p-8 text-center text-slate-500">
                                        {searchTerm ? 'لا توجد نتائج بحث' : 'قم بالبحث لعرض المستخدمين'}
                                    </td>
                                </tr>
                            )}
                            {loading && (
                                <tr>
                                    <td colSpan="5" className="p-8 text-center text-slate-500 animate-pulse">
                                        جاري التحميل...
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default UsersManager;

