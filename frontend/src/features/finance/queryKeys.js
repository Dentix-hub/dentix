/**
 * Query Key Factory for DENTIX Finance V2.
 * Enables granular React Query caching and targeted invalidation.
 */

export const financeKeys = {
    all: ['finance'],

    // Overview
    overview: (filters = {}) => [...financeKeys.all, 'overview', filters],
    overviewStats: (filters = {}) => [...financeKeys.all, 'overview', 'stats', filters],
    overviewTrends: (filters = {}) => [...financeKeys.all, 'overview', 'trends', filters],

    // Patient Accounts / Receivables
    receivables: (filters = {}) => [...financeKeys.all, 'receivables', filters],
    patientAccount: (patientId, filters = {}) => [...financeKeys.all, 'receivables', 'patient', patientId, filters],

    // Payments
    payments: (filters = {}) => [...financeKeys.all, 'payments', filters],
    paymentDetails: (id) => [...financeKeys.all, 'payments', 'detail', id],

    // Expenses
    expenses: (filters = {}) => [...financeKeys.all, 'expenses', filters],
    expenseDetails: (id) => [...financeKeys.all, 'expenses', 'detail', id],
    expenseCategories: () => [...financeKeys.all, 'expenses', 'categories'],

    // Doctor Compensation
    doctors: (filters = {}) => [...financeKeys.all, 'compensation', 'doctors', filters],
    doctorRevenue: (from, to, scope) => [
        ...financeKeys.all,
        'compensation',
        'doctors',
        ...(from || to || scope ? [{ from, to, scope: scope || 'all' }] : []),
    ],
    doctorDetail: (doctorId, filters = {}) => [...financeKeys.all, 'compensation', 'doctors', doctorId, filters],
    doctorDetails: (doctorId, from, to) => [...financeKeys.all, 'compensation', 'doctors', doctorId, { from, to }],

    // Staff Payroll
    payroll: (month) => [...financeKeys.all, 'compensation', 'payroll', month],
    payrollSummary: (month) => [...financeKeys.all, 'compensation', 'payroll', 'summary', month],

    // Financial Activity Feed
    activity: (filters = {}) => [...financeKeys.all, 'activity', filters],

    // Reports
    reports: (reportType, filters = {}) => [...financeKeys.all, 'reports', reportType, filters],
};
