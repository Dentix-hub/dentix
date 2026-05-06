
import React, { useState, useEffect } from 'react';
import { User, Activity, Calendar, Search, RotateCcw, Filter, Download, ChevronRight, ChevronLeft, Eye, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { DateTimePicker } from '@/shared/ui';
import { api } from '@/api';

const AuditLogViewer = ({ tenants = [] }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [data, setData] = useState({ logs: [], total: 0, pages: 0, current_page: 1 });
    const [loading, setLoading] = useState(false);
    const [filters, setFilters] = useState({
        tenant_id: '',
        user_id: '',
        action: '',
        start_date: '',
        end_date: '',
        page: 1,
        limit: 20
    });

    const [selectedLog, setSelectedLog] = useState(null);

    useEffect(() => {
        fetchLogs();
    }, [filters.page, filters.limit]);

    const fetchLogs = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            Object.entries(filters).forEach(([key, val]) => {
                if (val) params.append(key, val);
            });
            const res = await api.get(`/api/v1/admin/system/audit-logs?${params.toString()}`);
            const responseData = res.data.data || res.data;
            setData({
                logs: Array.isArray(responseData.logs) ? responseData.logs : [],
                total: responseData.total || 0,
                pages: responseData.pages || 0,
                current_page: responseData.current_page || 1
            });
        } catch (err) {
            console.error('Fetch logs error:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async () => {
        try {
            const params = new URLSearchParams();
            Object.entries(filters).forEach(([key, val]) => {
                if (val && key !== 'page' && key !== 'limit') params.append(key, val);
            });
            const res = await api.get(`/api/v1/admin/system/audit-logs/export?${params.toString()}`, {
                responseType: 'blob'
            });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `audit_logs_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (err) {
            alert(t('super_admin.audit.export_error'));
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value, page: 1 }));
    };

    const handleReset = () => {
        setFilters({
            tenant_id: '',
            user_id: '',
            action: '',
            start_date: '',
            end_date: '',
            page: 1,
            limit: 20
        });
        setTimeout(fetchLogs, 0);
    };

    const getActionColor = (action) => {
        switch (action) {
            case 'create': return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
            case 'update': return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
            case 'delete': return 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400';
            default: return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400';
        }
    };

    const formatJSON = (val) => {
        if (!val) return null;
        try {
            return JSON.stringify(val, null, 2);
        } catch {
            return val;
        }
    };

    return (
        <div className="space-y-6 animate-fade-in-up pb-10">
            <div className={`flex flex-col md:flex-row justify-between items-start md:items-center gap-4 ${isRtl ? 'md:flex-row-reverse' : ''}`}>
                <h2 className={`text-2xl font-black text-slate-800 dark:text-white flex items-center gap-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
                    <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 rounded-xl">
                        <Activity size={24} />
                    </div>
                    {t('super_admin.audit.title')}
                </h2>
                <button
                    onClick={handleExport}
                    className={`flex items-center gap-2 px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-white rounded-2xl font-black text-sm shadow-lg shadow-emerald-500/20 transition-all active:scale-95 ${isRtl ? 'flex-row-reverse' : ''}`}
                >
                    <Download size={18} />
                    {t('super_admin.audit.export_csv')}
                </button>
            </div>

            {/* Filters */}
            <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] shadow-sm border border-slate-100 dark:border-slate-800 p-8">
                <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 ${isRtl ? 'text-right' : 'text-left'}`}>
                    <div>
                        <label className="block text-xs font-black text-slate-400 mb-2 uppercase tracking-wider">{t('super_admin.audit.all_tenants')}</label>
                        <select
                            value={filters.tenant_id}
                            onChange={(e) => handleFilterChange('tenant_id', e.target.value)}
                            className="w-full px-4 py-3 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800 text-sm font-bold outline-none focus:ring-4 focus:ring-indigo-500/10 transition-all"
                            dir={isRtl ? 'rtl' : 'ltr'}
                        >
                            <option value="">{t('super_admin.audit.all_tenants')}</option>
                            {tenants.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="block text-xs font-black text-slate-400 mb-2 uppercase tracking-wider">{t('super_admin.audit.action_type')}</label>
                        <select
                            value={filters.action}
                            onChange={(e) => handleFilterChange('action', e.target.value)}
                            className="w-full px-4 py-3 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800 text-sm font-bold outline-none focus:ring-4 focus:ring-indigo-500/10 transition-all"
                            dir={isRtl ? 'rtl' : 'ltr'}
                        >
                            <option value="">{t('super_admin.audit.all')}</option>
                            <option value="create">{t('super_admin.audit.create')}</option>
                            <option value="update">{t('super_admin.audit.update')}</option>
                            <option value="delete">{t('super_admin.audit.delete')}</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-xs font-black text-slate-400 mb-2 uppercase tracking-wider">{t('super_admin.audit.from_date')}</label>
                        <DateTimePicker
                            mode="date"
                            value={filters.start_date}
                            onChange={(e) => handleFilterChange('start_date', e.target.value)}
                        />
                    </div>
                    <div className={`flex items-end gap-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className="flex-1">
                            <label className="block text-xs font-black text-slate-400 mb-2 uppercase tracking-wider">{t('super_admin.audit.to_date')}</label>
                            <DateTimePicker
                                mode="date"
                                value={filters.end_date}
                                onChange={(e) => handleFilterChange('end_date', e.target.value)}
                            />
                        </div>
                        <button
                            onClick={fetchLogs}
                            className="p-3.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl shadow-lg shadow-indigo-500/20 transition-all active:scale-90"
                            title={t('super_admin.audit.search')}
                        >
                            <Search size={20} />
                        </button>
                        <button
                            onClick={handleReset}
                            className="p-3.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 rounded-2xl transition-all"
                            title={t('super_admin.audit.reset')}
                        >
                            <RotateCcw size={20} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Table */}
            <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden relative">
                {loading && (
                    <div className="absolute inset-0 bg-white/50 dark:bg-slate-900/50 backdrop-blur-[2px] z-10 flex items-center justify-center">
                        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                )}
                
                <div className="overflow-x-auto">
                    <table className="w-full border-collapse" dir={isRtl ? 'rtl' : 'ltr'}>
                        <thead>
                            <tr className={`bg-slate-50/50 dark:bg-slate-800/30 text-slate-400 text-xs font-black uppercase tracking-widest ${isRtl ? 'text-right' : 'text-left'}`}>
                                <th className="p-6">{t('super_admin.audit.time')}</th>
                                <th className="p-6">{t('super_admin.audit.admin')}</th>
                                <th className="p-6">{t('super_admin.audit.all_tenants')}</th>
                                <th className="p-6">{t('super_admin.audit.action')}</th>
                                <th className="p-6">{t('super_admin.audit.target')}</th>
                                <th className="p-6"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {data.logs.map(log => (
                                <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/20 transition-colors group">
                                    <td className="p-6 text-sm font-bold text-slate-500" dir="ltr">
                                        {new Date(log.created_at).toLocaleString(isRtl ? 'ar-EG' : 'en-US', { dateStyle: 'medium', timeStyle: 'short' })}
                                    </td>
                                    <td className="p-6">
                                        <div className={`flex items-center gap-3 ${isRtl ? 'flex-row-reverse' : ''}`}>
                                            <div className="w-9 h-9 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500 group-hover:scale-110 transition-transform">
                                                <User size={16} />
                                            </div>
                                            <div className={isRtl ? 'text-right' : 'text-left'}>
                                                <p className="text-sm font-black text-slate-800 dark:text-white">{log.performed_by_username || 'System'}</p>
                                                <p className="text-[10px] text-slate-400 font-bold">{t('super_admin.audit.ip')}: {log.ip_address || 'Internal'}</p>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="p-6">
                                        <span className="text-xs font-bold bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded-full text-slate-600 dark:text-slate-400">
                                            {log.tenant_name || 'System Global'}
                                        </span>
                                    </td>
                                    <td className="p-6">
                                        <span className={`px-4 py-1.5 rounded-2xl text-[10px] font-black uppercase tracking-wide shadow-sm ${getActionColor(log.action)}`}>
                                            {log.action}
                                        </span>
                                    </td>
                                    <td className="p-6">
                                        <p className={`text-xs font-black text-indigo-600 dark:text-indigo-400 uppercase tracking-tighter ${isRtl ? 'text-right' : 'text-left'}`}>{log.entity_type}</p>
                                        <p className={`text-[10px] text-slate-400 font-bold mt-0.5 ${isRtl ? 'text-right' : 'text-left'}`}>{t('super_admin.audit.id_label')}: {log.entity_id}</p>
                                    </td>
                                    <td className="p-6">
                                        <button 
                                            onClick={() => setSelectedLog(log)}
                                            className="p-3 bg-slate-50 dark:bg-slate-800 hover:bg-indigo-600 hover:text-white text-slate-500 rounded-2xl transition-all active:scale-90"
                                        >
                                            <Eye size={18} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {data.logs.length === 0 && !loading && (
                                <tr>
                                    <td colSpan="6" className="p-20 text-center">
                                        <Activity size={60} className="mx-auto text-slate-200 mb-4" />
                                        <p className="text-slate-400 font-black text-lg">{t('super_admin.audit.no_results_found')}</p>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                {data.pages > 1 && (
                    <div className={`p-8 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className="text-sm font-bold text-slate-400">
                            {t('super_admin.audit.showing_x_of_y', { count: data.logs.length, total: data.total })}
                        </div>
                        <div className={`flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <button
                                disabled={filters.page === 1}
                                onClick={() => handleFilterChange('page', filters.page - 1)}
                                className="p-3 bg-slate-100 dark:bg-slate-800 rounded-xl disabled:opacity-30 transition-all hover:bg-slate-200"
                            >
                                {isRtl ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
                            </button>
                            {[...Array(data.pages)].map((_, i) => (
                                <button
                                    key={i}
                                    onClick={() => handleFilterChange('page', i + 1)}
                                    className={`w-10 h-10 rounded-xl font-black text-sm transition-all ${filters.page === i + 1 ? 'bg-indigo-600 text-white shadow-lg' : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500'}`}
                                >
                                    {i + 1}
                                </button>
                            ))}
                            <button
                                disabled={filters.page === data.pages}
                                onClick={() => handleFilterChange('page', filters.page + 1)}
                                className="p-3 bg-slate-100 dark:bg-slate-800 rounded-xl disabled:opacity-30 transition-all hover:bg-slate-200"
                            >
                                {isRtl ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Details Modal */}
            {selectedLog && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/60 backdrop-blur-md p-4 animate-in fade-in zoom-in duration-300">
                    <div className="bg-white dark:bg-slate-900 rounded-[3rem] w-full max-w-4xl max-h-[85vh] overflow-hidden shadow-2xl flex flex-col">
                        <div className={`p-8 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <div className={`flex items-center gap-4 ${isRtl ? 'flex-row-reverse text-right' : 'text-left'}`}>
                                <div className={`p-4 rounded-3xl ${getActionColor(selectedLog.action)}`}>
                                    <Activity size={32} />
                                </div>
                                <div>
                                    <h3 className="text-2xl font-black text-slate-800 dark:text-white">{t('super_admin.audit.details_title')}</h3>
                                    <p className="text-slate-500 font-bold">{selectedLog.entity_type} {t('super_admin.audit.id_label')} #{selectedLog.entity_id}</p>
                                </div>
                            </div>
                            <button onClick={() => setSelectedLog(null)} className="p-4 bg-slate-100 dark:bg-slate-800 rounded-2xl hover:bg-rose-50 hover:text-rose-500 transition-all">
                                <X size={24} />
                            </button>
                        </div>

                        <div className={`p-8 overflow-y-auto space-y-8 ${isRtl ? 'text-right' : 'text-left'}`}>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div className="space-y-6">
                                    <h4 className="text-sm font-black text-slate-400 uppercase tracking-widest">{t('super_admin.audit.basic_info')}</h4>
                                    <div className="space-y-4">
                                        <div className={`flex justify-between ${isRtl ? 'flex-row-reverse' : ''}`}>
                                            <span className="font-bold text-slate-500">{t('super_admin.audit.time')}:</span>
                                            <span className="font-mono text-indigo-600 font-bold" dir="ltr">{new Date(selectedLog.created_at).toLocaleString(isRtl ? 'ar-EG' : 'en-US')}</span>
                                        </div>
                                        <div className={`flex justify-between ${isRtl ? 'flex-row-reverse' : ''}`}>
                                            <span className="font-bold text-slate-500">{t('super_admin.audit.admin')}:</span>
                                            <span className="font-black">{selectedLog.performed_by_username}</span>
                                        </div>
                                        <div className={`flex justify-between ${isRtl ? 'flex-row-reverse' : ''}`}>
                                            <span className="font-bold text-slate-500">{t('super_admin.audit.ip')}:</span>
                                            <span className="font-mono text-slate-600" dir="ltr">{selectedLog.ip_address}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="space-y-6">
                                    <h4 className="text-sm font-black text-slate-400 uppercase tracking-widest">{t('super_admin.audit.description')}</h4>
                                    <div className="p-6 bg-slate-50 dark:bg-slate-800 rounded-3xl border border-slate-100 dark:border-slate-700">
                                        <p className="text-slate-700 dark:text-slate-300 font-bold">{selectedLog.details}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Values Comparison (Diff) */}
                            {(selectedLog.old_value || selectedLog.new_value) && (
                                <div className="space-y-6">
                                    <h4 className="text-sm font-black text-slate-400 uppercase tracking-widest">{t('super_admin.audit.data_diff')}</h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <div className="space-y-3">
                                            <p className={`text-xs font-black text-rose-500 bg-rose-50 dark:bg-rose-900/20 px-3 py-1 rounded-full w-fit ${isRtl ? 'mr-0 ml-auto' : ''}`}>{t('super_admin.audit.old_value')}</p>
                                            <pre className="p-6 bg-slate-900 text-emerald-400 rounded-3xl font-mono text-xs overflow-x-auto min-h-[200px]" dir="ltr">
                                                {formatJSON(selectedLog.old_value) || t('super_admin.audit.no_data')}
                                            </pre>
                                        </div>
                                        <div className="space-y-3">
                                            <p className={`text-xs font-black text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 px-3 py-1 rounded-full w-fit ${isRtl ? 'mr-0 ml-auto' : ''}`}>{t('super_admin.audit.new_value')}</p>
                                            <pre className="p-6 bg-slate-900 text-amber-400 rounded-3xl font-mono text-xs overflow-x-auto min-h-[200px]" dir="ltr">
                                                {formatJSON(selectedLog.new_value) || t('super_admin.audit.no_data')}
                                            </pre>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AuditLogViewer;

