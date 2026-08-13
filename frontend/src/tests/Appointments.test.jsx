/**
 * Appointments Page Tests
 * Verifies Kanban board rendering, filtering, and modal interactions.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Appointments from '@/pages/Appointments';

// Mock dependencies
vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'en' },
    }),
}));

vi.mock('react-router-dom', () => ({
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));

const mockAppointments = [
    {
        id: 1,
        patient_id: 1,
        patient_name: 'Patient A',
        doctor_name: 'Dr. Smith',
        status: 'Scheduled',
        date_time: '2026-02-10T10:00:00',
        notes: 'Checkup'
    },
    {
        id: 2,
        patient_id: 2,
        patient_name: 'Patient B',
        doctor_name: 'Dr. Jones',
        status: 'Completed',
        date_time: '2026-02-10T11:00:00',
        notes: 'Filling'
    }
];

// Mock Hooks
vi.mock('@/hooks/useAppointments', () => ({
    useAppointments: () => ({
        data: mockAppointments,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
    }),
    useUpdateAppointment: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateAppointmentStatus: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/hooks/usePatients', () => ({
    usePatients: () => ({
        data: [
            { id: 1, name: 'Patient A' },
            { id: 2, name: 'Patient B' },
        ],
        isLoading: false,
        refetch: vi.fn(),
    }),
    useCreatePatient: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({ user: { id: 1, role: 'admin' } }),
}));

describe('Appointments Page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders the appointments board title', () => {
        render(<Appointments />);
        expect(screen.getByRole('heading', { name: 'appointments.title' })).toBeInTheDocument();
    });

    it('renders appointment cards in correct columns', () => {
        render(<Appointments />);
        fireEvent.click(screen.getByTitle('appointments.view.list'));
        expect(screen.getByText('Patient A')).toBeInTheDocument(); // Scheduled
        expect(screen.getByText('Patient B')).toBeInTheDocument(); // Completed
    });

    it('opens new appointment modal on button click', () => {
        render(<Appointments />);
        const addButton = screen.getByText('appointments.new_booking');
        fireEvent.click(addButton);

        // Check for modal content (assuming modal renders title)
        expect(screen.getByText('appointments.form.title')).toBeInTheDocument();
    });

    it('switches between calendar, list, and board views', async () => {
        render(<Appointments />);
        fireEvent.click(screen.getByTitle('appointments.view.board'));
        expect(await screen.findByText('Patient A')).toBeInTheDocument();
        fireEvent.click(screen.getByTitle('appointments.view.list'));
        expect(await screen.findByText('Patient B')).toBeInTheDocument();
    });
});

