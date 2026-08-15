import { lazy, Suspense } from 'react';

// Single dynamic import promise for all Recharts exports
const RechartsPromise = import('./RechartsComponents');

// Lazy-loaded component exports
export const ResponsiveContainer = lazy(() => RechartsPromise.then(m => ({ default: m.ResponsiveContainer })));
export const AreaChart = lazy(() => RechartsPromise.then(m => ({ default: m.AreaChart })));
export const Area = lazy(() => RechartsPromise.then(m => ({ default: m.Area })));
export const XAxis = lazy(() => RechartsPromise.then(m => ({ default: m.XAxis })));
export const YAxis = lazy(() => RechartsPromise.then(m => ({ default: m.YAxis })));
export const Tooltip = lazy(() => RechartsPromise.then(m => ({ default: m.Tooltip })));
export const PieChart = lazy(() => RechartsPromise.then(m => ({ default: m.PieChart })));
export const Pie = lazy(() => RechartsPromise.then(m => ({ default: m.Pie })));
export const Cell = lazy(() => RechartsPromise.then(m => ({ default: m.Cell })));
export const LineChart = lazy(() => RechartsPromise.then(m => ({ default: m.LineChart })));
export const Line = lazy(() => RechartsPromise.then(m => ({ default: m.Line })));
export const BarChart = lazy(() => RechartsPromise.then(m => ({ default: m.BarChart })));
export const Bar = lazy(() => RechartsPromise.then(m => ({ default: m.Bar })));
export const CartesianGrid = lazy(() => RechartsPromise.then(m => ({ default: m.CartesianGrid })));
export const Legend = lazy(() => RechartsPromise.then(m => ({ default: m.Legend })));

// Helper wrapper component that provides local Suspense fallback
export function LazyChart({ children, fallback }) {
    return (
        <Suspense fallback={fallback || <div className="h-64 bg-slate-100 dark:bg-slate-800/50 animate-pulse rounded-3xl w-full" />}>
            {children}
        </Suspense>
    );
}
