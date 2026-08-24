/**
 * Standards-based Web Push client (plan §12.4–§12.5).
 *
 * Rules enforced here:
 * - Permission is requested ONLY from an explicit user action (never at load).
 * - The subscription is registered with the backend after creation and
 *   revoked on unsubscribe/logout.
 * - Unsupported browsers degrade gracefully; iOS requires Home Screen install.
 */

import logger from '@/utils/logger';
import {
    listMyPushSubscriptions,
    registerPushSubscription,
    revokePushSubscription,
} from '@/api/push';

const VAPID_PUBLIC_KEY_ENV = 'VITE_VAPID_PUBLIC_KEY';

// Read lazily so tests (and runtime env injection) observe the current value.
function getVapidPublicKey() {
    return import.meta.env[VAPID_PUBLIC_KEY_ENV] || '';
}

export const PUSH_SUPPORT_STATE = {
    UNSUPPORTED: 'unsupported',
    REQUIRES_INSTALL: 'requires_install', // iOS browser tab (not standalone)
    PERMISSION_DENIED: 'permission_denied',
    NOT_SUBSCRIBED: 'not_subscribed',
    SUBSCRIBED: 'subscribed',
    STALE: 'stale',
};

export function isPushSupported() {
    return typeof window !== 'undefined'
        && 'serviceWorker' in navigator
        && 'PushManager' in window
        && 'Notification' in window;
}

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const normalized = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(normalized);
    const output = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) output[i] = raw.charCodeAt(i);
    return output;
}

function detectPlatform() {
    const ua = navigator.userAgent || '';
    if (/iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) return 'ios';
    if (/Android/.test(ua)) return 'android';
    return 'desktop';
}

function detectBrowserFamily() {
    const ua = navigator.userAgent || '';
    if (/Edg\//.test(ua)) return 'edge';
    if (/SamsungBrowser/.test(ua)) return 'samsung';
    if (/Chrome\//.test(ua)) return 'chrome';
    if (/Firefox\//.test(ua)) return 'firefox';
    if (/Safari\//.test(ua)) return 'safari';
    return 'unknown';
}

async function getRegistration() {
    return navigator.serviceWorker.getRegistration();
}

export function getPermissionState() {
    if (!isPushSupported()) return 'unsupported';
    return Notification.permission;
}

/**
 * Evaluate the current installation's push status without prompting.
 */
export async function evaluatePushStatus() {
    if (!isPushSupported()) return { state: PUSH_SUPPORT_STATE.UNSUPPORTED };

    const isStandalone = window.matchMedia?.('(display-mode: standalone)').matches
        || window.navigator.standalone === true;
    if (detectPlatform() === 'ios' && !isStandalone) {
        // iOS/iPadOS only deliver Web Push to installed Home Screen web apps.
        return { state: PUSH_SUPPORT_STATE.REQUIRES_INSTALL };
    }

    if (Notification.permission === 'denied') {
        return { state: PUSH_SUPPORT_STATE.PERMISSION_DENIED };
    }
    if (!getVapidPublicKey()) {
        logger.warn('[PUSH] VITE_VAPID_PUBLIC_KEY not configured.');
        return { state: PUSH_SUPPORT_STATE.UNSUPPORTED };
    }

    const registration = await getRegistration();
    if (!registration) return { state: PUSH_SUPPORT_STATE.NOT_SUBSCRIBED };

    const subscription = await registration.pushManager.getSubscription();
    if (!subscription) return { state: PUSH_SUPPORT_STATE.NOT_SUBSCRIBED };

    const serverList = await listMyPushSubscriptions()
        .then((res) => res.data)
        .catch(() => null);
    if (serverList && !serverList.some((item) => item.endpoint === subscription.endpoint)) {
        // Browser has a subscription the server does not know about.
        return { state: PUSH_SUPPORT_STATE.STALE, subscription };
    }
    return { state: PUSH_SUPPORT_STATE.SUBSCRIBED, subscription };
}

/**
 * Ask permission + create the browser subscription + register it server-side.
 * MUST only be invoked from an explicit user gesture.
 */
export async function subscribeToPush() {
    if (!isPushSupported()) return { ok: false, reason: PUSH_SUPPORT_STATE.UNSUPPORTED };
    if (!getVapidPublicKey()) return { ok: false, reason: PUSH_SUPPORT_STATE.UNSUPPORTED };

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return { ok: false, reason: permission };

    const registration = await getRegistration();
    if (!registration) return { ok: false, reason: PUSH_SUPPORT_STATE.NOT_SUBSCRIBED };

    const existing = await registration.pushManager.getSubscription();
    const subscription = existing || await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(getVapidPublicKey()),
    });

    const json = subscription.toJSON();
    await registerPushSubscription({
        endpoint: json.endpoint,
        keys: {
            p256dh: json.keys.p256dh,
            auth: json.keys.auth,
        },
        provider: 'web_push',
        platform: detectPlatform(),
        browser_family: detectBrowserFamily(),
    });
    return { ok: true, subscription };
}

/**
 * Revoke one installation: unsubscribe in the browser + delete server-side.
 */
export async function unsubscribeFromPush() {
    const registration = await getRegistration();
    const subscription = registration ? await registration.pushManager.getSubscription() : null;
    if (!subscription) return { ok: true };

    const serverList = await listMyPushSubscriptions()
        .then((res) => res.data)
        .catch(() => []);
    const match = serverList.find((item) => item.endpoint === subscription.endpoint);
    if (match) await revokePushSubscription(match.id);

    await subscription.unsubscribe();
    return { ok: true };
}
