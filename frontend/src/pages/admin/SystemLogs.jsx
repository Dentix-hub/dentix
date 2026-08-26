import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '@/api';
import { Card, Button, DataTable, SkeletonBox, Modal, ConfirmDialog, IconButton, toast } from '@/shared/ui';
import { AlertTriangle, RefreshCw, Smartphone, Server, Trash2, Copy, Eye, FileSpreadsheet, AlertCircle } from 'lucide-react';

export default function SystemLogs() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [page, setPage] = useState(0);
    const [selectedLog, setSelectedLog] = useState(null);
    const [logToDelete, setLogToDelete] = useState(null);
    const [isClearingAll, setIsClearingAll] = useState(false);
    const limit = 50;
    const queryClient = useQueryClient();

    const { data: logs = [], isLoading, isError, error, refetch } = useQuery({
        queryKey: ['system-logs', page],
        queryFn: async () => {
            const res = await api.get(`/api/v1/admin/system/logs?skip=${page * limit}&limit=${limit}`);
            return Array.isArray(res.data) ? res.data : [];
        },
        keepPreviousData: true
    });

    const deleteMutation = useMutation({
        mutationFn: (id) => api.delete(`/api/v1/admin/system/logs/${id}`),
        onSuccess: () => {
            toast.success(t('super_admin.logs.delete_success') || 'تم حذف الخطأ بنجاح');
            if (logs.length === 1 && page > 0) {
                setPage(p => Math.max(0, p - 1));
            }
            queryClient.invalidateQueries({ queryKey: ['system-logs'] });
            setLogToDelete(null);
        },
        onError: () => toast.error(t('super_admin.logs.delete_failed') || 'فشل في حذف الخطأ')
    });

    const clearAllMutation = useMutation({
        mutationFn: () => api.delete('/api/v1/admin/system/logs/clear'),
        onSuccess: () => {
            toast.success(t('super_admin.logs.clear_success') || 'تم مسح جميع الأخطاء');
            setPage(0);
            queryClient.invalidateQueries({ queryKey: ['system-logs'] });
            setIsClearingAll(false);
        },
        onError: () => toast.error(t('super_admin.logs.clear_failed') || 'فشل في مسح الأخطاء')
    });

    const handleExport = async () => {
        let url = null;
        try {
            const res = await api.get('/api/v1/admin/system/logs/export', { responseType: 'blob' });
            url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `system_logs_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            toast.success(t('super_admin.logs.export_success') || 'تم تصدير السجل بنجاح');
        } catch (err) {
            toast.error(t('super_admin.logs.export_failed') || 'فشل في تصدير البيانات');
        } finally {
            if (url) {
                window.URL.revokeObjectURL(url);
            }
        }
    };

    const handleCopy = async (log) => {
        const text = `Level: ${log.level || 'ERROR'}\nMessage: ${log.message || ''}\nPath: ${log.path || ''}\nStack Trace: ${log.stack_trace || 'N/A'}`;
        try {
            if (navigator?.clipboard?.writeText) {
                await navigator.clipboard.writeText(text);
                toast.success(t('super_admin.logs.copy_success') || 'تم نسخ تفاصيل الخطأ');
            } else {
                throw new Error('Clipboard API unavailable');
            }
        } catch (err) {
            toast.error(t('super_admin.logs.copy_failed') || 'فشل في نسخ التفاصيل');
        }
    };

    const columns = [
        {
            header: t('super_admin.logs.col_level') || 'المستوى',
            accessor: 'level',
            render: (level) => (
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${level === 'ERROR' ? 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400' :
                    level === 'WARNING' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400' :
                        'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400'
                    }`}>
                    {level || 'ERROR'}
                </span>
            )
        },
        {
            header: t('super_admin.logs.col_source') || 'المصدر',
            accessor: 'source',
            render: (source) => (
                <div className="flex items-center gap-2">
                    {source === 'BACKEND' ? <Server size={14} className="text-indigo-500" /> : <Smartphone size={14} className="text-emerald-500" />}
                    <span className="text-xs font-semibold">{source || 'BACKEND'}</span>
                </div>
            )
        },
        {
            header: t('super_admin.logs.col_message') || 'الرسالة',
            accessor: 'message',
            render: (msg) => <span className="font-mono text-xs text-red-600 dark:text-red-400 line-clamp-1" title={msg}>{msg || '—'}</span>
        },
        {
            header: t('super_admin.logs.col_path') || 'المسار',
            accessor: 'path',
            render: (path) => <span className="text-xs font-mono text-slate-500 dark:text-slate-400">{path || '—'}</span>
        },
        {
            header: t('super_admin.logs.col_date') || 'التاريخ',
            accessor: 'created_at',
            render: (date) => <span className="text-xs font-medium">{date ? new Date(date).toLocaleString(i18n.language) : '—'}</span>
        },
        {
            header: t('super_admin.logs.col_actions') || 'إجراءات',
            accessor: 'id',
            render: (_, log) => (
                <div className="flex items-center gap-1">
                    <IconButton
                        icon={<Eye size={14} />}
                        variant="ghost"
                        color="blue"
                        title={t('super_admin.logs.action_view') || 'عرض التفاصيل'}
                        aria-label={`${t('super_admin.logs.action_view') || 'عرض التفاصيل'} ${log.id}`}
                        onClick={() => setSelectedLog(log)}
                    />
                    <IconButton
                        icon={<Copy size={14} />}
                        variant="ghost"
                        color="gray"
                        title={t('super_admin.logs.action_copy') || 'نسخ'}
                        aria-label={`${t('super_admin.logs.action_copy') || 'نسخ'} ${log.id}`}
                        onClick={() => handleCopy(log)}
                    />
                    <IconButton
                        icon={<Trash2 size={14} />}
                        variant="ghost"
                        color="red"
                        title={t('super_admin.logs.action_delete') || 'حذف'}
                        aria-label={`${t('super_admin.logs.action_delete') || 'حذف'} ${log.id}`}
                        onClick={() => setLogToDelete(log.id)}
                    />
                </div>
            )
        }
    ];

    return (
        <div className="space-y-6" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="text-start">
                    <h1 className="text-2xl font-bold flex items-center gap-2 text-slate-800 dark:text-white">
                        <AlertTriangle className="text-red-500" />
                        {t('super_admin.logs.title') || 'سجل أخطاء النظام'}
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 text-sm">
                        {t('super_admin.logs.subtitle') || 'مراقبة الأخطاء التقنية (Backend & Frontend)'}
                    </p>
                </div>
                <div className="flex flex-wrap gap-2 w-full md:w-auto">
                    <Button variant="outline" onClick={handleExport} className="gap-2 cursor-pointer">
                        <FileSpreadsheet size={18} />
                        {t('super_admin.logs.export_csv') || 'تصدير CSV'}
                    </Button>
                    <Button variant="outline" color="red" onClick={() => setIsClearingAll(true)} className="gap-2 cursor-pointer text-red-600 border-red-200 hover:bg-red-50 dark:hover:bg-red-950/20">
                        <Trash2 size={18} />
                        {t('super_admin.logs.clear_all') || 'مسح الكل'}
                    </Button>
                    <Button variant="outline" onClick={() => refetch()} disabled={isLoading} className="gap-2 cursor-pointer">
                        <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
                        {t('common.refresh') || 'تحديث'}
                    </Button>
                </div>
            </div>

            <Card>
                {isLoading ? (
                    <div className="space-y-4 p-4">
                        <SkeletonBox height="3rem" />
                        <SkeletonBox height="3rem" />
                        <SkeletonBox height="3rem" />
                    </div>
                ) : isError ? (
                    <div className="p-12 text-center text-rose-500 space-y-3">
                        <AlertCircle size={40} className="mx-auto" />
                        <p className="font-bold">{error?.message || t('super_admin.logs.fetch_error') || 'فشل في تحميل سجل الأخطاء'}</p>
                        <Button variant="outline" onClick={() => refetch()} className="gap-2 mx-auto">
                            <RefreshCw size={16} />
                            {t('common.retry') || 'إعادة المحاولة'}
                        </Button>
                    </div>
                ) : (
                    <DataTable
                        data={logs}
                        columns={columns}
                        emptyMessage={t('super_admin.logs.empty_msg') || 'لا توجد أخطاء مسجلة، النظام يعمل بكفاءة! 🎉'}
                    />
                )}
                {!isError && (
                    <div className="p-4 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center">
                        <Button
                            variant="ghost"
                            disabled={page === 0}
                            onClick={() => setPage(p => Math.max(0, p - 1))}
                        >
                            {t('common.previous') || 'السابق'}
                        </Button>
                        <span className="text-sm font-mono font-bold text-slate-600 dark:text-slate-400">
                            {t('common.page') || 'صفحة'} {page + 1}
                        </span>
                        <Button
                            variant="ghost"
                            disabled={logs.length < limit}
                            onClick={() => setPage(p => p + 1)}
                        >
                            {t('common.next') || 'التالي'}
                        </Button>
                    </div>
                )}
            </Card>

            {/* Error Detail Modal */}
            <Modal
                isOpen={!!selectedLog}
                onClose={() => setSelectedLog(null)}
                title={t('super_admin.logs.detail_title') || 'تفاصيل الخطأ'}
                size="xl"
            >
                {selectedLog && (
                    <div className="space-y-4 p-4 text-start" dir={isRtl ? 'rtl' : 'ltr'}>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs text-slate-500 dark:text-slate-400 block">{t('super_admin.logs.col_level') || 'المستوى'}</label>
                                <span className="font-bold text-slate-800 dark:text-white">{selectedLog.level || 'ERROR'}</span>
                            </div>
                            <div>
                                <label className="text-xs text-slate-500 dark:text-slate-400 block">{t('super_admin.logs.col_source') || 'المصدر'}</label>
                                <span className="font-bold text-slate-800 dark:text-white">{selectedLog.source || 'BACKEND'}</span>
                            </div>
                            <div className="col-span-2">
                                <label className="text-xs text-slate-500 dark:text-slate-400 block mb-1">{t('super_admin.logs.col_path') || 'المسار'}</label>
                                <code className="text-xs bg-slate-100 dark:bg-slate-800 p-1.5 rounded font-mono text-slate-700 dark:text-slate-300 block overflow-x-auto">
                                    {selectedLog.path || '—'}
                                </code>
                            </div>
                        </div>
                        <div>
                            <label className="text-xs text-slate-500 dark:text-slate-400 block mb-1">{t('super_admin.logs.col_message') || 'الرسالة'}</label>
                            <div className="p-3 bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 rounded-xl border border-red-100 dark:border-red-900/40 font-mono text-sm">
                                {selectedLog.message || '—'}
                            </div>
                        </div>
                        {selectedLog.stack_trace && (
                            <div>
                                <label className="text-xs text-slate-500 dark:text-slate-400 block mb-1">Stack Trace</label>
                                <pre className="p-3 bg-slate-900 text-slate-100 rounded-xl text-xs overflow-auto max-h-[400px] font-mono whitespace-pre-wrap" dir="ltr">
                                    {selectedLog.stack_trace}
                                </pre>
                            </div>
                        )}
                        <div className="flex justify-end pt-4">
                            <Button onClick={() => handleCopy(selectedLog)} className="gap-2 cursor-pointer">
                                <Copy size={16} />
                                {t('super_admin.logs.copy_details') || 'نسخ التفاصيل'}
                            </Button>
                        </div>
                    </div>
                )}
            </Modal>

            {/* Delete Confirmation */}
            <ConfirmDialog
                isOpen={!!logToDelete}
                onClose={() => setLogToDelete(null)}
                onConfirm={() => deleteMutation.mutate(logToDelete)}
                title={t('super_admin.logs.delete_title') || 'حذف الخطأ'}
                message={t('super_admin.logs.delete_confirm_msg') || 'هل أنت متأكد من رغبتك في حذف هذا الخطأ من السجل؟'}
                confirmText={t('common.delete') || 'حذف'}
                cancelText={t('common.cancel') || 'إلغاء'}
                variant="danger"
                isLoading={deleteMutation.isLoading}
            />

            {/* Clear All Confirmation */}
            <ConfirmDialog
                isOpen={isClearingAll}
                onClose={() => setIsClearingAll(false)}
                onConfirm={() => clearAllMutation.mutate()}
                title={t('super_admin.logs.clear_title') || 'مسح جميع الأخطاء'}
                message={t('super_admin.logs.clear_confirm_msg') || 'هل أنت متأكد من رغبتك في مسح سجل الأخطاء بالكامل؟ لا يمكن التراجع عن هذا الإجراء.'}
                confirmText={t('super_admin.logs.clear_all') || 'مسح الكل'}
                cancelText={t('common.cancel') || 'إلغاء'}
                variant="danger"
                isLoading={clearAllMutation.isLoading}
            />
        </div>
    );
}
