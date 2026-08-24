import { useEffect, useState } from 'react';
import { detectPlatform, isStandalone } from './platform';
import {
    INSTALL_ENGAGEMENT_DELAY_MS,
    useInstallStore,
} from './installState';

/**
 * Platform-aware install orchestration (plan §9.1–§9.3).
 *
 * - Android/Chromium: captures `beforeinstallprompt` and defers the native
 *   prompt to an explicit user action.
 * - iOS/iPadOS: exposes `showIosInstructions` for the Add to Home Screen sheet.
 * - Both: honor the dismissal cooldown, `appinstalled` receipt, and the
 *   engagement delay so the UI never nags at first paint.
 */
export function usePwaInstall() {
    const platform = detectPlatform();
    const standalone = isStandalone();
    const {
        promptAvailable,
        installed,
        markPromptAvailable,
        markInstalled,
        dismiss,
        isDismissalCooldownActive,
    } = useInstallStore();
    const [deferredPrompt, setDeferredPrompt] = useState(null);
    const [engaged, setEngaged] = useState(false);

    useEffect(() => {
        const timer = window.setTimeout(() => setEngaged(true), INSTALL_ENGAGEMENT_DELAY_MS);
        return () => window.clearTimeout(timer);
    }, []);

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

    const surface = platform === 'ios' ? 'ios' : 'android';
    const cooldownActive = isDismissalCooldownActive(surface);

    const androidPromptReady = Boolean(deferredPrompt) && !standalone && !installed;
    const iosInstructionsRelevant = platform === 'ios' && !standalone && !installed;

    const canPrompt = !standalone
        && !installed
        && engaged
        && !cooldownActive
        && (androidPromptReady || iosInstructionsRelevant);

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
        standalone,
        installed,
        promptAvailable,
        androidPromptReady,
        iosInstructionsRelevant,
        canPrompt,
        promptInstall,
        dismiss: () => dismiss(surface),
    };
}
