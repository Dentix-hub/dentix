/**
 * Appointments Page Tests
 * Verifies page rendering and modal interactions against the current hook architecture.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Appointments from '@/pages/Appointments';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({ t: (key) => key }),
}));

vi.mock('react-router-dom', () => ({
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({
        user: { id: 1, role: 'admin', tenant_id: 1 },
    }),
}));

const mockAppointments = [
    { id: 1, patient_name: 'Patient A', doctor_name: 'Dr. Smith', status: 'scheduled', date_time: '2026-02-10T10:00:00', notes: 'Checkup' },
    { id: 2, patient_name: 'Patient B', doctor_name: 'Dr. Jones', status: 'completed', date_time: '2026-02-10T11:00:00', notes: 'Filling' }
];

vi.mock('@/hooks/useAppointments', () => ({
    useAppointments: () => ({ data: mockAppointments, appointments: mockAppointments, isLoading: false, error: null }),
    useUpdateAppointmentStatus: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateAppointment: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/hooks/usePatients', () => ({
    usePatients: () => ({ data: [], patients: [], isLoading: false }),
    useCreatePatient: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe('Appointments Page', () => {
    beforeEach(() => vi.clearAllMocks());

    it('renders the appointments page', () => {
        render(<Appointments />);
        expect(screen.getByText('appointments.title')).toBeInTheDocument();
    });

    it('opens the new appointment flow', () => {
        render(<Appointments />);
        const addButton = screen.getByText('appointments.new_appointment');
        fireEvent.click(addButton);
        expect(screen.getByText('appointments.new_modal_title')).toBeInTheDocument();
    });
});
