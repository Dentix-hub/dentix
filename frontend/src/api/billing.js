import { api } from './apiClient';

export const createPayment = (data) => api.post('/api/v1/payments', data);
export const getPayments = (params) => (params && Object.keys(params).length > 0 ? api.get('/api/v1/payments', { params }) : api.get('/api/v1/payments'));
export const getAllPayments = (params) => (params && Object.keys(params).length > 0 ? api.get('/api/v1/payments', { params }) : api.get('/api/v1/payments'));
export const getFinancialStats = () => api.get('/api/v1/expenses/stats');
export const getDashboardStats = () => api.get('/api/v1/stats/dashboard');
export const getTodayPayments = () => api.get('/api/v1/payments/today/payments');
export const getTodayDebtors = () => api.get('/api/v1/payments/today/debtors');
export const deletePayment = (id) => api.delete(`/api/v1/payments/${id}`);

export const getExpenses = (params) => (params && Object.keys(params).length > 0 ? api.get('/api/v1/expenses', { params }) : api.get('/api/v1/expenses'));
export const createExpense = (data) => api.post('/api/v1/expenses', data);
export const deleteExpense = (id) => api.delete(`/api/v1/expenses/${id}`);
