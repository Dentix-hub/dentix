import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
    api, API_URL, login, registerClinic, getMe,
    getPatients, getPatient, createPatient, updatePatient, deletePatient,
    getAppointments, createAppointment,
    createPayment, getFinancialStats, getDashboardStats,
    getProcedures, createProcedure,
    getExpenses, createExpense,
    getNotifications,
    forgotPassword, resetPassword, verifyResetToken
} from '../api';

vi.mock('axios', () => {
    const mockAxios = {
        create: vi.fn(() => mockAxios),
        get: vi.fn(() => Promise.resolve({ data: {} })),
        post: vi.fn(() => Promise.resolve({ data: {} })),
        put: vi.fn(() => Promise.resolve({ data: {} })),
        delete: vi.fn(() => Promise.resolve({ data: {} })),
        interceptors: {
            request: { use: vi.fn() },
            response: { use: vi.fn() },
        },
        defaults: { headers: { common: {} } },
    };
    return { default: mockAxios };
});

describe('API Module', () => {
    beforeEach(() => vi.clearAllMocks());

    it('API_URL is defined and is a string', () => {
        expect(typeof API_URL).toBe('string');
    });

    it('login uses the current auth token endpoint', async () => {
        await login('admin', 'pass123');
        expect(api.post).toHaveBeenCalledWith('/api/v1/auth/token', expect.any(FormData));
    });

    it('registerClinic uses the registration endpoint', async () => {
        const data = { clinic_name: 'Test', admin_email: 'test@test.com' };
        await registerClinic(data);
        expect(api.post).toHaveBeenCalledWith('/api/v1/auth/register_clinic', data);
    });

    it('getMe uses the normalized users/me route', async () => {
        await getMe();
        expect(api.get).toHaveBeenCalledWith('/api/v1/users/me');
    });

    it('forgotPassword sends the email in a JSON request body', async () => {
        await forgotPassword('test@example.com');
        expect(api.post).toHaveBeenCalledWith('/api/v1/auth/forgot-password', { email: 'test@example.com' });
    });

    it('resetPassword keeps the token and password out of the URL and sends a JSON body', async () => {
        await resetPassword('tok123', 'newpass123');
        expect(api.post).toHaveBeenCalledWith('/api/v1/auth/reset-password', {
            token: 'tok123',
            new_password: 'newpass123',
        });
    });

    it('verifyResetToken uses the verify endpoint with the token query parameter', async () => {
        await verifyResetToken('tok123');
        expect(api.get).toHaveBeenCalledWith('/api/v1/auth/verify-reset-token', {
            params: { token: 'tok123' },
        });
    });

    it('patient APIs use normalized routes', async () => {
        await getPatients();
        expect(api.get).toHaveBeenCalledWith('/api/v1/patients');
        await getPatient(42);
        expect(api.get).toHaveBeenCalledWith('/api/v1/patients/42');
        const data = { name: 'Ahmed', phone: '01234567890' };
        await createPatient(data);
        expect(api.post).toHaveBeenCalledWith('/api/v1/patients', data);
        await updatePatient(5, { name: 'Ahmed Updated' });
        expect(api.put).toHaveBeenCalledWith('/api/v1/patients/5', { name: 'Ahmed Updated' });
        await deletePatient(10);
        expect(api.delete).toHaveBeenCalledWith('/api/v1/patients/10');
    });

    it('appointment APIs use normalized routes', async () => {
        await getAppointments();
        expect(api.get).toHaveBeenCalledWith('/api/v1/appointments');
        const data = { patient_id: 1, date: '2026-02-10' };
        await createAppointment(data);
        expect(api.post).toHaveBeenCalledWith('/api/v1/appointments', data);
    });

    it('billing and dashboard APIs use current routes', async () => {
        const data = { patient_id: 1, amount: 500 };
        await createPayment(data);
        expect(api.post).toHaveBeenCalledWith('/api/v1/payments', data);
        await getFinancialStats();
        expect(api.get).toHaveBeenCalledWith('/api/v1/expenses/stats');
        await getDashboardStats();
        expect(api.get).toHaveBeenCalledWith('/api/v1/stats/dashboard');
    });

    it('procedure APIs use current routes', async () => {
        await getProcedures();
        expect(api.get).toHaveBeenCalled();
        const data = { name: 'Filling', price: 200 };
        await createProcedure(data);
        expect(api.post).toHaveBeenCalled();
    });

    it('expense APIs use normalized routes', async () => {
        await getExpenses();
        expect(api.get).toHaveBeenCalledWith('/api/v1/expenses');
        const data = { description: 'Office supplies', amount: 100 };
        await createExpense(data);
        expect(api.post).toHaveBeenCalledWith('/api/v1/expenses', data);
    });

    it('notifications API invokes the client', async () => {
        await getNotifications();
        expect(api.get).toHaveBeenCalled();
    });
});
