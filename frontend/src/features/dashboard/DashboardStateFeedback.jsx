import { AlertCircle, AlertTriangle, CalendarX2, RefreshCw } from 'lucide-react';
import { Button } from '@/shared/ui';

export function DashboardSourceError({
    title,
    description,
    actions = [],
    testId,
    compact = false,
}) {
    return (
        <div
            role="alert"
            data-testid={testId}
            className={`flex w-full flex-col items-center justify-center rounded-2xl border border-rose-200/80 bg-rose-50/70 text-center dark:border-rose-900/50 dark:bg-rose-950/20 ${
                compact ? 'gap-2.5 p-4' : 'gap-3 p-5 sm:p-6'
            }`}
        >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-400">
                <AlertCircle size={20} aria-hidden="true" />
            </div>
            <div className="max-w-md space-y-1">
                <h4 className="text-sm font-bold text-text-primary sm:text-base">{title}</h4>
                <p className="text-xs text-text-secondary sm:text-sm">{description}</p>
            </div>
            {actions.length > 0 && (
                <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
                    {actions.map((action) => (
                        <Button
                            key={action.key}
                            type="button"
                            size="sm"
                            variant="secondary"
                            onClick={action.onClick}
                            disabled={action.loading}
                            data-testid={action.testId}
                            className="min-h-10 gap-2"
                        >
                            <RefreshCw
                                size={14}
                                className={action.loading ? 'animate-spin' : ''}
                                aria-hidden="true"
                            />
                            <span>{action.loading ? action.loadingLabel : action.label}</span>
                        </Button>
                    ))}
                </div>
            )}
        </div>
    );
}

export function DashboardStaleWarning({
    message,
    retryLabel,
    retryingLabel,
    isRetrying,
    onRetry,
    testId,
    retryTestId,
}) {
    return (
        <div
            role="status"
            aria-live="polite"
            data-testid={testId}
            className="flex flex-col gap-3 rounded-2xl border border-amber-300/80 bg-amber-50/90 px-4 py-3 text-amber-950 dark:border-amber-800/70 dark:bg-amber-950/30 dark:text-amber-100 sm:flex-row sm:items-center sm:justify-between"
        >
            <div className="flex min-w-0 items-start gap-2.5 sm:items-center">
                <AlertTriangle
                    size={18}
                    className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400 sm:mt-0"
                    aria-hidden="true"
                />
                <p className="min-w-0 break-words text-xs font-medium sm:text-sm">{message}</p>
            </div>
            <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={onRetry}
                disabled={isRetrying}
                data-testid={retryTestId}
                className="min-h-9 shrink-0 gap-1.5 self-start sm:self-auto"
            >
                <RefreshCw
                    size={14}
                    className={isRetrying ? 'animate-spin' : ''}
                    aria-hidden="true"
                />
                <span>{isRetrying ? retryingLabel : retryLabel}</span>
            </Button>
        </div>
    );
}

export function DashboardUnavailableNotice({
    title,
    description,
    action,
    testId,
    compact = false,
}) {
    return (
        <div
            role="status"
            data-testid={testId}
            className={`flex w-full flex-col items-center justify-center rounded-2xl border border-amber-200/80 bg-amber-50/60 text-center dark:border-amber-900/50 dark:bg-amber-950/20 ${
                compact ? 'gap-2 p-4' : 'gap-3 p-5 sm:p-6'
            }`}
        >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                <CalendarX2 size={20} aria-hidden="true" />
            </div>
            <div className="max-w-md space-y-1">
                <h4 className="text-sm font-bold text-text-primary">{title}</h4>
                <p className="text-xs text-text-secondary sm:text-sm">{description}</p>
            </div>
            {action && (
                <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={action.onClick}
                    disabled={action.loading}
                    data-testid={action.testId}
                    className="min-h-9 gap-1.5"
                >
                    <RefreshCw
                        size={14}
                        className={action.loading ? 'animate-spin' : ''}
                        aria-hidden="true"
                    />
                    <span>{action.loading ? action.loadingLabel : action.label}</span>
                </Button>
            )}
        </div>
    );
}
