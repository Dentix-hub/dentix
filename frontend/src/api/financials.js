import { api } from './apiClient';

export const getProcedureFinancials = (procedureId) => {
    return api.get(`/api/v1/financials/procedure/${procedureId}/analysis`);
};

export const getAllProceduresFinancials = () => {
    return api.get(`/api/v1/financials/procedures/analysis`);
};

// Accounting
export const getAccounts = (type = null) => api.get(`/api/v1/accounting/accounts${type ? `?account_type=${type}` : ''}`);
export const getAccountsTree = () => api.get('/api/v1/accounting/accounts/tree');
export const createAccount = (data) => api.post('/api/v1/accounting/accounts', data);
export const updateAccount = (id, data) => api.put(`/api/v1/accounting/accounts/${id}`, data);
export const deleteAccount = (id) => api.delete(`/api/v1/accounting/accounts/${id}`);
export const getAccountBalance = (id, date = null) => api.get(`/api/v1/accounting/accounts/${id}/balance${date ? `?as_of_date=${date}` : ''}`);
export const getAccountLedger = (id, params) => api.get(`/api/v1/accounting/accounts/${id}/ledger`, { params });

// Journal Entries
export const getJournals = () => api.get('/api/v1/accounting/journals');
export const getJournalEntries = (params) => api.get('/api/v1/accounting/journal-entries', { params });
export const createJournalEntry = (data) => api.post('/api/v1/accounting/journal-entries', data);
export const getJournalEntry = (id) => api.get(`/api/v1/accounting/journal-entries/${id}`);
export const updateJournalEntry = (id, data) => api.put(`/api/v1/accounting/journal-entries/${id}`, data);
export const postJournalEntry = (id, data) => api.post(`/api/v1/accounting/journal-entries/${id}/post`, data);
export const voidJournalEntry = (id, data) => api.post(`/api/v1/accounting/journal-entries/${id}/void`, data);

// Reports
export const getTrialBalance = (date = null) => api.get(`/api/v1/accounting/reports/trial-balance${date ? `?as_of_date=${date}` : ''}`);
export const getDoctorRevenue = (start, end) => api.get('/api/v1/accounting/doctor-revenue', { params: { start_date: start, end_date: end } });
export const getDoctorDetails = (id, start, end) => api.get(`/api/v1/accounting/doctor-details/${id}`, { params: { start_date: start, end_date: end } });
export const updateStaffCompensation = (userId, commission, salary, perAppointment = 0) => api.put(`/api/v1/accounting/staff-compensation/${userId}`, null, { params: { commission_percent: commission, fixed_salary: salary, per_appointment_fee: perAppointment } });
export const getStaffRevenue = (start, end) => api.get('/api/v1/accounting/staff-revenue', { params: { start_date: start, end_date: end } });
export const getComprehensiveStats = (start, end) => api.get('/api/v1/accounting/comprehensive-stats', { params: { start_date: start, end_date: end } });

// Salary Payments
export const getSalariesStatus = (month) => api.get('/api/v1/accounting/salaries', { params: { month } });
export const recordSalaryPayment = (userId, month, amount, isPartial = false, daysWorked = null, notes = null) =>
    api.post('/api/v1/accounting/salaries', null, { params: { user_id: userId, month, amount, is_partial: isPartial, days_worked: daysWorked, notes } });
export const deleteSalaryPayment = (paymentId) => api.delete(`/api/v1/accounting/salaries/${paymentId}`);
export const updateHireDate = (userId, hireDate) => api.put(`/api/v1/accounting/staff/${userId}/hire-date`, null, { params: { hire_date: hireDate } });

