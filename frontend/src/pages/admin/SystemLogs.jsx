import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api';
import { Card, Button, DataTable, Skeleton } from '@/shared/ui';
import { AlertTriangle, RefreshCw, Smartphone, Server } from 'lucide-react';
export default function SystemLogs() {
    const [page, setPage] = useState(0);
    const limit = 50;
    const { data: logs = [], isLoading, refetch } = useQuery({
        queryKey: ['system-logs', page],
        queryFn: async () => {
            const res = await api.get(`/admin/system/logs?skip=${page * limit}&limit=${limit}`);
            // Ensure we always return an array, even if API returns unexpected data
            return Array.isArray(res.data) ? res.data : [];
        },
        keepPreviousData: true
    });
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
                <Button variant="outline" onClick={() => refetch()} disabled={isLoading}>
                    <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
                    تحديث
                </Button>
            </div>
            <Card>
                {isLoading ? (
                    <div className="space-y-4">
                        <Skeleton.Box height="3rem" />
                        <Skeleton.Box height="3rem" />
                        <Skeleton.Box height="3rem" />
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
        </div>
    );
}
