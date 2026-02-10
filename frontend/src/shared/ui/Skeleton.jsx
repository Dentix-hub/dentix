import { memo } from 'react';
/**
 * Skeleton Loading Components
 * Use these for better perceived performance while data loads
 */
// Shimmer animation style
const shimmerStyle = {
    backgroundImage: 'linear-gradient(90deg, #f0f0f0 0%, #e0e0e0 50%, #f0f0f0 100%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.5s infinite',
};
// Add this to your CSS:
// @keyframes shimmer { 0% { background-position: 200% 0 } 100% { background-position: -200% 0 } }
export const SkeletonBox = memo(function SkeletonBox({
    className = '',
    width = '100%',
    height = '1rem',
    rounded = 'md'
}) {
    return (
        <div
            className={`bg-slate-200 dark:bg-slate-700/50 animate-pulse rounded-${rounded} ${className}`}
            style={{ width, height }}
        />
    );
});
export const SkeletonText = memo(function SkeletonText({ lines = 3, className = '' }) {
    return (
        <div className={`space-y-2 ${className}`}>
            {Array.from({ length: lines }).map((_, i) => (
                <SkeletonBox
                    key={i}
                    width={i === lines - 1 ? '75%' : '100%'}
                    height="0.875rem"
                />
            ))}
        </div>
    );
});
export const SkeletonCard = memo(function SkeletonCard({ className = '' }) {
    return (
        <div className={`bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm ${className}`}>
            <div className="flex items-center gap-4 mb-4">
                <SkeletonBox width="3rem" height="3rem" rounded="full" />
                <div className="flex-1">
                    <SkeletonBox width="60%" height="1rem" className="mb-2" />
                    <SkeletonBox width="40%" height="0.75rem" />
                </div>
            </div>
            <SkeletonText lines={2} />
        </div>
    );
});
export const SkeletonTable = memo(function SkeletonTable({ rows = 5, cols = 4 }) {
    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="flex gap-4 p-4 border-b border-slate-100 dark:border-slate-700">
                {Array.from({ length: cols }).map((_, i) => (
                    <SkeletonBox key={i} width={i === 0 ? '30%' : '20%'} height="1rem" />
                ))}
            </div>
            {/* Rows */}
            {Array.from({ length: rows }).map((_, rowIdx) => (
                <div key={rowIdx} className="flex gap-4 p-4 border-b border-slate-50 dark:border-slate-700/50">
                    {Array.from({ length: cols }).map((_, colIdx) => (
                        <SkeletonBox
                            key={colIdx}
                            width={colIdx === 0 ? '30%' : '20%'}
                            height="0.875rem"
                        />
                    ))}
                </div>
            ))}
        </div>
    );
});
export const SkeletonStatCard = memo(function SkeletonStatCard() {
    return (
        <div className="bg-white dark:bg-slate-800/50 p-6 rounded-[2rem] shadow-sm border border-slate-100 dark:border-white/5 flex items-center gap-4">
            <SkeletonBox width="3.5rem" height="3.5rem" rounded="2xl" />
            <div className="flex-1">
                <SkeletonBox width="50%" height="0.875rem" className="mb-2" />
                <SkeletonBox width="70%" height="1.5rem" />
            </div>
        </div>
    );
});
export default {
    Box: SkeletonBox,
    Text: SkeletonText,
    Card: SkeletonCard,
    Table: SkeletonTable,
    StatCard: SkeletonStatCard,
};
