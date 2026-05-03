
import React, { useState } from 'react';
import { User, Activity, Calendar, Search, RotateCcw, Filter } from 'lucide-react';

const AuditLogViewer = ({ logs, tenants = [], users = [], onFilter }) => {
    const [filters, setFilters] = useState({
        tenant_id: '',
        user_id: '',
        action: '',
        start_date: '',
        end_date: ''
    });

    // Action color mapping
    const getActionColor = (action) => {
        switch (action) {
            case 'create': return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
            case 'update': return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
            case 'delete':
            case 'archive': return 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400';
            case 'restore': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
            default: return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400';
        }
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleString('ar-EG');
    };

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value }));
    };

    const handleSearch = () => {
        if (onFilter) {
            onFilter(filters);
        }
    };

    const handleReset = () => {
        const emptyFilters = {
            tenant_id: '',
            user_id: '',
            action: '',
            start_date: '',
            end_date: ''
        };
        setFilters(emptyFilters);
        if (onFilter) {
            onFilter(emptyFilters);
        }
    };

    const actionOptions = [
        { value: '', label: 'الكل' },
        { value: 'create', label: 'إنشاء' },
        { value: 'update', label: 'تحديث' },
        { value: 'delete', label: 'حذف' },
        { value: 'archive', label: 'أرشفة' },
        { value: 'restore', label: 'استعادة' }
    ];

    return (
        <div className="space-y-4 animate-fade-in-up">
            <h2 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <Activity className="text-indigo-500" />
                سجل نشاط النظام (Audit Logs)
            </h2>

            {/* Filters Section */}
            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 p-6">
                <div className="flex items-center gap-2 mb-4 text-slate-600 dark:text-slate-400">
                    <Filter size={18} />
                    <span className="font-bold">فلاتر البحث</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    {/* Tenant Filter */}
                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1.5">العيادة</label>
                        <select
                            value={filters.tenant_id}
                            onChange={(e) => handleFilterChange('tenant_id', e.target.value)}
                            className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-medium focus:ring-2 focus:ring-indigo-500 outline-none"
                        >
                            <option value="">كل العيادات</option>
                            {(tenants || []).map(t => (
                                <option key={t.id} value={t.id}>{t.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Action Filter */}
                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1.5">نوع الإجراء</label>
                        <select
                            value={filters.action}
                            onChange={(e) => handleFilterChange('action', e.target.value)}
                            className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-medium focus:ring-2 focus:ring-indigo-500 outline-none"
                        >
                            {actionOptions.map(opt => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                    </div>

                    {/* Start Date */}
                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1.5">من تاريخ</label>
                        <input
                            type="date"
                            value={filters.start_date}
                            onChange={(e) => handleFilterChange('start_date', e.target.value)}
                            className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-medium focus:ring-2 focus:ring-indigo-500 outline-none"
                        />
                    </div>

                    {/* End Date */}
                    <div>
                        <label className="block text-xs font-bold text-slate-500 mb-1.5">إلى تاريخ</label>
                        <input
                            type="date"
                            value={filters.end_date}
                            onChange={(e) => handleFilterChange('end_date', e.target.value)}
                            className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-medium focus:ring-2 focus:ring-indigo-500 outline-none"
                        />
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-end gap-2">
                        <button
                            onClick={handleSearch}
                            className="flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-colors"
                        >
                            <Search size={16} />
                            بحث
                        </button>
                        <button
                            onClick={handleReset}
                            className="px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400 rounded-xl text-sm font-bold transition-colors"
                            title="إعادة تعيين"
                        >
                            <RotateCcw size={16} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Logs Table */}
            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-right">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-sm font-bold uppercase tracking-wider">
                                <th className="p-4">الوقت</th>
                                <th className="p-4">المسؤول</th>
                                <th className="p-4">الإجراء</th>
                                <th className="p-4">الهدف</th>
                                <th className="p-4">التفاصيل</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {logs.map((log) => (
                                <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                                    <td className="p-4 text-sm text-slate-500 font-bold" dir="ltr">
                                        {formatDate(log.created_at)}
                                    </td>
                                    <td className="p-4">
                                        <div className="flex items-center gap-2 font-bold text-slate-700 dark:text-slate-300">
                                            <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                                                <User size={14} />
                                            </div>
                                            {log.performed_by_username}
                                        </div>
                                    </td>
                                    <td className="p-4">
                                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${getActionColor(log.action)}`}>
                                            {log.action?.toUpperCase()}
                                        </span>
                                    </td>
                                    <td className="p-4 text-indigo-600 dark:text-indigo-400 font-bold">
                                        {log.entity_type} #{log.entity_id}
                                    </td>
                                    <td className="p-4 text-slate-600 dark:text-slate-400 text-sm">
                                        {log.details}
                                    </td>
                                </tr>
                            ))}
                            {logs.length === 0 && (
                                <tr>
                                    <td colSpan="5" className="p-8 text-center text-slate-500">لا يوجد سجلات حتى الآن</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default AuditLogViewer;

