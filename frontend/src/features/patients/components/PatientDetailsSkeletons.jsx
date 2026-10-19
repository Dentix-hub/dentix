import { memo } from 'react';
import { SkeletonBox } from '@/shared/ui';

export const TabSkeleton = memo(() => (
    <div className="space-y-3 p-2 sm:space-y-4 sm:p-4">
        <SkeletonBox height="4rem" className="rounded-xl" />
        <SkeletonBox height="4rem" className="rounded-xl" />
        <SkeletonBox height="4rem" className="rounded-xl" />
    </div>
));
TabSkeleton.displayName = 'TabSkeleton';

export const PatientInfoSkeleton = memo(() => (
    <div className="flex min-w-0 items-center gap-3 rounded-2xl border border-border bg-surface p-3 animate-pulse sm:gap-4 sm:rounded-3xl sm:p-6">
        <div className="h-12 w-12 shrink-0 rounded-xl bg-slate-200 dark:bg-slate-700 sm:h-16 sm:w-16 sm:rounded-2xl" />
        <div className="min-w-0 flex-1 space-y-2">
            <div className="h-6 w-2/3 max-w-48 rounded bg-slate-200 dark:bg-slate-700" />
            <div className="h-4 w-1/2 max-w-32 rounded bg-slate-200 dark:bg-slate-700" />
        </div>
    </div>
));
PatientInfoSkeleton.displayName = 'PatientInfoSkeleton';
