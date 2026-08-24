import { isRunningAsPWA } from '@/utils/pwa';

/**
 * Coarse client platform detection for PWA install UX.
 * The app never gates clinical behavior on this — install UI only.
 */
export function detectPlatform() {
    if (typeof navigator === 'undefined') return 'unknown';
    const ua = navigator.userAgent || '';
    const isIOS = /iPad|iPhone|iPod/.test(ua)
        || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    if (isIOS) return 'ios';
    if (/Android/.test(ua)) return 'android';
    return 'desktop';
}

export function isStandalone() {
    return isRunningAsPWA();
}

export function isIosInstallPlatform() {
    return detectPlatform() === 'ios';
}
