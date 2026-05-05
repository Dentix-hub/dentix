import { memo } from 'react';
import { 
    Clock, 
    PlusCircle, 
    CreditCard, 
    AlertCircle, 
    ShieldAlert,
    ChevronLeft,
    ChevronRight
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ar, enUS } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';

const iconMap = {
    tenant: { icon: PlusCircle, color: 'text-emerald-500', bg: 'bg-emerald-50' },
    payment: { icon: CreditCard, color: 'text-blue-500', bg: 'bg-blue-50' },
    error: { icon: AlertCircle, color: 'text-rose-500', bg: 'bg-rose-50' },
    audit: { icon: ShieldAlert, color: 'text-amber-500', bg: 'bg-amber-50' }
};

const ActivityFeed = memo(function ActivityFeed({ activities = [] }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    if (!activities?.length) {
        return (
            <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-100 dark:border-slate-800 text-center" dir={isRtl ? 'rtl' : 'ltr'}>
                <p className="text-slate-500">{t('super_admin.activity.no_activity')}</p>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-100 dark:border-slate-800 overflow-hidden shadow-sm" dir={isRtl ? 'rtl' : 'ltr'}>
            <div className="p-6 border-b border-slate-50 dark:border-slate-800 flex justify-between items-center">
                <h3 className="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2">
                    <Clock size={20} className="text-indigo-500" />
                    {t('super_admin.activity.title')}
                </h3>
            </div>
            
            <div className="divide-y divide-slate-50 dark:divide-slate-800 max-h-[500px] overflow-y-auto custom-scrollbar">
                {activities.map((activity, idx) => {
                    const Config = iconMap[activity.type] || iconMap.audit;
                    return (
                        <div 
                            key={`${activity.type}-${activity.id}-${idx}`}
                            className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group cursor-pointer"
                            onClick={() => activity.link && (window.location.href = activity.link)}
                        >
                            <div className="flex gap-4">
                                <div className={`${Config.bg} dark:bg-opacity-10 p-2.5 rounded-xl self-start`}>
                                    <Config.icon size={20} className={Config.color} />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-start mb-0.5">
                                        <h4 className="font-bold text-slate-800 dark:text-slate-200 truncate">
                                            {activity.title}
                                        </h4>
                                        <span className={`text-[11px] text-slate-400 whitespace-nowrap bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-full ${isRtl ? 'mr-2' : 'ml-2'}`}>
                                            {formatDistanceToNow(new Date(activity.timestamp), { 
                                                addSuffix: true, 
                                                locale: isRtl ? ar : enUS 
                                            })}
                                        </span>
                                    </div>
                                    <p className="text-sm text-slate-500 dark:text-slate-400 line-clamp-2">
                                        {activity.description}
                                    </p>
                                </div>
                                <div className="opacity-0 group-hover:opacity-100 transition-opacity self-center">
                                    {isRtl ? <ChevronLeft size={16} className="text-slate-300" /> : <ChevronRight size={16} className="text-slate-300" />}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
            
            <div className="p-4 bg-slate-50/50 dark:bg-slate-800/30 text-center border-t border-slate-50 dark:border-slate-800">
                <button className="text-sm font-bold text-indigo-600 dark:text-indigo-400 hover:underline">
                    {t('super_admin.activity.view_all')}
                </button>
            </div>
        </div>
    );
});

export default ActivityFeed;
