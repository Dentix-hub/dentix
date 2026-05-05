import React, { useState, useEffect } from 'react';
import { api } from '@/api';
import { Activity, AlertTriangle, ShieldAlert, Database, CheckCircle2, Clock } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export default function HealthAlerts() {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchHealth = async () => {
        try {
            const res = await api.get('/api/v1/admin/health/alerts');
            setHealth(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHealth();
        const interval = setInterval(fetchHealth, 60000); // Update every minute
        return () => clearInterval(interval);
    }, []);

    if (loading) return (
        <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-8 border border-slate-100 dark:border-slate-800 animate-pulse">
            <div className={`h-8 w-48 bg-slate-100 dark:bg-slate-800 rounded-lg mb-6 ${isRtl ? 'ml-auto' : ''}`}></div>
            <div className="space-y-4">
                <div className="h-16 bg-slate-50 dark:bg-slate-800/50 rounded-2xl"></div>
                <div className="h-16 bg-slate-50 dark:bg-slate-800/50 rounded-2xl"></div>
            </div>
        </div>
    );

    const getStatusConfig = (status) => {
        switch (status) {
            case 'healthy': return { color: 'emerald', label: t('super_admin.health.stable'), icon: CheckCircle2 };
            case 'warning': return { color: 'amber', label: t('super_admin.health.warning'), icon: AlertTriangle };
            case 'critical': return { color: 'rose', label: t('super_admin.health.critical'), icon: ShieldAlert };
            default: return { color: 'slate', label: t('super_admin.health.unknown'), icon: Activity };
        }
    };

    const config = getStatusConfig(health?.status);

    return (
        <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-8 border border-slate-100 dark:border-slate-800 shadow-sm overflow-hidden relative group">
            {/* Background Glow */}
            <div className={`absolute -top-24 ${isRtl ? '-left-24' : '-right-24'} w-64 h-64 bg-${config.color}-500/5 blur-[100px] rounded-full group-hover:bg-${config.color}-500/10 transition-all duration-700`}></div>
            
            <div className={`flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8 relative z-10 ${isRtl ? 'md:flex-row-reverse' : ''}`}>
                <div className={`flex items-center gap-4 ${isRtl ? 'flex-row-reverse' : ''}`}>
                    <div className={`p-4 rounded-2xl bg-${config.color}-50 dark:bg-${config.color}-900/10 text-${config.color}-600 dark:text-${config.color}-400`}>
                        <config.icon size={32} />
                    </div>
                    <div className={isRtl ? 'text-right' : 'text-left'}>
                        <h3 className="text-2xl font-black text-slate-800 dark:text-white">{t('super_admin.health.health_score')}</h3>
                        <div className={`flex items-center gap-2 mt-1 ${isRtl ? 'flex-row-reverse' : ''}`}>
                            <span className={`w-2 h-2 rounded-full bg-${config.color}-500 animate-pulse`}></span>
                            <p className={`text-${config.color}-600 font-black text-sm`}>{config.label}</p>
                        </div>
                    </div>
                </div>

                <div className={`flex flex-col ${isRtl ? 'items-start' : 'items-end'}`}>
                    <div className="text-4xl font-black text-slate-800 dark:text-white tabular-nums">
                        {health?.score}<span className="text-lg text-slate-400 font-bold">%</span>
                    </div>
                    <p className="text-xs text-slate-500 font-bold mt-1">{t('super_admin.health.analysis_title')}</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative z-10">
                <div className={`p-5 rounded-3xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 group/item hover:border-rose-200 transition-all ${isRtl ? 'text-right' : 'text-left'}`}>
                    <div className={`flex items-center gap-3 mb-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className="p-2 bg-rose-100 dark:bg-rose-900/20 text-rose-600 rounded-xl">
                            <AlertTriangle size={18} />
                        </div>
                        <span className="text-sm font-black text-slate-700 dark:text-slate-300">{t('super_admin.health.critical_errors')}</span>
                    </div>
                    <div className="text-2xl font-black text-slate-800 dark:text-white">{health?.critical_errors}</div>
                    <p className="text-[10px] text-slate-500 font-bold uppercase mt-1">{t('super_admin.health.last_24h')}</p>
                </div>

                <div className={`p-5 rounded-3xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 group/item hover:border-indigo-200 transition-all ${isRtl ? 'text-right' : 'text-left'}`}>
                    <div className={`flex items-center gap-3 mb-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className="p-2 bg-indigo-100 dark:bg-indigo-900/20 text-indigo-600 rounded-xl">
                            <ShieldAlert size={18} />
                        </div>
                        <span className="text-sm font-black text-slate-700 dark:text-slate-300">{t('super_admin.health.security_alerts')}</span>
                    </div>
                    <div className="text-2xl font-black text-slate-800 dark:text-white">{health?.security_alerts}</div>
                    <p className="text-[10px] text-slate-500 font-bold uppercase mt-1">{t('super_admin.health.high_level')}</p>
                </div>

                <div className={`p-5 rounded-3xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 group/item hover:border-amber-200 transition-all ${isRtl ? 'text-right' : 'text-left'}`}>
                    <div className={`flex items-center gap-3 mb-2 ${isRtl ? 'flex-row-reverse' : ''}`}>
                        <div className="p-2 bg-amber-100 dark:bg-amber-900/20 text-amber-600 rounded-xl">
                            <Database size={18} />
                        </div>
                        <span className="text-sm font-black text-slate-700 dark:text-slate-300">{t('super_admin.health.backups')}</span>
                    </div>
                    <div className="text-2xl font-black text-slate-800 dark:text-white">
                        {health?.failed_backups_count > 0 ? (
                            <span className={`text-rose-500 flex items-center gap-1 ${isRtl ? 'flex-row-reverse' : ''}`}>
                                {health.failed_backups_count} <span className="text-xs">{t('super_admin.health.failed')}</span>
                            </span>
                        ) : (
                            <span className="text-emerald-500">{t('super_admin.health.success')}</span>
                        )}
                    </div>
                    <p className="text-[10px] text-slate-500 font-bold uppercase mt-1">{t('super_admin.health.cloud_sync')}</p>
                </div>
            </div>

            <div className={`mt-8 pt-6 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between relative z-10 ${isRtl ? 'flex-row-reverse' : ''}`}>
                <div className={`flex items-center gap-2 text-slate-400 text-xs font-bold ${isRtl ? 'flex-row-reverse' : ''}`}>
                    <Clock size={14} />
                    <span>{t('super_admin.health.last_check')}: {new Date(health?.checked_at).toLocaleTimeString(isRtl ? 'ar-EG' : 'en-US')}</span>
                </div>
                <button 
                    onClick={fetchHealth}
                    className={`text-indigo-600 hover:text-indigo-700 text-xs font-black flex items-center gap-1 transition-all hover:gap-2 ${isRtl ? 'flex-row-reverse' : ''}`}
                >
                    {t('super_admin.health.update_now')} {isRtl ? '↺' : '↺'}
                </button>
            </div>
        </div>
    );
}

