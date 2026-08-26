import { useState, useEffect, useCallback } from 'react';
import logger from '@/utils/logger';
import { api } from '@/api';
import { Activity, Server, Clock, CheckCircle, AlertCircle, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from '@/shared/ui';
import { useSystemHealth, useInvalidateSystemHealth, HEALTH_STATUS_CLASS_MAP } from './hooks/useSystemHealth';

export default function SystemHealth() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [jobs, setJobs] = useState([]);
    const [jobsLoading, setJobsLoading] = useState(true);
    const [jobsError, setJobsError] = useState(null);
    const [runningTest, setRunningTest] = useState(false);

    // Shared Health Query Hook
    const { data: health, isLoading: healthLoading, error: healthError } = useSystemHealth();
    const invalidateHealth = useInvalidateSystemHealth();

    const fetchJobs = useCallback(async () => {
        try {
            const res = await api.get('/api/v1/admin/security/jobs');
            setJobs(Array.isArray(res.data) ? res.data : []);
            setJobsError(null);
        } catch (error) {
            logger.error("Failed to fetch jobs", error);
            setJobsError(error);
            setJobs([]);
        } finally {
            setJobsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchJobs();
        const interval = setInterval(fetchJobs, 30000);
        return () => clearInterval(interval);
    }, [fetchJobs]);

    const runHealthCheck = async () => {
        setRunningTest(true);
        try {
            const res = await api.post('/api/v1/admin/health/check');
            invalidateHealth();
            if (res.data?.notification_sent) {
                toast.success(t('super_admin.health.check_success_alerts') || 'تم الفحص وتم إرسال تنبيهات');
            } else {
                toast.success(t('super_admin.health.check_success_stable') || 'النظام مستقر تماماً');
            }
            fetchJobs();
        } catch (err) {
            toast.error(t('common.error') || 'حدث خطأ أثناء فحص النظام');
        } finally {
            setRunningTest(false);
        }
    };

    const runBusinessCheck = async () => {
        setRunningTest(true);
        try {
            const res = await api.post('/api/v1/admin/business/check');
            const { expiring_alerts, churn_alerts } = res.data || {};
            invalidateHealth();
            toast.success(t('super_admin.health.business_check_success', { expiring: expiring_alerts || 0, churn: churn_alerts || 0 }) || `تم فحص الأعمال: ${expiring_alerts || 0} منتهي، ${churn_alerts || 0} ركود`);
            fetchJobs();
        } catch (error) {
            toast.error(t('super_admin.health.business_check_error') || 'فشل فحص الأعمال');
        } finally {
            setRunningTest(false);
        }
    };

    const totalJobs = jobs.length;
    const successJobs = jobs.filter(j => j.status === 'success').length;
    const stats = {
        successRate: totalJobs > 0 ? ((successJobs / totalJobs) * 100).toFixed(1) : (jobsLoading ? '...' : (jobsError ? '—' : '0.0')),
        lastBackup: jobs.find(j => (j.job_name || '').toLowerCase().includes('backup'))?.started_at || null,
        avgLatency: totalJobs > 0 ? (jobs.reduce((acc, j) => acc + (Number(j.duration_seconds) || 0), 0) / totalJobs).toFixed(2) : '0.00'
    };

    const healthScore = health?.score !== null && health?.score !== undefined ? health.score : 0;
    const statusKey = healthError ? 'unknown' : (health?.status || (healthScore >= 90 ? 'healthy' : (healthScore >= 70 ? 'warning' : 'critical')));
    const classes = HEALTH_STATUS_CLASS_MAP[statusKey] || HEALTH_STATUS_CLASS_MAP.unknown;

    return (
        <div className="space-y-6 animate-fade-in-up" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <h3 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                    <Activity className="text-blue-500" />
                    {t('super_admin.health.background_jobs') || 'المهام الخلفية وصحة النظام'}
                </h3>
                <div className="flex gap-2 w-full md:w-auto">
                    <button
                        type="button"
                        onClick={runBusinessCheck}
                        disabled={runningTest}
                        className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl shadow-lg font-bold text-sm disabled:opacity-50 transition-all active:scale-95"
                    >
                        <Activity size={16} className={runningTest ? 'animate-pulse' : ''} />
                        {runningTest ? (t('super_admin.health.checking') || 'جاري الفحص...') : (t('super_admin.health.run_business_check') || 'فحص الأعمال')}
                    </button>
                    <button
                        type="button"
                        onClick={runHealthCheck}
                        disabled={runningTest}
                        className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-lg font-bold text-sm disabled:opacity-50 transition-all active:scale-95"
                    >
                        <Activity size={16} className={runningTest ? 'animate-pulse' : ''} />
                        {runningTest ? (t('super_admin.health.checking') || 'جاري الفحص...') : (t('super_admin.health.run_system_check') || 'فحص شامل للنظام')}
                    </button>
                </div>
            </div>

            {/* Health Score Overview */}
            <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl shadow-xl border border-slate-100 dark:border-slate-800 flex flex-col md:flex-row items-center gap-8 relative overflow-hidden">
                <div className="absolute top-0 end-0 p-4 opacity-5 pointer-events-none">
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
                            className="text-slate-100 dark:text-slate-800"
                            fill="transparent"
                        />
                        <circle
                            cx="64"
                            cy="64"
                            r="58"
                            stroke="currentColor"
                            strokeWidth="12"
                            strokeDasharray={364.4}
                            strokeDashoffset={364.4 - (364.4 * (healthScore || 0)) / 100}
                            strokeLinecap="round"
                            className={classes.text}
                            fill="transparent"
                        />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-3xl font-black text-slate-800 dark:text-white tabular-nums">
                            {healthLoading ? '...' : (healthError ? '—' : `${healthScore}%`)}
                        </span>
                        <span className="text-[10px] text-slate-400 font-bold uppercase">
                            {t('super_admin.health.health_score') || 'الصحة'}
                        </span>
                    </div>
                </div>

                <div className="flex-1 space-y-4 text-start">
                    <div>
                        <div className="flex items-center gap-2">
                            <h4 className="text-lg font-bold text-slate-800 dark:text-white">
                                {t('super_admin.health.overall_status') || 'الحالة العامة للنظام'}
                            </h4>
                            <span className={`px-3 py-1 rounded-full text-xs font-bold ${classes.bgLight} ${classes.text}`}>
                                {healthError ? (t('super_admin.health.unknown') || 'غير محدد') : (statusKey === 'healthy' ? (t('super_admin.health.stable') || 'مستقر') : (statusKey === 'warning' ? (t('super_admin.health.warning') || 'تحذير') : (t('super_admin.health.critical') || 'حرج')))}
                            </span>
                        </div>
                        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
                            {t('super_admin.health.overview_desc') || 'تحليل دائم لأداء المهام وقاعدة البيانات والأمان'}
                        </p>
                    </div>

                    {/* Alerts Summary list */}
                    <div className="space-y-2">
                        {(!health?.alerts || health.alerts.length === 0) ? (
                            <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 text-sm font-medium">
                                <CheckCircle size={16} />
                                <span>{t('super_admin.health.no_active_alerts') || 'لا توجد تنبيهات حرجة نشطة'}</span>
                            </div>
                        ) : (
                            health.alerts.slice(0, 3).map((alert, idx) => (
                                <div key={idx} className="flex items-center gap-2 text-rose-600 dark:text-rose-400 text-sm font-medium">
                                    <AlertCircle size={16} />
                                    <span>{typeof alert === 'string' ? alert : (alert?.message || alert?.title || 'System Alert')}</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Micro Stats */}
                <div className="flex md:flex-col justify-between w-full md:w-auto gap-4 border-t md:border-t-0 md:border-s border-slate-100 dark:border-slate-800 pt-4 md:pt-0 md:ps-8">
                    <div>
                        <span className="text-xs text-slate-400 font-bold block">{t('super_admin.health.job_success_rate') || 'نسبة نجاح المهام'}</span>
                        <span className="text-xl font-black text-slate-800 dark:text-white">{stats.successRate}%</span>
                    </div>
                    <div>
                        <span className="text-xs text-slate-400 font-bold block">{t('super_admin.health.avg_latency') || 'متوسط زمن التنفيذ'}</span>
                        <span className="text-xl font-black text-slate-800 dark:text-white">{stats.avgLatency}s</span>
                    </div>
                </div>
            </div>

            {/* Jobs Telemetry Table */}
            <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-100 dark:border-slate-800 overflow-hidden shadow-sm">
                <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <Server size={20} className="text-slate-400" />
                        <h4 className="font-bold text-slate-800 dark:text-white">{t('super_admin.health.recent_jobs') || 'سجل المهام الأخيرة'}</h4>
                    </div>
                    <button
                        type="button"
                        onClick={fetchJobs}
                        disabled={jobsLoading}
                        className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                    >
                        <Clock size={12} />
                        {jobsLoading ? (t('common.loading') || 'جاري التحديث...') : (t('common.refresh') || 'تحديث')}
                    </button>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-start">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-800/50 text-slate-400 text-xs uppercase tracking-wider text-start">
                                <th className="p-4 font-black text-start">{t('super_admin.health.job_name') || 'اسم المهمة'}</th>
                                <th className="p-4 font-black text-start">{t('super_admin.health.job_status') || 'الحالة'}</th>
                                <th className="p-4 font-black text-start">{t('super_admin.health.job_duration') || 'المدة'}</th>
                                <th className="p-4 font-black text-start">{t('super_admin.health.job_started_at') || 'وقت البدء'}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {jobs.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="p-8 text-center text-slate-400 font-bold">
                                        {jobsLoading ? (t('super_admin.health.loading_jobs') || 'جاري تحميل المهام...') : (t('super_admin.health.no_jobs') || 'لا توجد مهام مسجلة')}
                                    </td>
                                </tr>
                            ) : (
                                jobs.map(job => (
                                    <tr key={job.id || `${job.job_name}-${job.started_at}`} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 text-sm">
                                        <td className="p-4 font-mono font-bold text-slate-800 dark:text-slate-200 text-start">{job.job_name}</td>
                                        <td className="p-4 text-start">
                                            <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${job.status === 'success' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400' : 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400'}`}>
                                                {job.status === 'success' ? <CheckCircle size={12} /> : <AlertTriangle size={12} />}
                                                {job.status}
                                            </span>
                                        </td>
                                        <td className="p-4 text-slate-500 font-mono text-start">{(Number(job.duration_seconds) || 0).toFixed(2)}s</td>
                                        <td className="p-4 text-slate-400 text-xs text-start">
                                            {job.started_at ? new Date(job.started_at).toLocaleString(i18n.language) : '—'}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
