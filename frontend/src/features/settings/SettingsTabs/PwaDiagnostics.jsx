import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Info } from 'lucide-react';
import { BUILD_INFO, getBuildLabel } from '@/config/buildInfo';

const formatTimestamp = (value) => {
    if (!value) return '—';
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toISOString();
};

/**
 * Support-facing PWA/build diagnostics.
 * Deliberately excludes secrets, tokens, user-agent fingerprints and PHI.
 */
export default function PwaDiagnostics() {
    const { t } = useTranslation();
    const [swState, setSwState] = useState('unsupported');
    const [online, setOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);

    useEffect(() => {
        if (!('serviceWorker' in navigator)) return undefined;
        let cancelled = false;

        navigator.serviceWorker.getRegistration().then((registration) => {
            if (cancelled) return;
            if (!registration) {
                setSwState('none');
                return;
            }
            if (registration.waiting) setSwState('waiting');
            else if (registration.active) setSwState('active');
            else setSwState('preparing');
        }).catch(() => {
            if (!cancelled) setSwState('none');
        });

        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        const goOnline = () => setOnline(true);
        const goOffline = () => setOnline(false);
        window.addEventListener('online', goOnline);
        window.addEventListener('offline', goOffline);
        return () => {
            window.removeEventListener('online', goOnline);
            window.removeEventListener('offline', goOffline);
        };
    }, []);

    const standalone = typeof window !== 'undefined' && (
        window.matchMedia?.('(display-mode: standalone)').matches ||
        window.navigator.standalone === true
    );

    const notificationPermission = typeof window !== 'undefined' && 'Notification' in window
        ? Notification.permission
        : 'unsupported';

    const rows = [
        { label: t('settings.pwa.build'), value: getBuildLabel(), copyable: true },
        { label: t('settings.pwa.commit_sha'), value: BUILD_INFO.sha || 'unknown', mono: true },
        { label: t('settings.pwa.built_at'), value: formatTimestamp(BUILD_INFO.builtAt), mono: true },
        { label: t('settings.pwa.environment'), value: BUILD_INFO.environment || 'unknown' },
        { label: t('settings.pwa.origin'), value: typeof window !== 'undefined' ? window.location.origin : 'unknown', mono: true },
        { label: t('settings.pwa.display_mode'), value: standalone ? t('settings.pwa.mode_standalone') : t('settings.pwa.mode_browser') },
        { label: t('settings.pwa.service_worker'), value: t(`settings.pwa.sw_${swState}`) },
        { label: t('settings.pwa.connection'), value: online ? t('settings.pwa.online') : t('settings.pwa.offline') },
        { label: t('settings.pwa.notification_permission'), value: t(`settings.pwa.notif_${notificationPermission}`, notificationPermission) },
    ];

    return (
        <div className="space-y-4">
            <div className="p-6 bg-slate-50 dark:bg-slate-900/30 rounded-2xl border border-slate-100 dark:border-white/5">
                <div className="flex items-center gap-3 text-slate-500 mb-4">
                    <Info size={20} />
                    <span className="font-bold">{t('settings.pwa.title')}</span>
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                    {t('settings.pwa.description')}
                </p>
                <dl className="divide-y divide-slate-100 dark:divide-white/5">
                    {rows.map((row) => (
                        <div key={row.label} className="py-3 flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4">
                            <dt className="text-sm font-semibold text-slate-500 dark:text-slate-400 sm:w-56 flex-shrink-0">
                                {row.label}
                            </dt>
                            <dd
                                className={`text-sm text-slate-800 dark:text-white break-all ${row.mono ? 'font-mono' : ''}`}
                            >
                                {row.value}
                            </dd>
                        </div>
                    ))}
                </dl>
            </div>
        </div>
    );
}
