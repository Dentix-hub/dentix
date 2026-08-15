import { Building2, TrendingUp, AlertCircle, DollarSign } from 'lucide-react';
import StatCard from '@/shared/ui/StatCard';
import { useTranslation } from 'react-i18next';

const DashboardStats = ({ stats }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    if (!stats) return null;

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-fade-in" dir={isRtl ? 'rtl' : 'ltr'}>
            <StatCard 
                icon={Building2} 
                title={t('super_admin.stats.total_tenants')} 
                value={stats.total_tenants} 
                subtext={t('super_admin.stats.total_tenants_desc')} 
                color="teal" 
            />
            <StatCard 
                icon={TrendingUp} 
                title={t('super_admin.stats.active_tenants')} 
                value={stats.active_tenants} 
                subtext={t('super_admin.stats.active_tenants_desc')} 
                color="emerald" 
            />
            <StatCard 
                icon={AlertCircle} 
                title={t('super_admin.stats.expired_tenants')} 
                value={stats.expired_tenants} 
                subtext={t('super_admin.stats.expired_tenants_desc')} 
                color="rose" 
            />
            <StatCard 
                icon={DollarSign} 
                title={t('super_admin.stats.total_revenue')} 
                value={`${(stats.total_revenue || 0).toLocaleString()} ${t('super_admin.finance.currency')}`} 
                subtext={t('super_admin.stats.total_revenue_desc')} 
                color="amber" 
            />
        </div>
    );
};

export default DashboardStats;

