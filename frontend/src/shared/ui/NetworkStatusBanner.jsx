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
    [CONNECTION_STATES.OFFLINE]: 'bg-red-600 text-white',
    [CONNECTION_STATES.DEGRADED]: 'bg-amber-500 text-slate-900',
    [CONNECTION_STATES.RECOVERING]: 'bg-sky-600 text-white',
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
                        ${BANNER_STYLES[state]}`}
        >
            <Icon size={18} className={`shrink-0 ${state === CONNECTION_STATES.RECOVERING ? 'animate-spin' : ''}`} aria-hidden="true" />
            <p className="min-w-0 flex-1 text-sm font-medium">
                {t(BANNER_KEYS[state])}
            </p>
            {state !== CONNECTION_STATES.RECOVERING && (
                <button
                    type="button"
                    onClick={() => evaluateConnectivity()}
                    className="flex shrink-0 items-center gap-1 rounded-lg bg-black/10 px-2.5 py-1.5
                               text-xs font-bold transition-colors hover:bg-black/20"
                >
                    <RefreshCw size={12} aria-hidden="true" />
                    {t('connectivity.retry')}
                </button>
            )}
        </div>
    );
}
