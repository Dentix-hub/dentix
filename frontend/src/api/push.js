import { api } from './apiClient';

/**
 * Push subscription API (plan §12.3).
 * Identity fields are derived server-side from the authenticated session.
 */

export function registerPushSubscription(payload) {
    return api.post('/push/subscriptions', payload);
}

export function listMyPushSubscriptions() {
    return api.get('/push/subscriptions/me');
}

export function refreshPushSubscription(payload) {
    return api.post('/push/subscriptions/refresh', payload);
}

export function revokePushSubscription(subscriptionId) {
    return api.delete(`/push/subscriptions/${subscriptionId}`);
}

export function revokeAllPushSubscriptions() {
    return api.delete('/push/subscriptions');
}
