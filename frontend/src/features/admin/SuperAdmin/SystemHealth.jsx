import React, { useState, useEffect } from 'react';
import { api } from '@/api';
import { Activity, Server, Clock, CheckCircle, Play } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from '@/shared/ui';

export default function SystemHealth() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [jobs, setJobs] = useState([]);
    const [health, setHealth] = useState({ score: 100, alerts: [] });
    const [loading, setLoading] = useState(true);
    const [runningTest, setRunningTest] = useState(false);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 10000);
        return () => clearInterval(interval);
    }, []);

    const fetchData = () => {
        fetchJobs();
        fetchHealth();
    };

    const fetchJobs = async () => {
        try {
            const res = await api.get('/api/v1/admin/security/jobs');
            setJobs(Array.isArray(res.data) ? res.data : []);
            setLoading(false);
        } catch (error) {
            console.error("Failed to fetch jobs", error);
        }
    };

    const fetchHealth = async () => {
        try {
            const res = await api.get('/api/v1/admin/health/alerts');
            setHealth(res.data);
        } catch (error) {
            console.error("Failed to fetch health", error);
        }
    };

    const runHealthCheck = async () => {
        setRunningTest(true);
        try {
            const res = await api.post('/api/v1/admin/health/check');
            setHealth(res.data.health);
            if (res.data.notification_sent) {
                toast.success(t('super_admin.health.check_success_alerts'));
            } else {
                toast.success(t('super_admin.health.check_success_stable'));
            }
            fetchJobs();
        } finally {
            setRunningTest(false);
        }
    };

    const runBusinessCheck = async () => {
        setRunningTest(true);
        try {
            const res = await api.post('/api/v1/admin/business/check');
            const { expiring_alerts, churn_alerts } = res.data;
            toast.success(t('super_admin.health.business_check_success', { expiring: expiring_alerts, churn: churn_alerts }));
        } catch (error) {
            toast.error(t('super_admin.health.business_check_error'));
        } finally {
            setRunningTest(false);
        }
    };

    const stats = {
        successRate: jobs.length > 0 ? ((jobs.filter(j => j.status === 'success').length / jobs.length) * 100).toFixed(1) : '100',
        lastBackup: jobs.find(j => j.job_name.toLowerCase().includes('backup'))?.started_at || null,
        avgLatency: jobs.length > 0 ? (jobs.reduce((acc, j) => acc + j.duration_seconds, 0) / jobs.length).toFixed(2) : '0.00'
    };

    return (
        <div className="space-y-6 animate-fade-in-up">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <h3 className={`text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                    <Activity className="text-blue-500" />
                    {t('super_admin.health.background_jobs')}
                </h3>
                <div className="flex gap-2 w-full md:w-auto">
                    <button
                        onClick={runBusinessCheck}
                        disabled={runningTest}
                        className={`flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl shadow-lg font-bold text-sm disabled:opacity-50 transition-all active:scale-95 ${isRtl ? 'flex-row-reverse' : ''}`}
                    >
                        <Activity size={16} className={runningTest ? 'animate-pulse' : ''} />
                        {runningTest ? t('super_admin.health.checking') : t('super_admin.health.run_business_check')}
                    </button>
                    <button
                        onClick={runHealthCheck}
                        disabled={runningTest}
                        className={`flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-lg font-bold text-sm disabled:opacity-50 transition-all active:scale-95 ${isRtl ? 'flex-row-reverse' : ''}`}
                    >
                        <Activity size={16} className={runningTest ? 'animate-pulse' : ''} />
                        {runningTest ? t('super_admin.health.checking') : t('super_admin.health.run_system_check')}
                    </button>
                </div>
            </div>

            {/* Health Score Overview */}
            <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl shadow-xl border border-slate-100 dark:border-slate-800 flex flex-col md:flex-row items-center gap-8 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                    <Activity size={200} />
                </div>
                
                <div className="relative flex-shrink-0">
                    <svg className="w-32 h-32 transform -rotate-90">
                        <circle
                            cx="64"
                            cy="64"
                            r="58"
                            stroke="currentColor"
                            strokeWidth="12"
                            fill="transparent"
                            className="text-slate-100 dark:text-slate-800"
                        />
                        <circle
                            cx="64"
                            cy="64"
                            r="58"
                            stroke="currentColor"
                            strokeWidth="12"
                            fill="transparent"
                            strokeDasharray={364.4}
                            strokeDashoffset={364.4 - (364.4 * health.score) / 100}
                            strokeLinecap="round"
                            className={`transition-all duration-1000 ${
                                health.score > 80 ? 'text-emerald-500' : health.score > 60 ? 'text-amber-500' : 'text-red-500'
                            }`}
                        />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-3xl font-black text-slate-800 dark:text-white">{health.score}%</span>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{t('super_admin.health.health_score')}</span>
                    </div>
                </div>

                <div className={`flex-grow space-y-4 ${isRtl ? 'text-right' : 'text-left'}`}>
                    <div>
                        <h4 className="text-lg font-bold text-slate-800 dark:text-white mb-1">{t('super_admin.health.analysis_title')}</h4>
                        <p className="text-sm text-slate-500">{t('super_admin.health.analysis_desc')}</p>
                    </div>
                    
                    <div className={`flex flex-wrap gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        {health.alerts.length > 0 ? (
                            health.alerts.map((alert, idx) => (
                                <div key={idx} className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold ${
                                    alert.severity === 'critical' ? 'bg-red-100 text-red-700' : 
                                    alert.severity === 'high' ? 'bg-orange-100 text-orange-700' : 'bg-amber-100 text-amber-700'
                                } ${isRtl ? 'flex-row-reverse' : ''}`}>
                                    <div className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                                    {alert.message}
                                </div>
                            ))
                        ) : (
                            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700 ${isRtl ? 'flex-row-reverse' : ''}`}>
                                <CheckCircle size={14} />
                                {t('super_admin.health.all_good')}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className={`bg-white dark:bg-slate-900 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800 flex items-center gap-4 hover:shadow-md transition-shadow ${isRtl ? 'flex-row-reverse' : ''}`}>
                    <div className="p-4 bg-emerald-100 text-emerald-600 rounded-xl">
                        <CheckCircle size={32} />
                    </div>
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <p className="text-sm text-slate-500 font-bold">{t('super_admin.health.success_rate')}</p>
                        <p className="text-2xl font-bold text-slate-800 dark:text-white" dir="ltr">{stats.successRate}%</p>
                    </div>
                </div>
                <div className={`bg-white dark:bg-slate-900 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800 flex items-center gap-4 hover:shadow-md transition-shadow ${isRtl ? 'flex-row-reverse' : ''}`}>
                    <div className="p-4 bg-blue-100 text-blue-600 rounded-xl">
                        <Server size={32} />
                    </div>
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <p className="text-sm text-slate-500 font-bold">{t('super_admin.health.last_backup')}</p>
                        <p className="text-2xl font-bold text-slate-800 dark:text-white" dir="ltr">
                            {stats.lastBackup ? new Date(stats.lastBackup).toLocaleDateString(isRtl ? 'ar-EG' : 'en-US', { hour: '2-digit', minute: '2-digit' }) : t('common.no_results')}
                        </p>
                    </div>
                </div>
                <div className={`bg-white dark:bg-slate-900 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800 flex items-center gap-4 hover:shadow-md transition-shadow ${isRtl ? 'flex-row-reverse' : ''}`}>
                    <div className="p-4 bg-teal-100 text-teal-600 rounded-xl">
                        <Clock size={32} />
                    </div>
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <p className="text-sm text-slate-500 font-bold">{t('super_admin.health.avg_latency')}</p>
                        <p className="text-2xl font-bold text-slate-800 dark:text-white" dir="ltr">{stats.avgLatency}s</p>
                    </div>
                </div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-800 overflow-hidden">
                <table className="w-full" dir={isRtl ? 'rtl' : 'ltr'}>
                    <thead className="bg-slate-50 dark:bg-slate-800 text-slate-500 font-bold text-sm">
                        <tr className={isRtl ? 'text-right' : 'text-left'}>
                            <th className="p-4">{t('super_admin.health.job_name')}</th>
                            <th className="p-4">{t('super_admin.health.status')}</th>
                            <th className="p-4">{t('super_admin.health.duration')}</th>
                            <th className="p-4">{t('super_admin.health.started_at')}</th>
                            <th className="p-4">{t('super_admin.health.triggered_by')}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {jobs.map(job => (
                            <tr key={job.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                <td className={`p-4 font-bold text-slate-700 dark:text-slate-300 flex items-center gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
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
                                    {new Date(job.started_at).toLocaleString(isRtl ? 'ar-EG' : 'en-US')}
                                </td>
                                <td className="p-4 text-slate-500 text-sm">
                                    {job.triggered_by}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {jobs.length === 0 && !loading && (
                    <div className="p-8 text-center text-slate-500">{t('super_admin.health.no_records')}</div>
                )}
            </div>
        </div>
    );
}

