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
    patientStatement: (patientId, filters = {}) => [
        ...financeKeys.receivablesRoot(),
        'statement',
        patientId,
        filters,
    ],

    // Payments
    paymentsRoot: () => [...financeKeys.all, 'payments'],
    payments: (filters = {}) => [...financeKeys.paymentsRoot(), filters],
    paymentDetails: (id) => [...financeKeys.paymentsRoot(), 'detail', id],

    // Expenses
    expensesRoot: () => [...financeKeys.all, 'expenses'],
    expenses: (filters = {}) => [...financeKeys.expensesRoot(), filters],
    expenseDetails: (id) => [...financeKeys.expensesRoot(), 'detail', id],
    expenseCategories: () => [...financeKeys.expensesRoot(), 'categories'],

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
    activityRoot: () => [...financeKeys.all, 'activity'],
    activity: (filters = {}) => [...financeKeys.activityRoot(), filters],

    // Reports
    reportsRoot: () => [...financeKeys.all, 'reports'],
    reports: (reportType, filters = {}) => [
        ...financeKeys.reportsRoot(),
        reportType,
        filters,
    ],
};
