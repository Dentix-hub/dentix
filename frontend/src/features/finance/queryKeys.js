/**
 * Query Key Factory for DENTIX Finance V2.
 * Shared financial truth must use the same cache identity across consumers.
 */

export const financeKeys = {
    all: ['finance'],

    // Authoritative Finance Summary — shared by Overview and Reports.
    summaryRoot: () => [...financeKeys.all, 'summary'],
    summary: (filters = {}) => [...financeKeys.summaryRoot(), filters],

    // Overview
    overview: (filters = {}) => [...financeKeys.all, 'overview', filters],
    overviewStats: (filters = {}) => financeKeys.summary(filters),
    overviewTrends: (filters = {}) => [...financeKeys.all, 'overview', 'trends', filters],

    // Patient Accounts / Receivables
    receivablesRoot: () => [...financeKeys.all, 'receivables'],
    receivables: (filters = {}) => [...financeKeys.receivablesRoot(), filters],
    patientAccount: (patientId, filters = {}) => [
        ...financeKeys.receivablesRoot(),
        'patient',
        patientId,
        filters,
    ],

    // Payments
    payments: (filters = {}) => [...financeKeys.all, 'payments', filters],
    paymentDetails: (id) => [...financeKeys.all, 'payments', 'detail', id],

    // Expenses
    expenses: (filters = {}) => [...financeKeys.all, 'expenses', filters],
    expenseDetails: (id) => [...financeKeys.all, 'expenses', 'detail', id],
    expenseCategories: () => [...financeKeys.all, 'expenses', 'categories'],

    // Doctor Compensation
    compensationRoot: () => [...financeKeys.all, 'compensation'],
    doctors: (filters = {}) => [...financeKeys.compensationRoot(), 'doctors', filters],
    doctorRevenue: (from, to, scope) => [
        ...financeKeys.compensationRoot(),
        'doctors',
        ...(from || to || scope ? [{ from, to, scope: scope || 'all' }] : []),
    ],
    doctorDetail: (doctorId, filters = {}) => [
        ...financeKeys.compensationRoot(),
        'doctors',
        doctorId,
        filters,
    ],
    doctorDetails: (doctorId, from, to) => [
        ...financeKeys.compensationRoot(),
        'doctors',
        doctorId,
        { from, to },
    ],

    // Staff Payroll
    payroll: (month) => [...financeKeys.compensationRoot(), 'payroll', month],
    payrollSummary: (month) => [
        ...financeKeys.compensationRoot(),
        'payroll',
        'summary',
        month,
    ],

    // Financial Activity Feed
    activity: (filters = {}) => [...financeKeys.all, 'activity', filters],

    // Reports
    reports: (reportType, filters = {}) => [
        ...financeKeys.all,
        'reports',
        reportType,
        filters,
    ],
};
