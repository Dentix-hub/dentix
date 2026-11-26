import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { CloudOff, ServerCrash, Loader2, RefreshCw } from 'lucide-react';
import { toast } from '@/shared/ui/ToastProvider';
import { OFFLINE_WRITE_BLOCKED_EVENT } from '@/api/apiClient';
import {
    CONNECTION_STATES,
    useConnectivityStore,
} from '@/pwa/connectivity/connectivityStore';
import {
    evaluateConnectivity,
    useConnectivity,
} from '@/pwa/connectivity/useConnectivity';

const BANNER_STYLES = {
    [CONNECTION_STATES.OFFLINE]: {
        container: 'bg-red-700 text-white',
        text: 'text-white dark:text-white',
        retry: 'bg-red-800 text-white hover:bg-red-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-red-700',
    },
    [CONNECTION_STATES.DEGRADED]: {
        container: 'bg-amber-500 text-slate-950',
        text: 'text-slate-950 dark:text-slate-950',
        retry: 'bg-slate-900 text-white hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 focus-visible:ring-offset-amber-500',
    },
    [CONNECTION_STATES.RECOVERING]: {
        container: 'bg-sky-700 text-white',
        text: 'text-white dark:text-white',
        retry: '',
    },
};

const BANNER_KEYS = {
    [CONNECTION_STATES.OFFLINE]: 'connectivity.offline',
    [CONNECTION_STATES.DEGRADED]: 'connectivity.degraded',
    [CONNECTION_STATES.RECOVERING]: 'connectivity.recovering',
};

/**
 * Global connectivity status banner (plan §10.3).
 * Hidden while ONLINE; distinguishes offline from backend-degraded.
 */
export default function NetworkStatusBanner() {
    const { t } = useTranslation();
    useConnectivity();
    const state = useConnectivityStore((s) => s.state);

    useEffect(() => {
        const onBlocked = () => toast.error(t('connectivity.write_blocked'));
        window.addEventListener(OFFLINE_WRITE_BLOCKED_EVENT, onBlocked);
        return () => window.removeEventListener(OFFLINE_WRITE_BLOCKED_EVENT, onBlocked);
    }, [t]);

    if (state === CONNECTION_STATES.ONLINE) return null;

    const styles = BANNER_STYLES[state];
    const Icon = state === CONNECTION_STATES.OFFLINE
        ? CloudOff
        : state === CONNECTION_STATES.DEGRADED
            ? ServerCrash
            : Loader2;

    return (
        <div
            role="status"
            data-testid="network-status-banner"
            className={`fixed top-[max(0.5rem,env(safe-area-inset-top))] start-4 end-4 md:start-auto md:w-96 z-system
                        flex items-center gap-3 rounded-xl px-4 py-3 shadow-lg
                        ${styles.container}`}
        >
            <Icon size={18} className={`shrink-0 ${state === CONNECTION_STATES.RECOVERING ? 'animate-spin' : ''}`} aria-hidden="true" />
            <p className={`min-w-0 flex-1 text-sm font-medium ${styles.text}`}>
                {t(BANNER_KEYS[state])}
            </p>
            {state !== CONNECTION_STATES.RECOVERING && (
                <button
                    type="button"
                    onClick={() => evaluateConnectivity()}
                    className={`flex shrink-0 items-center gap-1 rounded-lg px-2.5 py-1.5
                               text-xs font-bold transition-colors ${styles.retry}`}
                >
                    <RefreshCw size={12} aria-hidden="true" />
                    {t('connectivity.retry')}
                </button>
            )}
        </div>
    );
}
