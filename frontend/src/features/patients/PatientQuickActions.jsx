import React, { memo } from 'react';
import { Plus, Users, UserPlus, Activity } from 'lucide-react';
import { Button, SkeletonBox } from '@/shared/ui';

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
    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                        <Users className="w-6 h-6" />
                        Patients
                    </h1>
                    <p className="text-slate-500 mt-1">Manage your patient records</p>
                </div>
                <Button onClick={onAddClick} size="lg">
                    <Plus className="w-4 h-4 mr-2" />
                    Add New
                </Button>
            </div>

            {/* Stats Bar */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard
                    icon={Users}
                    label="Total Patients"
                    value={stats?.total || 0}
                    isLoading={isLoading}
                />
                <StatCard
                    icon={UserPlus}
                    label="New This Month"
                    value={stats?.newThisMonth || 0}
                    isLoading={isLoading}
                />
                <StatCard
                    icon={Activity}
                    label="Active Patients"
                    value={stats?.active || 0}
                    isLoading={isLoading}
                />
            </div>
        </div>
    );
});
