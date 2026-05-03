import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api';
import { Card, Button, DataTable, SkeletonBox, Modal, ConfirmDialog, IconButton, toast } from '@/shared/ui';
import { AlertTriangle, RefreshCw, Smartphone, Server, Download, Trash2, Copy, Eye, FileSpreadsheet } from 'lucide-react';

export default function SystemLogs() {
    const [page, setPage] = useState(0);
    const [selectedLog, setSelectedLog] = useState(null);
    const [logToDelete, setLogToDelete] = useState(null);
    const [isClearingAll, setIsClearingAll] = useState(false);
    const limit = 50;
    const queryClient = useQueryClient();

    const { data: logs = [], isLoading, refetch } = useQuery({
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
            toast.success('تم حذف الخطأ بنجاح');
            queryClient.invalidateQueries(['system-logs']);
            setLogToDelete(null);
        },
        onError: () => toast.error('فشل في حذف الخطأ')
    });

    const clearAllMutation = useMutation({
        mutationFn: () => api.delete('/api/v1/admin/system/logs/clear'),
        onSuccess: () => {
            toast.success('تم مسح جميع الأخطاء');
            queryClient.invalidateQueries(['system-logs']);
            setIsClearingAll(false);
        },
        onError: () => toast.error('فشل في مسح الأخطاء')
    });

    const handleExport = async () => {
        try {
            const res = await api.get('/api/v1/admin/system/logs/export', { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([res]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `system_logs_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            toast.error('فشل في تصدير البيانات');
        }
    };

    const handleCopy = (log) => {
        const text = `Level: ${log.level}\nMessage: ${log.message}\nPath: ${log.path}\nStack Trace: ${log.stack_trace || 'N/A'}`;
        navigator.clipboard.writeText(text);
        toast.success('تم نسخ تفاصيل الخطأ');
    };

    const columns = [
        {
            header: 'المستوى',
            accessor: 'level',
            render: (level) => (
                <span className={`px-2 py-1 rounded text-xs font-bold ${level === 'ERROR' ? 'bg-red-100 text-red-700' :
                    level === 'WARNING' ? 'bg-amber-100 text-amber-700' :
                        'bg-blue-100 text-blue-700'
                    }`}>
                    {level}
                </span>
            )
        },
        {
            header: 'المصدر',
            accessor: 'source',
            render: (source) => (
                <div className="flex items-center gap-2">
                    {source === 'BACKEND' ? <Server size={14} /> : <Smartphone size={14} />}
                    <span className="text-xs">{source}</span>
                </div>
            )
        },
        {
            header: 'الرسالة',
            accessor: 'message',
            render: (msg) => <span className="font-mono text-xs text-red-600 line-clamp-1" title={msg}>{msg}</span>
        },
        {
            header: 'المسار',
            accessor: 'path',
            render: (path) => <span className="text-xs font-mono text-slate-500">{path}</span>
        },
        {
            header: 'التاريخ',
            accessor: 'created_at',
            render: (date) => <span className="text-xs">{new Date(date).toLocaleString()}</span>
        },
        {
            header: 'إجراءات',
            accessor: 'id',
            render: (_, log) => (
                <div className="flex items-center gap-1">
                    <IconButton
                        icon={<Eye size={14} />}
                        variant="ghost"
                        color="blue"
                        title="عرض التفاصيل"
                        onClick={() => setSelectedLog(log)}
                    />
                    <IconButton
                        icon={<Copy size={14} />}
                        variant="ghost"
                        color="gray"
                        title="نسخ"
                        onClick={() => handleCopy(log)}
                    />
                    <IconButton
                        icon={<Trash2 size={14} />}
                        variant="ghost"
                        color="red"
                        title="حذف"
                        onClick={() => setLogToDelete(log.id)}
                    />
                </div>
            )
        }
    ];

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <AlertTriangle className="text-red-500" />
                        سجل أخطاء النظام
                    </h1>
                    <p className="text-text-secondary text-sm">مراقبة الأخطاء التقنية (Backend & Frontend)</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={handleExport} className="gap-2">
                        <FileSpreadsheet size={18} />
                        تصدير CSV
                    </Button>
                    <Button variant="outline" color="red" onClick={() => setIsClearingAll(true)} className="gap-2">
                        <Trash2 size={18} />
                        مسح الكل
                    </Button>
                    <Button variant="outline" onClick={() => refetch()} disabled={isLoading} className="gap-2">
                        <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
                        تحديث
                    </Button>
                </div>
            </div>

            <Card>
                {isLoading ? (
                    <div className="space-y-4">
                        <SkeletonBox height="3rem" />
                        <SkeletonBox height="3rem" />
                        <SkeletonBox height="3rem" />
                    </div>
                ) : (
                    <DataTable
                        data={logs}
                        columns={columns}
                        emptyMessage="لا توجد أخطاء مسجلة، النظام يعمل بكفاءة! 🎉"
                    />
                )}
                <div className="p-4 border-t border-border flex justify-between items-center">
                    <Button
                        variant="ghost"
                        disabled={page === 0}
                        onClick={() => setPage(p => Math.max(0, p - 1))}
                    >
                        السابق
                    </Button>
                    <span className="text-sm font-mono">صفحة {page + 1}</span>
                    <Button
                        variant="ghost"
                        disabled={logs.length < limit}
                        onClick={() => setPage(p => p + 1)}
                    >
                        التالي
                    </Button>
                </div>
            </Card>

            {/* Error Detail Modal */}
            <Modal
                isOpen={!!selectedLog}
                onClose={() => setSelectedLog(null)}
                title="تفاصيل الخطأ"
                size="xl"
            >
                {selectedLog && (
                    <div className="space-y-4 p-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs text-slate-500 block">المستوى</label>
                                <span className="font-bold">{selectedLog.level}</span>
                            </div>
                            <div>
                                <label className="text-xs text-slate-500 block">المصدر</label>
                                <span className="font-bold">{selectedLog.source}</span>
                            </div>
                            <div className="col-span-2">
                                <label className="text-xs text-slate-500 block">المسار</label>
                                <code className="text-xs bg-slate-100 p-1 rounded">{selectedLog.path}</code>
                            </div>
                        </div>
                        <div>
                            <label className="text-xs text-slate-500 block">الرسالة</label>
                            <div className="p-3 bg-red-50 text-red-700 rounded border border-red-100 font-mono text-sm">
                                {selectedLog.message}
                            </div>
                        </div>
                        {selectedLog.stack_trace && (
                            <div>
                                <label className="text-xs text-slate-500 block mb-1">Stack Trace</label>
                                <pre className="p-3 bg-slate-900 text-slate-100 rounded text-xs overflow-auto max-h-[400px] font-mono whitespace-pre-wrap">
                                    {selectedLog.stack_trace}
                                </pre>
                            </div>
                        )}
                        <div className="flex justify-end pt-4">
                            <Button onClick={() => handleCopy(selectedLog)} className="gap-2">
                                <Copy size={16} />
                                نسخ التفاصيل
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
                title="حذف الخطأ"
                message="هل أنت متأكد من رغبتك في حذف هذا الخطأ من السجل؟"
                confirmText="حذف"
                cancelText="إلغاء"
                variant="danger"
                isLoading={deleteMutation.isLoading}
            />

            {/* Clear All Confirmation */}
            <ConfirmDialog
                isOpen={isClearingAll}
                onClose={() => setIsClearingAll(false)}
                onConfirm={() => clearAllMutation.mutate()}
                title="مسح جميع الأخطاء"
                message="هل أنت متأكد من رغبتك في مسح سجل الأخطاء بالكامل؟ لا يمكن التراجع عن هذا الإجراء."
                confirmText="مسح الكل"
                cancelText="إلغاء"
                variant="danger"
                isLoading={clearAllMutation.isLoading}
            />
        </div>
    );
}

