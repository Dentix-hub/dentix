/**
 * Appointments Page Tests
 * Verifies page rendering and modal interactions against the current hook architecture.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Appointments from '@/pages/Appointments';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar', changeLanguage: vi.fn() },
    }),
}));

vi.mock('react-router-dom', () => ({
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({
        user: { id: 1, role: 'admin', tenant_id: 1 },
    }),
}));

// Keep this page test focused on Dentix behavior rather than FullCalendar internals.
// The real calendar owns observers/listeners/timers that are irrelevant to these unit assertions.
vi.mock('@/shared/ui/WeeklyCalendar', () => ({
    default: () => <div data-testid="weekly-calendar">Weekly Calendar</div>,
}));

const mockAppointments = [
    { id: 1, patient_name: 'Patient A', doctor_name: 'Dr. Smith', status: 'Scheduled', date_time: '2026-02-10T10:00:00', notes: 'Checkup' },
    { id: 2, patient_name: 'Patient B', doctor_name: 'Dr. Jones', status: 'Completed', date_time: '2026-02-10T11:00:00', notes: 'Filling' }
];

vi.mock('@/hooks/useAppointments', () => ({
    useAppointments: () => ({
        data: mockAppointments,
        appointments: mockAppointments,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
    }),
    useUpdateAppointmentStatus: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateAppointment: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/hooks/usePatients', () => ({
    usePatients: () => ({ data: [], patients: [], isLoading: false, refetch: vi.fn() }),
    useCreatePatient: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe('Appointments Page', () => {
    beforeEach(() => vi.clearAllMocks());

    it('renders the appointments page and calendar view', () => {
        render(<Appointments />);
        expect(screen.getByText('appointments.title')).toBeInTheDocument();
        expect(screen.getByTestId('weekly-calendar')).toBeInTheDocument();
    });

    it('opens the new appointment flow', () => {
        render(<Appointments />);
        fireEvent.click(screen.getByText('appointments.new_booking'));
        expect(screen.getByText('appointments.form.title')).toBeInTheDocument();
    });
});
