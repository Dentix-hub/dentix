import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    PUSH_SUPPORT_STATE,
    evaluatePushStatus,
    subscribeToPush,
    unsubscribeFromPush,
} from './pushClient';

const apiMocks = vi.hoisted(() => ({
    registerPushSubscription: vi.fn().mockResolvedValue({ data: {} }),
    listMyPushSubscriptions: vi.fn().mockResolvedValue({ data: [] }),
    revokePushSubscription: vi.fn().mockResolvedValue({ data: {} }),
}));

vi.mock('@/api/push', () => ({
    registerPushSubscription: apiMocks.registerPushSubscription,
    listMyPushSubscriptions: apiMocks.listMyPushSubscriptions,
    revokePushSubscription: apiMocks.revokePushSubscription,
    refreshPushSubscription: vi.fn(),
    revokeAllPushSubscriptions: vi.fn(),
}));

const originalNavigator = window.navigator;

function installPushEnvironment({
    permission = 'default',
    standalone = false,
    userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36',
    subscription = null,
    hasRegistration = true,
} = {}) {
    Object.defineProperty(window, 'navigator', {
        value: {
            ...originalNavigator,
            userAgent,
            platform: 'Win32',
            maxTouchPoints: 0,
            serviceWorker: hasRegistration
                ? {
                    getRegistration: vi.fn().mockResolvedValue({
                        pushManager: {
                            getSubscription: vi.fn().mockResolvedValue(subscription),
                            subscribe: vi.fn().mockResolvedValue(subscription),
                        },
                    }),
                }
                : undefined,
        },
        configurable: true,
    });
    window.Notification = { permission, requestPermission: vi.fn().mockResolvedValue(permission) };
    window.PushManager = function PushManager() {};
    window.matchMedia = vi.fn().mockImplementation((query) => ({
        matches: standalone && query === '(display-mode: standalone)',
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
    }));
}

function fakeSubscription(endpoint = 'https://push.example/sub-1') {
    return {
        endpoint,
        toJSON: () => ({
            endpoint,
            keys: { p256dh: 'p256dh', auth: 'auth' },
        }),
        unsubscribe: vi.fn().mockResolvedValue(true),
    };
}

beforeEach(() => {
    vi.stubEnv('VITE_VAPID_PUBLIC_KEY', 'BTestPublicKeyTestPublicKeyTestPublicKeyTest');
    apiMocks.registerPushSubscription.mockClear();
    apiMocks.listMyPushSubscriptions.mockResolvedValue({ data: [] });
    apiMocks.revokePushSubscription.mockClear();
});

afterEach(() => {
    Object.defineProperty(window, 'navigator', { value: originalNavigator, configurable: true });
    delete window.Notification;
    delete window.PushManager;
    vi.unstubAllEnvs();
});

describe('push client (plan §12.4–12.5)', () => {
    it('reports unsupported when PushManager is missing', async () => {
        installPushEnvironment();
        delete window.PushManager;
        const status = await evaluatePushStatus();
        expect(status.state).toBe(PUSH_SUPPORT_STATE.UNSUPPORTED);
    });

    it('requires Home Screen install on iOS browser tabs', async () => {
        installPushEnvironment({
            userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1',
            standalone: false,
        });
        const status = await evaluatePushStatus();
        expect(status.state).toBe(PUSH_SUPPORT_STATE.REQUIRES_INSTALL);
    });

    it('reports denied without prompting', async () => {
        installPushEnvironment({ permission: 'denied' });
        const status = await evaluatePushStatus();
        expect(status.state).toBe(PUSH_SUPPORT_STATE.PERMISSION_DENIED);
        expect(window.Notification.requestPermission).not.toHaveBeenCalled();
    });

    it('subscribes only after permission is granted and registers server-side', async () => {
        installPushEnvironment({ permission: 'granted', subscription: fakeSubscription() });
        const result = await subscribeToPush();

        expect(result.ok).toBe(true);
        expect(window.Notification.requestPermission).toHaveBeenCalled();
        expect(apiMocks.registerPushSubscription).toHaveBeenCalledWith(
            expect.objectContaining({
                endpoint: 'https://push.example/sub-1',
                keys: { p256dh: 'p256dh', auth: 'auth' },
                provider: 'web_push',
                platform: 'desktop',
            }),
        );
    });

    it('flags a browser subscription the server does not know as stale', async () => {
        installPushEnvironment({
            permission: 'granted',
            subscription: fakeSubscription('https://push.example/unknown'),
        });
        apiMocks.listMyPushSubscriptions.mockResolvedValue({
            data: [{ endpoint: 'https://push.example/other', id: 2 }],
        });

        const status = await evaluatePushStatus();
        expect(status.state).toBe(PUSH_SUPPORT_STATE.STALE);
    });

    it('revokes server-side then unsubscribes the browser installation', async () => {
        const subscription = fakeSubscription('https://push.example/sub-9');
        installPushEnvironment({ subscription });
        apiMocks.listMyPushSubscriptions.mockResolvedValue({
            data: [{ endpoint: 'https://push.example/sub-9', id: 7 }],
        });

        const result = await unsubscribeFromPush();
        expect(result.ok).toBe(true);
        expect(apiMocks.revokePushSubscription).toHaveBeenCalledWith(7);
        expect(subscription.unsubscribe).toHaveBeenCalled();
    });
});
