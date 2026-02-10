import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
    api, API_URL, login, registerClinic, getMe,
    getPatients, getPatient, createPatient, updatePatient, deletePatient,
    getAppointments, createAppointment,
    createPayment, getFinancialStats, getDashboardStats,
    getProcedures, createProcedure,
    getExpenses, createExpense,
    getNotifications
} from '../api';

// Mock axios methods
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

    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('API URL Resolution', () => {
        it('API_URL is defined and is a string', () => {
            expect(typeof API_URL).toBe('string');
        });
    });

    describe('Auth APIs', () => {
        it('login sends POST to /api/v1/token with FormData', async () => {
            await login('admin', 'pass123');
            expect(api.post).toHaveBeenCalledWith('/api/v1/token', expect.any(FormData));
        });

        it('registerClinic sends POST to /api/v1/auth/register_clinic', async () => {
            const data = { clinic_name: 'Test', admin_email: 'test@test.com' };
            await registerClinic(data);
            expect(api.post).toHaveBeenCalledWith('/api/v1/auth/register_clinic', data);
        });

        it('getMe sends GET to /api/v1/users/me/', async () => {
            await getMe();
            expect(api.get).toHaveBeenCalledWith('/api/v1/users/me/');
        });
    });

    describe('Patient APIs', () => {
        it('getPatients calls correct endpoint', async () => {
            await getPatients();
            expect(api.get).toHaveBeenCalledWith('/api/v1/patients/');
        });

        it('getPatient includes ID in URL', async () => {
            await getPatient(42);
            expect(api.get).toHaveBeenCalledWith('/api/v1/patients/42');
        });

        it('createPatient sends POST with patient data', async () => {
            const data = { name: 'Ahmed', phone: '01234567890' };
            await createPatient(data);
            expect(api.post).toHaveBeenCalledWith('/api/v1/patients/', data);
        });

        it('updatePatient sends PUT with ID and data', async () => {
            const data = { name: 'Ahmed Updated' };
            await updatePatient(5, data);
            expect(api.put).toHaveBeenCalledWith('/api/v1/patients/5', data);
        });

        it('deletePatient sends DELETE with ID', async () => {
            await deletePatient(10);
            expect(api.delete).toHaveBeenCalledWith('/api/v1/patients/10');
        });
    });

    describe('Appointment APIs', () => {
        it('getAppointments calls correct endpoint', async () => {
            await getAppointments();
            expect(api.get).toHaveBeenCalledWith('/api/v1/appointments/');
        });

        it('createAppointment sends POST', async () => {
            const data = { patient_id: 1, date: '2026-02-10' };
            await createAppointment(data);
            expect(api.post).toHaveBeenCalledWith('/api/v1/appointments/', data);
        });
    });

    describe('Financial APIs', () => {
        it('createPayment sends POST to /api/v1/payments/', async () => {
            const data = { patient_id: 1, amount: 500 };
            await createPayment(data);
            expect(api.post).toHaveBeenCalledWith('/api/v1/payments/', data);
        });

        it('getFinancialStats calls expenses/stats', async () => {
            await getFinancialStats();
            expect(api.get).toHaveBeenCalledWith('/api/v1/expenses/stats');
        });

        it('getDashboardStats calls stats/dashboard', async () => {
            await getDashboardStats();
            expect(api.get).toHaveBeenCalledWith('/api/v1/stats/dashboard');
        });
    });

    describe('Procedures APIs', () => {
        it('getProcedures calls correct endpoint', async () => {
            await getProcedures();
            expect(api.get).toHaveBeenCalledWith('/api/v1/procedures/');
        });

        it('createProcedure sends POST with data', async () => {
            const data = { name: 'Filling', price: 200 };
            await createProcedure(data);
            expect(api.post).toHaveBeenCalledWith('/api/v1/procedures/', data);
        });
    });

    describe('Expenses APIs', () => {
        it('getExpenses calls correct endpoint', async () => {
            await getExpenses();
            expect(api.get).toHaveBeenCalledWith('/api/v1/expenses/');
        });

        it('createExpense sends POST', async () => {
            const data = { description: 'Office supplies', amount: 100 };
            await createExpense(data);
            expect(api.post).toHaveBeenCalledWith('/api/v1/expenses/', data);
        });
    });

    describe('Notifications APIs', () => {
        it('getNotifications calls correct endpoint', async () => {
            await getNotifications();
            expect(api.get).toHaveBeenCalledWith('/api/v1/notifications/');
        });
    });
});
