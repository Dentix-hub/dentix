import { Activity, AlertTriangle, ShieldAlert, Database, CheckCircle2, Clock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useSystemHealth, useInvalidateSystemHealth, HEALTH_STATUS_CLASS_MAP } from './hooks/useSystemHealth';

export default function HealthAlerts() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const { data: health, isLoading: loading, error } = useSystemHealth();
    const invalidateHealth = useInvalidateSystemHealth();

    if (loading && !health) return (
        <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-8 border border-slate-100 dark:border-slate-800 animate-pulse" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="h-8 w-48 bg-slate-100 dark:bg-slate-800 rounded-lg mb-6"></div>
            <div className="space-y-4">
                <div className="h-16 bg-slate-50 dark:bg-slate-800/50 rounded-2xl"></div>
                <div className="h-16 bg-slate-50 dark:bg-slate-800/50 rounded-2xl"></div>
            </div>
        </div>
    );

    const getStatusConfig = (status) => {
        switch (status) {
            case 'healthy': return { key: 'healthy', label: t('super_admin.health.stable') || 'مستقر', icon: CheckCircle2 };
            case 'warning': return { key: 'warning', label: t('super_admin.health.warning') || 'تحذير', icon: AlertTriangle };
            case 'critical': return { key: 'critical', label: t('super_admin.health.critical') || 'حرج', icon: ShieldAlert };
            default: return { key: 'unknown', label: t('super_admin.health.unknown') || 'غير محدد', icon: Activity };
        }
    };

    const statusKey = error ? 'unknown' : (health?.status || 'unknown');
    const config = getStatusConfig(statusKey);
    const classes = HEALTH_STATUS_CLASS_MAP[config.key] || HEALTH_STATUS_CLASS_MAP.unknown;

    return (
        <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-8 border border-slate-100 dark:border-slate-800 shadow-sm overflow-hidden relative group" dir={isRtl ? 'rtl' : 'ltr'}>
            {/* Background Glow with static classes */}
            <div className={`absolute -top-24 ${isRtl ? '-start-24' : '-end-24'} w-64 h-64 blur-[100px] rounded-full transition-all duration-700 ${classes.glow}`}></div>
            
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8 relative z-10">
                <div className="flex items-center gap-4">
                    <div className={`p-4 rounded-2xl ${classes.bgLight} ${classes.text} shrink-0`}>
                        <config.icon size={32} />
                    </div>
                    <div className="text-start">
                        <h3 className="text-2xl font-black text-slate-800 dark:text-white">{t('super_admin.health.health_score') || 'درجة صحة النظام'}</h3>
                        <div className="flex items-center gap-2 mt-1">
                            <span className={`w-2 h-2 rounded-full ${classes.dot} animate-pulse`}></span>
                            <p className={`font-black text-sm ${classes.text}`}>{config.label}</p>
                        </div>
                    </div>
                </div>

                <div className="flex flex-col md:items-end text-start md:text-end">
                    <div className="text-4xl font-black text-slate-800 dark:text-white tabular-nums">
                        {health?.score !== null && health?.score !== undefined ? health.score : '—'}<span className="text-lg text-slate-400 font-bold">%</span>
                    </div>
                    <p className="text-xs text-slate-500 font-bold mt-1">{t('super_admin.health.analysis_title') || 'مؤشر أداء الخدمات الأساسية'}</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative z-10">
                <div className="p-5 rounded-3xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 group/item hover:border-rose-200 transition-all text-start">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-rose-100 dark:bg-rose-900/20 text-rose-600 rounded-xl">
                            <AlertTriangle size={18} />
                        </div>
                        <span className="text-sm font-black text-slate-700 dark:text-slate-300">{t('super_admin.health.critical_errors') || 'أخطاء حرجة'}</span>
                    </div>
                    <div className="text-2xl font-black text-slate-800 dark:text-white">{health?.critical_errors || 0}</div>
                    <p className="text-[10px] text-slate-500 font-bold uppercase mt-1">{t('super_admin.health.last_24h') || 'خلال 24 ساعة'}</p>
                </div>

                <div className="p-5 rounded-3xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 group/item hover:border-indigo-200 transition-all text-start">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-indigo-100 dark:bg-indigo-900/20 text-indigo-600 rounded-xl">
                            <ShieldAlert size={18} />
                        </div>
                        <span className="text-sm font-black text-slate-700 dark:text-slate-300">{t('super_admin.health.security_alerts') || 'تنبيهات أمنية'}</span>
                    </div>
                    <div className="text-2xl font-black text-slate-800 dark:text-white">{health?.security_alerts || 0}</div>
                    <p className="text-[10px] text-slate-500 font-bold uppercase mt-1">{t('super_admin.health.high_level') || 'مستوى عالي الأهمية'}</p>
                </div>

                <div className="p-5 rounded-3xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 group/item hover:border-amber-200 transition-all text-start">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-amber-100 dark:bg-amber-900/20 text-amber-600 rounded-xl">
                            <Database size={18} />
                        </div>
                        <span className="text-sm font-black text-slate-700 dark:text-slate-300">{t('super_admin.health.backups') || 'النسخ الاحتياطي'}</span>
                    </div>
                    <div className="text-2xl font-black text-slate-800 dark:text-white">
                        {health?.failed_backups_count > 0 ? (
                            <span className="text-rose-500 flex items-center gap-1">
                                {health.failed_backups_count} <span className="text-xs">{t('super_admin.health.failed') || 'فشل'}</span>
                            </span>
                        ) : (
                            <span className="text-emerald-500">{t('super_admin.health.success') || 'ناجح'}</span>
                        )}
                    </div>
                    <p className="text-[10px] text-slate-500 font-bold uppercase mt-1">{t('super_admin.health.cloud_sync') || 'المزامنة السحابية'}</p>
                </div>
            </div>

            <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between relative z-10">
                <div className="flex items-center gap-2 text-slate-400 text-xs font-bold">
                    <Clock size={14} />
                    <span>
                        {t('super_admin.health.last_check') || 'آخر فحص'}: {health?.checked_at ? new Date(health.checked_at).toLocaleTimeString(i18n.language) : '—'}
                    </span>
                </div>
                <button 
                    type="button"
                    onClick={() => invalidateHealth()}
                    className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 text-xs font-black flex items-center gap-1 transition-all hover:gap-2 cursor-pointer"
                >
                    {t('super_admin.health.update_now') || 'تحديث الآن'} ↺
                </button>
            </div>
        </div>
    );
}
