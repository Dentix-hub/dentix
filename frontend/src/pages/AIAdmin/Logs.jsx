import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Clock } from 'lucide-react';
import { getAILogs } from '@/api';
export default function AILogs() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const fetchLogs = async (pageNum = 0) => {
        try {
            setLoading(true);
            const res = await getAILogs(pageNum * 20, 20);
            setLogs(res.data);
            setPage(pageNum);
        } catch (err) {
            console.error("Failed to load logs", err);
        } finally {
            setLoading(false);
        }
    };
    useEffect(() => {
        fetchLogs();
    }, []);
    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700" dir="rtl">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-black text-slate-800 dark:text-white">سجل العمليات 📜</h1>
                    <p className="text-slate-500 mt-2">تتبع جميع تفاعلات المساعد الذكي بالتفصيل.</p>
                </div>
                <div className="flex gap-2">
                    <button
                        disabled={page === 0}
                        onClick={() => fetchLogs(page - 1)}
                        className="px-4 py-2 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 disabled:opacity-50"
                    >
                        السابق
                    </button>
                    <button
                        onClick={() => fetchLogs(page + 1)}
                        className="px-4 py-2 rounded-xl bg-primary text-white font-bold"
                    >
                        التالي
                    </button>
                </div>
            </div>
            {/* Logs Table */}
            <div className="bg-white dark:bg-slate-800 rounded-[2rem] shadow-sm border border-slate-100 dark:border-slate-700 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-slate-50 dark:bg-slate-900/50">
                            <tr>
                                <th className="px-6 py-4 text-right text-sm font-bold text-slate-500">الوقت</th>
                                <th className="px-6 py-4 text-right text-sm font-bold text-slate-500">المستخدم</th>
                                <th className="px-6 py-4 text-right text-sm font-bold text-slate-500">السؤال</th>
                                <th className="px-6 py-4 text-right text-sm font-bold text-slate-500">الأداة</th>
                                <th className="px-6 py-4 text-right text-sm font-bold text-slate-500">الحالة</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                            {loading ? (
                                <tr><td colSpan="5" className="px-6 py-8 text-center text-slate-400">تحميل...</td></tr>
                            ) : logs.length === 0 ? (
                                <tr><td colSpan="5" className="px-6 py-8 text-center text-slate-400">لا توجد سجلات</td></tr>
                            ) : logs.map((log) => (
                                <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                                    <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-300">
                                        <div className="flex items-center gap-2">
                                            <Clock size={14} className="text-slate-400" />
                                            {new Date(log.created_at).toLocaleString('ar-EG')}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                            {log.username}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-slate-800 dark:text-white max-w-xs truncate" title={log.query}>
                                        {log.query}
                                    </td>
                                    <td className="px-6 py-4 text-sm font-mono text-slate-500">
                                        {log.response_tool || '-'}
                                    </td>
                                    <td className="px-6 py-4">
                                        {log.success ? (
                                            <span className="inline-flex items-center gap-1 text-emerald-600 text-xs font-bold">
                                                <CheckCircle size={14} /> نجاح
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center gap-1 text-red-500 text-xs font-bold">
                                                <XCircle size={14} /> فشل
                                            </span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

