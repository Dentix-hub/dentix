/**
 * Reception Next-Visit Queue & Booking Conversion Tests (Slice S25 / G11-M04, G11-M05, G11-M09..M12).
 * Verifies reception queue triage, prefilled booking conversion, and safety lifecycle UI interactions.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NextVisitQueue from '@/features/appointments/components/NextVisitQueue';
import Appointments from '@/pages/Appointments';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => fallback || key,
        i18n: { language: 'en', changeLanguage: vi.fn() },
    }),
}));

vi.mock('react-router-dom', () => ({
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({
        user: { id: 10, role: 'receptionist', tenant_id: 1 },
    }),
}));

vi.mock('@/shared/ui/WeeklyCalendar', () => ({
    default: () => <div data-testid="weekly-calendar">Weekly Calendar</div>,
}));

const mockRequests = [
    {
        id: 101,
        patient_id: 5,
        patient_name: 'Tariq Ali',
        patient_phone: '+966500000001',
        reason: 'Tooth 46: Root Canal Treatment - Obturation & Seal',
        suggested_duration_minutes: 45,
        preferred_time_window_start: '2026-10-25T10:00:00Z',
        status: 'requested',
        notes: 'Bring radiograph',
    },
    {
        id: 102,
        patient_id: 8,
        patient_name: 'Sara Ahmed',
        patient_phone: '+966500000002',
        reason: 'Crown Placement Tooth 21',
        suggested_duration_minutes: 30,
        status: 'requested',
        notes: null,
    },
    {
        id: 103,
        patient_id: 9,
        patient_name: 'Khaled Omar',
        patient_phone: '+966500000003',
        reason: 'Routine Cleaning',
        suggested_duration_minutes: 30,
        status: 'scheduled',
        fulfilled_appointment_id: 55,
        notes: '[APPOINTMENT:55]',
    },
];

let mockScheduleMutate;
let mockCancelMutate;

vi.mock('@/hooks/useAppointments', () => ({
    useAppointments: () => ({
        data: [
            { id: 1, patient_name: 'Existing Patient', status: 'Scheduled', date_time: '2026-10-21T09:00:00' }
        ],
        isLoading: false,
        refetch: vi.fn(),
    }),
    useUpdateAppointmentStatus: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateAppointment: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useNextVisitRequests: () => ({
        data: mockRequests,
        isLoading: false,
        refetch: vi.fn(),
    }),
    useScheduleNextVisitRequest: () => ({
        mutateAsync: (...args) => mockScheduleMutate(...args),
        isPending: false,
    }),
    useCancelNextVisitRequest: () => ({
        mutateAsync: (...args) => mockCancelMutate(...args),
        isPending: false,
    }),
}));

vi.mock('@/hooks/usePatients', () => ({
    usePatients: () => ({
        data: [
            { id: 5, name: 'Tariq Ali', phone: '+966500000001' },
            { id: 8, name: 'Sara Ahmed', phone: '+966500000002' },
        ],
        isLoading: false,
        refetch: vi.fn(),
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

describe('NextVisitQueue Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders queue header with pending count badge (G11-M04)', () => {
        render(<NextVisitQueue requests={mockRequests} />);

        expect(screen.getByTestId('reception-next-visit-queue')).toBeInTheDocument();
        expect(screen.getByText('Next-Visit Requests')).toBeInTheDocument();
        expect(screen.getByTestId('nvr-pending-badge')).toHaveTextContent('2 pending');
    });

    it('displays patient details, clinical reasons, and duration pills', () => {
        render(<NextVisitQueue requests={mockRequests} />);

        expect(screen.getByText('Tariq Ali')).toBeInTheDocument();
        expect(screen.getByText('+966500000001')).toBeInTheDocument();
        expect(screen.getByText('Tooth 46: Root Canal Treatment - Obturation & Seal')).toBeInTheDocument();
        expect(screen.getByText('45 min')).toBeInTheDocument();

        expect(screen.getByText('Sara Ahmed')).toBeInTheDocument();
        expect(screen.getByText('Crown Placement Tooth 21')).toBeInTheDocument();
    });

    it('filters between Pending and All requests', () => {
        render(<NextVisitQueue requests={mockRequests} />);

        // In 'requested' filter (default), only 2 pending cards appear
        expect(screen.getByTestId('next-visit-request-card-101')).toBeInTheDocument();
        expect(screen.getByTestId('next-visit-request-card-102')).toBeInTheDocument();
        expect(screen.queryByTestId('next-visit-request-card-103')).not.toBeInTheDocument();

        // Switch filter to 'All'
        fireEvent.click(screen.getByTestId('nvr-filter-all'));
        expect(screen.getByTestId('next-visit-request-card-103')).toBeInTheDocument();
        expect(screen.getByText('Appt #55')).toBeInTheDocument();
    });

    it('triggers onSchedule callback when Book Appointment is clicked (G11-M05)', () => {
        const onSchedule = vi.fn();
        render(<NextVisitQueue requests={mockRequests} onSchedule={onSchedule} />);

        const bookBtn = screen.getByTestId('schedule-request-btn-101');
        fireEvent.click(bookBtn);

        expect(onSchedule).toHaveBeenCalledTimes(1);
        expect(onSchedule).toHaveBeenCalledWith(mockRequests[0]);
    });

    it('triggers onDismiss callback when Dismiss is clicked', () => {
        const onDismiss = vi.fn();
        render(<NextVisitQueue requests={mockRequests} onDismiss={onDismiss} />);

        const dismissBtn = screen.getByTestId('dismiss-request-btn-101');
        fireEvent.click(dismissBtn);

        expect(onDismiss).toHaveBeenCalledTimes(1);
        expect(onDismiss).toHaveBeenCalledWith(mockRequests[0]);
    });

    it('renders empty state when there are no requests', () => {
        render(<NextVisitQueue requests={[]} />);

        expect(screen.getByText('No pending follow-up requests')).toBeInTheDocument();
    });
});

describe('Appointments Page Next-Visit Queue Integration (G11-M05, G11-M08)', () => {
    beforeEach(() => {
        mockScheduleMutate = vi.fn().mockResolvedValue({ data: { id: 101, status: 'scheduled' } });
        mockCancelMutate = vi.fn().mockResolvedValue({ data: { id: 101, status: 'cancelled' } });
        vi.clearAllMocks();
    });

    it('pre-fills booking modal when Book Appointment is clicked on a request card', async () => {
        render(<Appointments />);

        // 1. Verify queue is mounted on Appointments page
        expect(screen.getByTestId('reception-next-visit-queue')).toBeInTheDocument();

        // 2. Click Book Appointment on Tariq's request (45 min, Tooth 46 RCT)
        const bookBtn = screen.getByTestId('schedule-request-btn-101');
        fireEvent.click(bookBtn);

        // 3. Modal opens with pre-filled clinical reason and schedule title
        await waitFor(() => {
            expect(screen.getByRole('dialog')).toBeInTheDocument();
        });
        expect(screen.getByText('Schedule Next-Visit Follow-up')).toBeInTheDocument();

        // Verify notes textarea pre-filled with clinical reason
        const notesInput = screen.getByPlaceholderText('appointments.form.notes_placeholder');
        expect(notesInput.value).toBe('Tooth 46: Root Canal Treatment - Obturation & Seal');
    });

    it('enforces G11-M08: never auto-books an appointment without user action', async () => {
        render(<Appointments />);

        // Seeing the request in the queue does NOT call schedule mutation
        expect(mockScheduleMutate).not.toHaveBeenCalled();

        // Clicking "Book Appointment" to open the modal does NOT book yet
        fireEvent.click(screen.getByTestId('schedule-request-btn-101'));
        expect(mockScheduleMutate).not.toHaveBeenCalled();

        // Only submitting the form triggers the booking mutation
        const confirmBtn = screen.getByText('appointments.form.confirm_btn');
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(mockScheduleMutate).toHaveBeenCalledTimes(1);
        });
        expect(mockScheduleMutate).toHaveBeenCalledWith(
            expect.objectContaining({
                requestId: 101,
                data: expect.objectContaining({
                    duration_minutes: 45,
                    notes: 'Tooth 46: Root Canal Treatment - Obturation & Seal',
                }),
            })
        );
    });

    it('calls cancelRequestMutation when receptionist dismisses a request', async () => {
        render(<Appointments />);

        const dismissBtn = screen.getByTestId('dismiss-request-btn-101');
        fireEvent.click(dismissBtn);

        await waitFor(() => {
            expect(mockCancelMutate).toHaveBeenCalledTimes(1);
        });
        expect(mockCancelMutate).toHaveBeenCalledWith(
            expect.objectContaining({
                requestId: 101,
            })
        );
    });
});
