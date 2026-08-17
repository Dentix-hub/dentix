import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 30 * 1000,
            gcTime: 5 * 60 * 1000,
            refetchOnWindowFocus: false,
            retry: 1,
            refetchOnReconnect: false,
        },
        mutations: {
            retry: 1,
        },
    },
});

export const queryKeys = {
    patients: ['patients'],
    patientDirectory: (filters = {}) => ['patients', 'directory', filters],
    patientSearch: (query) => ['patients', 'search', query],
    patient: (id) => ['patient', id],
    patientTeeth: (id) => ['patient', id, 'teeth'],
    patientTreatments: (id) => ['patient', id, 'treatments'],
    patientPayments: (id) => ['patient', id, 'payments'],
    patientAttachments: (id) => ['patient', id, 'attachments'],

    dashboardStats: ['dashboard', 'stats'],
    todayPayments: ['dashboard', 'todayPayments'],
    todayDebtors: ['dashboard', 'todayDebtors'],
    appointments: ['appointments'],
    financialStats: ['financial', 'stats'],
    allPayments: ['payments'],
    expenses: ['expenses'],
    procedures: ['procedures'],
    users: ['users'],
    labs: ['labs'],
};
