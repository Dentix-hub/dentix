import React, { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Users, UserPlus, Activity, Home } from 'lucide-react';
import { Button, SkeletonBox, PageHeader } from '@/shared/ui';

function StatCard({ icon: Icon, label, value, isLoading }) {
    if (isLoading) {
        return (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <div className="flex items-center justify-between">
                    <SkeletonBox className="w-10 h-10 rounded-lg" />
                    <SkeletonBox className="w-16 h-8" />
                </div>
                <SkeletonBox className="w-24 h-4 mt-3" />
            </div>
        );
    }

    return (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between">
                <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
                    <Icon className="w-5 h-5" />
                </div>
                <span className="text-2xl font-bold text-slate-800">{value}</span>
            </div>
            <p className="mt-3 text-sm text-slate-600">{label}</p>
        </div>
    );
}

export default memo(function PatientQuickActions({ stats, isLoading, onAddClick }) {
    const { t } = useTranslation();

    return (
        <div className="space-y-6">
            <PageHeader
                title={t('patients.title')}
                subtitle={t('patients.subtitle')}
                icon={Users}
                breadcrumbs={[
                    { label: t('nav.home', 'Home'), icon: Home, path: '/' },
                    { label: t('patients.title') }
                ]}
                actions={
                    <Button onClick={onAddClick} size="lg">
                        <Plus className="w-4 h-4 mr-2" />
                        {t('patients.add_new')}
                    </Button>
                }
            />

            {/* Stats Bar */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard
                    icon={Users}
                    label={t('patients.stats_total')}
                    value={stats?.total || 0}
                    isLoading={isLoading}
                />
                <StatCard
                    icon={UserPlus}
                    label={t('patients.stats_new_month')}
                    value={stats?.newThisMonth || 0}
                    isLoading={isLoading}
                />
                <StatCard
                    icon={Activity}
                    label={t('patients.stats_active')}
                    value={stats?.active || 0}
                    isLoading={isLoading}
                />
            </div>
        </div>
    );
});

