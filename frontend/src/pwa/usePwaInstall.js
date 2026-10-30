import { useEffect, useState } from 'react';
import { detectPlatform, isInAppBrowser, isStandalone } from './platform';
import {
    INSTALL_ENGAGEMENT_DELAY_MS,
    useInstallStore,
} from './installState';

/**
 * Platform-aware install orchestration (plan §9.1–§9.3).
 *
 * - Android/Chromium: captures `beforeinstallprompt` and defers the native
 *   prompt to an explicit user action; falls back to manual instructions
 *   if no prompt arrives.
 * - iOS/iPadOS: exposes `iosInstructionsRelevant` for the Add to Home Screen sheet.
 * - In-app browsers: shows open-in-browser advice card.
 * - All: honor the dismissal cooldown, `appinstalled` receipt, and the
 *   engagement delay so the UI never nags at first paint.
 */
export function usePwaInstall() {
    const platform = detectPlatform();
    const inApp = isInAppBrowser();
    const standalone = isStandalone();
    const {
        promptAvailable,
        installed,
        markPromptAvailable,
        markInstalled,
        dismiss,
        isDismissalCooldownActive,
        syncInstalledState,
    } = useInstallStore();
    const [deferredPrompt, setDeferredPrompt] = useState(null);
    const [engaged, setEngaged] = useState(false);

    useEffect(() => {
        syncInstalledState?.();
        const timer = window.setTimeout(() => setEngaged(true), INSTALL_ENGAGEMENT_DELAY_MS);
        return () => window.clearTimeout(timer);
    }, [syncInstalledState]);

    useEffect(() => {
        const onPrompt = (event) => {
            event.preventDefault();
            setDeferredPrompt(event);
            markPromptAvailable();
        };
        const onInstalled = () => {
            markInstalled();
            setDeferredPrompt(null);
        };
        window.addEventListener('beforeinstallprompt', onPrompt);
        window.addEventListener('appinstalled', onInstalled);
        return () => {
            window.removeEventListener('beforeinstallprompt', onPrompt);
            window.removeEventListener('appinstalled', onInstalled);
        };
    }, [markPromptAvailable, markInstalled]);

    const surface = inApp ? 'inapp' : (platform === 'ios' ? 'ios' : 'android');
    const cooldownActive = isDismissalCooldownActive(surface);

    const inAppNoticeRelevant = inApp && !standalone && !installed;
    const androidPromptReady = !inApp && Boolean(deferredPrompt) && !standalone && !installed;
    const androidManualRelevant = !inApp && platform === 'android' && !deferredPrompt && !standalone && !installed;
    const iosInstructionsRelevant = !inApp && platform === 'ios' && !standalone && !installed;

    const canPrompt = !standalone
        && !installed
        && engaged
        && !cooldownActive
        && (inAppNoticeRelevant || androidPromptReady || androidManualRelevant || iosInstructionsRelevant);

    const promptInstall = async () => {
        if (!deferredPrompt) return 'unavailable';
        deferredPrompt.prompt();
        try {
            const { outcome } = await deferredPrompt.userChoice;
            if (outcome === 'accepted') {
                // `appinstalled` also fires; this covers browsers that skip it.
                markInstalled();
                return 'accepted';
            }
            dismiss('android');
            return outcome;
        } finally {
            setDeferredPrompt(null);
        }
    };

    return {
        platform,
        inApp,
        standalone,
        installed,
        promptAvailable,
        inAppNoticeRelevant,
        androidPromptReady,
        androidManualRelevant,
        iosInstructionsRelevant,
        canPrompt,
        promptInstall,
        dismiss: () => dismiss(surface),
    };
}
