import React, { useState, useEffect } from 'react';
import { api } from '@/api';
import { Activity, Server, Clock, CheckCircle, XCircle, Play } from 'lucide-react';

export default function SystemHealth() {
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [runningTest, setRunningTest] = useState(false);

    useEffect(() => {
        fetchJobs();
        const interval = setInterval(fetchJobs, 10000); // Poll every 10s
        return () => clearInterval(interval);
    }, []);

    const fetchJobs = async () => {
        try {
            const res = await api.get('/api/v1/admin/security/jobs'); // Check endpoint path
            setJobs(res.data);
            setLoading(false);
        } catch (error) {
            console.error("Failed to fetch jobs", error);
        }
    };

    const runTestJob = async () => {
        setRunningTest(true);
        try {
            await api.post('/api/v1/admin/security/jobs/trigger-test');
            fetchJobs();
        } catch (error) {
            alert("فشل تشغيل المهمة التجريبية");
        } finally {
            setRunningTest(false);
        }
    };

    return (
        <div className="space-y-6 animate-fade-in-up">
            <div className="flex justify-between items-center">
                <h3 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                    <Activity className="text-blue-500" />
                    حالة النظام والمهام الخلفية (Background Jobs)
                </h3>
                <button
                    onClick={runTestJob}
                    disabled={runningTest}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow font-bold text-sm disabled:opacity-50"
                >
                    <Play size={16} />
                    {runningTest ? 'جاري التشغيل...' : 'تشغيل فحص يدوي'}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800 flex items-center gap-4">
                    <div className="p-4 bg-emerald-100 text-emerald-600 rounded-xl">
                        <CheckCircle size={32} />
                    </div>
                    <div>
                        <p className="text-sm text-slate-500 font-bold">نسبة النجاح (24h)</p>
                        <p className="text-2xl font-bold text-slate-800 dark:text-white">99.8%</p>
                    </div>
                </div>
                <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800 flex items-center gap-4">
                    <div className="p-4 bg-blue-100 text-blue-600 rounded-xl">
                        <Server size={32} />
                    </div>
                    <div>
                        <p className="text-sm text-slate-500 font-bold">آخر نسخ احتياطي</p>
                        <p className="text-2xl font-bold text-slate-800 dark:text-white">منذ 2 ساعة</p>
                    </div>
                </div>
                <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800 flex items-center gap-4">
                    <div className="p-4 bg-purple-100 text-purple-600 rounded-xl">
                        <Clock size={32} />
                    </div>
                    <div>
                        <p className="text-sm text-slate-500 font-bold">متوسط زمن الاستجابة</p>
                        <p className="text-2xl font-bold text-slate-800 dark:text-white">45ms</p>
                    </div>
                </div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                <table className="w-full text-right">
                    <thead className="bg-slate-50 dark:bg-slate-800 text-slate-500 font-bold text-sm">
                        <tr>
                            <th className="p-4">اسم المهمة</th>
                            <th className="p-4">الحالة</th>
                            <th className="p-4">الوقت المستغرق</th>
                            <th className="p-4">تاريخ البدء</th>
                            <th className="p-4">المُشغّل</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {jobs.map(job => (
                            <tr key={job.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                <td className="p-4 font-bold text-slate-700 dark:text-slate-300 flex items-center gap-2">
                                    <div className={`w-2 h-2 rounded-full ${job.status === 'success' ? 'bg-emerald-500' : job.status === 'running' ? 'bg-blue-500 animate-pulse' : 'bg-red-500'}`}></div>
                                    {job.job_name}
                                </td>
                                <td className="p-4">
                                    <span className={`px-2 py-1 rounded text-xs font-bold ${job.status === 'success' ? 'bg-emerald-100 text-emerald-700' :
                                        job.status === 'running' ? 'bg-blue-100 text-blue-700' :
                                            'bg-red-100 text-red-700'
                                        }`}>
                                        {job.status.toUpperCase()}
                                    </span>
                                </td>
                                <td className="p-4 text-slate-500 font-mono text-sm" dir="ltr">
                                    {job.duration_seconds.toFixed(2)}s
                                </td>
                                <td className="p-4 text-slate-500 text-sm" dir="ltr">
                                    {new Date(job.started_at).toLocaleString()}
                                </td>
                                <td className="p-4 text-slate-500 text-sm">
                                    {job.triggered_by}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {jobs.length === 0 && !loading && (
                    <div className="p-8 text-center text-slate-400">لا توجد سجلات للمهام مؤخراً.</div>
                )}
            </div>
        </div>
    );
}
