/**
 * Appointments Page Tests
 * Verifies page rendering and modal interactions against the current hook architecture.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import Appointments from '@/pages/Appointments';
import { toast } from '@/shared/ui';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => fallback || key,
        i18n: { language: 'ar', changeLanguage: vi.fn() },
    }),
}));

vi.mock('react-router-dom', () => ({
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        useQuery: () => ({ data: [{ id: 10, name: 'Dr. Smith' }], isLoading: false }),
    };
});

vi.mock('@/api/admin', () => ({
    getDoctors: vi.fn().mockResolvedValue({ data: [{ id: 10, name: 'Dr. Smith' }] }),
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({
        user: { id: 1, role: 'admin', tenant_id: 1 },
    }),
}));

vi.mock('@/shared/ui', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        toast: {
            loading: vi.fn().mockReturnValue('toast-id'),
            success: vi.fn(),
            error: vi.fn(),
        },
    };
});

// Keep this page test focused on Dentix behavior rather than FullCalendar internals.
// The real calendar owns observers/listeners/timers that are irrelevant to these unit assertions.
// The adapter contract (onEventClick receives the appointment) is exercised here; the
// actual FullCalendar click/tap path is covered by the focused Playwright spec.
vi.mock('@/shared/ui/WeeklyCalendar', () => ({
    default: ({ appointments = [], onEventClick }) => (
        <div data-testid="weekly-calendar">
            {appointments.map((appt) => (
                <button
                    key={appt.id}
                    type="button"
                    data-testid={`calendar-event-${appt.id}`}
                    onClick={() => onEventClick?.(appt)}
                >
                    {appt.patient_name}
                </button>
            ))}
        </div>
    ),
}));

const mockAppointments = [
    { id: 1, patient_id: 101, patient_name: 'Patient A', doctor_name: 'Dr. Smith', status: 'Scheduled', date_time: '2026-02-10T10:00:00', notes: 'Checkup' },
    { id: 2, patient_id: 102, patient_name: 'Patient B', doctor_name: 'Dr. Jones', status: 'Completed', date_time: '2026-02-10T11:00:00', notes: 'Filling' }
];

const mockUpdateMutateAsync = vi.fn();
const mockRefetch = vi.fn();

vi.mock('@/hooks/useAppointments', () => ({
    useAppointments: () => ({
        data: mockAppointments,
        appointments: mockAppointments,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
    }),
    useUpdateAppointmentStatus: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateAppointment: () => ({ mutateAsync: mockUpdateMutateAsync, isPending: false }),
    useNextVisitRequests: () => ({ data: [], isLoading: false, refetch: vi.fn() }),
    useScheduleNextVisitRequest: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useCancelNextVisitRequest: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/hooks/usePatients', () => ({
    usePatients: () => ({
        data: [
            { id: 101, name: 'Patient A' },
            { id: 102, name: 'Patient B' },
        ],
        patients: [
            { id: 101, name: 'Patient A' },
            { id: 102, name: 'Patient B' },
        ],
        isLoading: false,
        refetch: vi.fn()
    }),
    useSearchPatients: () => ({
        data: [],
        isLoading: false,
        isFetching: false,
        isError: false,
        error: null,
    }),
    useCreatePatient: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe('Appointments Page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUpdateMutateAsync.mockResolvedValue({ data: { success: true } });
    });

    it('renders the appointments page and calendar view', () => {
        render(<Appointments />);
        expect(screen.getByRole('heading', { name: 'appointments.title', level: 1 })).toBeInTheDocument();
        expect(screen.getByTestId('weekly-calendar')).toBeInTheDocument();
    });

    it('opens the new appointment flow', () => {
        render(<Appointments />);
        fireEvent.click(screen.getByText('appointments.new_booking'));
        expect(screen.getByText('appointments.form.title')).toBeInTheDocument();
    });

    it('switches to list view and opens edit appointment modal', async () => {
        render(<Appointments />);
        // Switch to list view
        const listButton = screen.getByTitle('appointments.view.list');
        fireEvent.click(listButton);

        // Find Edit buttons
        const editButtons = screen.getAllByLabelText('appointments.actions.edit');
        expect(editButtons.length).toBeGreaterThan(0);
        fireEvent.click(editButtons[0]);

        // Edit modal should open
        expect(screen.getByText('appointments.edit_form.title')).toBeInTheDocument();

        // Submit edit
        const saveButton = screen.getByText('appointments.edit_form.save_btn');
        fireEvent.click(saveButton);

        await waitFor(() => {
            expect(mockUpdateMutateAsync).toHaveBeenCalledWith(
                expect.objectContaining({
                    id: 1,
                    data: expect.objectContaining({
                        duration_minutes: 30,
                    }),
                })
            );
        });
    });

    it('opens the matching edit modal for each calendar event and closes without mutating', async () => {
        render(<Appointments />);

        fireEvent.click(screen.getByTestId('calendar-event-1'));
        let dialog = screen.getByRole('dialog');
        expect(within(dialog).getByText('appointments.edit_form.title')).toBeInTheDocument();
        expect(within(dialog).getByText('Patient A')).toBeInTheDocument();
        expect(within(dialog).getByDisplayValue('Checkup')).toBeInTheDocument();
        fireEvent.click(within(dialog).getByText('appointments.edit_form.cancel_btn'));
        await waitFor(() => {
            expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        });

        fireEvent.click(screen.getByTestId('calendar-event-2'));
        dialog = screen.getByRole('dialog');
        expect(within(dialog).getByText('appointments.edit_form.title')).toBeInTheDocument();
        expect(within(dialog).getByText('Patient B')).toBeInTheDocument();
        expect(within(dialog).getByDisplayValue('Filling')).toBeInTheDocument();
        fireEvent.click(within(dialog).getByText('appointments.edit_form.cancel_btn'));
        await waitFor(() => {
            expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        });

        expect(mockUpdateMutateAsync).not.toHaveBeenCalled();
    });

    it('saves a calendar-opened appointment exactly once for the selected record', async () => {
        render(<Appointments />);

        fireEvent.click(screen.getByTestId('calendar-event-2'));
        const dialog = screen.getByRole('dialog');
        fireEvent.change(within(dialog).getByDisplayValue('Filling'), {
            target: { value: 'Filling updated from calendar' },
        });
        fireEvent.click(within(dialog).getByText('appointments.edit_form.save_btn'));

        await waitFor(() => {
            expect(mockUpdateMutateAsync).toHaveBeenCalledTimes(1);
        });
        expect(mockUpdateMutateAsync).toHaveBeenCalledWith({
            id: 2,
            data: {
                date_time: '2026-02-10T11:00',
                duration_minutes: 30,
                doctor_id: null,
                notes: 'Filling updated from calendar',
            },
        });
        await waitFor(() => {
            expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        });
        expect(mockRefetch).toHaveBeenCalled();
    });

    it('opens postpone modal and postpones appointment', async () => {
        render(<Appointments />);
        const listButton = screen.getByTitle('appointments.view.list');
        fireEvent.click(listButton);

        const postponeButtons = screen.getAllByLabelText('appointments.actions.postpone');
        expect(postponeButtons.length).toBeGreaterThan(0);
        fireEvent.click(postponeButtons[0]);

        expect(screen.getByText('appointments.postpone.title')).toBeInTheDocument();

        const confirmButton = screen.getByText('appointments.postpone.confirm_btn');
        fireEvent.click(confirmButton);

        await waitFor(() => {
            expect(mockUpdateMutateAsync).toHaveBeenCalledWith({
                id: 1,
                data: {
                    status: 'Postponed',
                },
            });
        });
    });

    it('displays 409 conflict detail in toast on update conflict', async () => {
        const conflictError = {
            response: {
                status: 409,
                data: { detail: 'Appointment conflict: Another appointment is already scheduled at this time' },
            },
        };
        mockUpdateMutateAsync.mockRejectedValueOnce(conflictError);

        render(<Appointments />);
        const listButton = screen.getByTitle('appointments.view.list');
        fireEvent.click(listButton);

        const editButtons = screen.getAllByLabelText('appointments.actions.edit');
        fireEvent.click(editButtons[0]);

        const saveButton = screen.getByText('appointments.edit_form.save_btn');
        fireEvent.click(saveButton);

        await waitFor(() => {
            expect(toast.error).toHaveBeenCalledWith(
                'Appointment conflict: Another appointment is already scheduled at this time',
                expect.anything()
            );
        });
    });
});
