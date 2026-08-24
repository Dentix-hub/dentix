import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Bell, BellOff } from 'lucide-react';
import {
    PUSH_SUPPORT_STATE,
    evaluatePushStatus,
    subscribeToPush,
    unsubscribeFromPush,
} from '@/pwa/push/pushClient';

/**
 * Settings → About App: explicit, user-initiated push opt-in (plan §12.4).
 * Permission is NEVER requested at page load — only from the button click.
 */
export default function PwaPushSection() {
    const { t } = useTranslation();
    const [status, setStatus] = useState(null);
    const [busy, setBusy] = useState(false);

    const refresh = () => {
        evaluatePushStatus()
            .then(setStatus)
            .catch(() => setStatus({ state: PUSH_SUPPORT_STATE.UNSUPPORTED }));
    };

    useEffect(() => {
        refresh();
    }, []);

    const handleEnable = async () => {
        setBusy(true);
        try {
            await subscribeToPush();
        } finally {
            setBusy(false);
            refresh();
        }
    };

    const handleDisable = async () => {
        setBusy(true);
        try {
            await unsubscribeFromPush();
        } finally {
            setBusy(false);
            refresh();
        }
    };

    if (!status || status.state === PUSH_SUPPORT_STATE.UNSUPPORTED) return null;

    const stateKey = `settings.push.state_${status.state}`;
    const subscribed = status.state === PUSH_SUPPORT_STATE.SUBSCRIBED;

    return (
        <div className="p-6 bg-slate-50 dark:bg-slate-900/30 rounded-2xl border border-slate-100 dark:border-white/5 mb-4">
            <div className="flex items-center gap-3 text-slate-500 mb-2">
                {subscribed ? <Bell size={20} /> : <BellOff size={20} />}
                <span className="font-bold">{t('settings.push.title')}</span>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                {t('settings.push.description')}
            </p>
            <div className="flex flex-wrap items-center gap-3">
                <span
                    className={`text-xs font-bold rounded-full px-3 py-1 ${
                        subscribed
                            ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                            : 'bg-slate-200/60 text-slate-600 dark:bg-slate-700/60 dark:text-slate-300'
                    }`}
                >
                    {t(stateKey)}
                </span>
                {subscribed ? (
                    <button
                        type="button"
                        onClick={handleDisable}
                        disabled={busy}
                        className="bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300
                                   text-sm rounded-lg px-4 py-2 hover:bg-gray-200
                                   dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
                    >
                        {t('settings.push.disable')}
                    </button>
                ) : (
                    <button
                        type="button"
                        onClick={handleEnable}
                        disabled={busy || status.state === PUSH_SUPPORT_STATE.PERMISSION_DENIED
                            || status.state === PUSH_SUPPORT_STATE.REQUIRES_INSTALL}
                        className="bg-blue-600 text-white text-sm rounded-lg px-4 py-2
                                   hover:bg-blue-700 transition-colors disabled:opacity-50"
                    >
                        {t('settings.push.enable')}
                    </button>
                )}
            </div>
            {status.state === PUSH_SUPPORT_STATE.PERMISSION_DENIED && (
                <p className="mt-3 text-xs text-amber-600 dark:text-amber-400">
                    {t('settings.push.denied_hint')}
                </p>
            )}
            {status.state === PUSH_SUPPORT_STATE.REQUIRES_INSTALL && (
                <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                    {t('settings.push.install_hint')}
                </p>
            )}
        </div>
    );
}
