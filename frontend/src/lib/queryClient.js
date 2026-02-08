import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            // Data stays fresh for 30 seconds
            staleTime: 30 * 1000,
            // Keep unused data for 5 minutes
            gcTime: 5 * 60 * 1000,
            // Don't refetch on window focus (annoying in medical apps)
            refetchOnWindowFocus: false,
            // Retry failed requests once
            retry: 1,
            // Don't refetch on reconnect by default
            refetchOnReconnect: false,
        },
        mutations: {
            // Retry mutations once
            retry: 1,
        },
    },
});

// Query Keys - centralized for easy invalidation
export const queryKeys = {
    // Patients
    patients: ['patients'],
    patient: (id) => ['patient', id],
    patientTeeth: (id) => ['patient', id, 'teeth'],
    patientTreatments: (id) => ['patient', id, 'treatments'],
    patientPayments: (id) => ['patient', id, 'payments'],
    patientAttachments: (id) => ['patient', id, 'attachments'],

    // Dashboard
    dashboardStats: ['dashboard', 'stats'],
    todayPayments: ['dashboard', 'todayPayments'],
    todayDebtors: ['dashboard', 'todayDebtors'],

    // Appointments
    appointments: ['appointments'],

    // Financial
    financialStats: ['financial', 'stats'],
    allPayments: ['payments'],
    expenses: ['expenses'],

    // Settings
    procedures: ['procedures'],
    users: ['users'],

    // Labs
    labs: ['labs'],
};
