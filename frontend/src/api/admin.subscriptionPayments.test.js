import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./apiClient', () => ({
    api: {
        get: vi.fn(),
        post: vi.fn(),
        delete: vi.fn(),
    },
}));

import { api } from './apiClient';
import {
    deleteSubscriptionPayment,
    getSubscriptionPayments,
    recordSubscriptionPayment,
    registerUser,
} from './admin';

describe('admin subscription payment API', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('uses the platform subscription payment routes, not clinic patient payments', () => {
        const payload = { tenant_id: 7, plan_id: 3, amount: 1500, payment_method: 'cash' };

        getSubscriptionPayments();
        recordSubscriptionPayment(payload);
        deleteSubscriptionPayment(12);

        expect(api.get).toHaveBeenCalledWith('/api/v1/admin/subscriptions/payments');
        expect(api.post).toHaveBeenCalledWith('/api/v1/admin/subscriptions/payments', payload);
        expect(api.delete).toHaveBeenCalledWith('/api/v1/admin/subscriptions/payments/12');
    });

    it('sends registerUser credentials, full_name, and patient_visibility_mode in JSON body instead of query params', () => {
        registerUser({
            username: 'أحمد',
            password: 'Valid#Pass89!XyZ',
            full_name: 'د. أحمد',
            role: 'doctor',
            permissions: '["view_patients"]',
            patient_visibility_mode: 'appointments_only',
        });

        expect(api.post).toHaveBeenCalledTimes(1);
        expect(api.post).toHaveBeenCalledWith('/api/v1/users/register', {
            username: 'أحمد',
            password: 'Valid#Pass89!XyZ',
            email: null,
            full_name: 'د. أحمد',
            role: 'doctor',
            permissions: '["view_patients"]',
            patient_visibility_mode: 'appointments_only',
        });
    });
});
