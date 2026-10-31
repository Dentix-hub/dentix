import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import FollowUpDashboard from './FollowUpDashboard';
import * as appointmentsApi from '@/api/appointments';
import * as adminApi from '@/api/admin';

vi.mock('@/api/appointments', () => ({
    getFollowUpDashboard: vi.fn(),
}));

vi.mock('@/api/admin', () => ({
    getDoctors: vi.fn(),
}));

describe('FollowUpDashboard', () => {
    let queryClient;

    const mockDashboardData = {
        counts: {
            total: 3,
            overdue: 1,
            upcoming: 1,
            unscheduled: 1,
            postponed: 0,
            stopped: 0,
        },
        items: [
            {
                id: 11,
                patient_id: 101,
                patient_name: 'Amira Hassan',
                patient_phone: '+201001234567',
                procedure_name: 'SURG_EXTRACTION',
                tooth_number: 38,
                reason: 'Suture removal & socket inspection',
                suggested_duration_minutes: 20,
                status: 'requested',
                due_category: 'overdue',
                target_date: '2026-10-25T10:00:00Z',
                assigned_doctor_name: 'Dr. Sarah',
            },
            {
                id: 12,
                patient_id: 102,
                patient_name: 'Khaled Omar',
                patient_phone: '+201009876543',
                procedure_name: 'PROS_CROWN',
                tooth_number: 16,
                reason: 'Crown try-in & bite check',
                suggested_duration_minutes: 30,
                status: 'requested',
                due_category: 'upcoming',
                target_date: '2026-11-05T10:00:00Z',
                assigned_doctor_name: 'Dr. James',
            },
        ],
        total: 2,
    };

    const mockDoctors = [
        { id: 1, full_name: 'Dr. Sarah' },
        { id: 2, full_name: 'Dr. James' },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        queryClient = new QueryClient({
            defaultOptions: {
                queries: { retry: false },
            },
        });
        appointmentsApi.getFollowUpDashboard.mockResolvedValue({ data: { data: mockDashboardData } });
        adminApi.getDoctors.mockResolvedValue({ data: { doctors: mockDoctors } });
    });

    const renderComponent = (props = {}) =>
        render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter>
                    <FollowUpDashboard {...props} />
                </MemoryRouter>
            </QueryClientProvider>
        );

    it('renders dashboard KPI cards and follow-up request table', async () => {
        renderComponent();

        expect(screen.getByText(/Follow-Up & Clinical Recall Dashboard/i)).toBeInTheDocument();

        await waitFor(() => {
            expect(screen.getByText('Amira Hassan')).toBeInTheDocument();
            expect(screen.getByText('Khaled Omar')).toBeInTheDocument();
            expect(screen.getByText('Suture removal & socket inspection')).toBeInTheDocument();
            expect(screen.getByText('Crown try-in & bite check')).toBeInTheDocument();
            expect(screen.getAllByText('Overdue').length).toBeGreaterThan(0);
            expect(screen.getAllByText('Upcoming').length).toBeGreaterThan(0);
        });
    });

    it('triggers onSchedule callback when Schedule button is clicked', async () => {
        const mockOnSchedule = vi.fn();
        renderComponent({ onSchedule: mockOnSchedule });

        await waitFor(() => {
            expect(screen.getByTestId('schedule-btn-11')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByTestId('schedule-btn-11'));
        expect(mockOnSchedule).toHaveBeenCalledWith(
            expect.objectContaining({
                id: 11,
                patient_id: 101,
                reason: 'Suture removal & socket inspection',
            })
        );
    });

    it('filters requests by category when KPI pill is clicked', async () => {
        renderComponent();

        await waitFor(() => {
            expect(screen.getByTestId('filter-cat-overdue')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByTestId('filter-cat-overdue'));

        await waitFor(() => {
            expect(appointmentsApi.getFollowUpDashboard).toHaveBeenCalledWith(
                expect.objectContaining({ due_category: 'overdue' })
            );
        });
    });

    it('filters requests by procedure and date range', async () => {
        renderComponent();

        await waitFor(() => {
            expect(screen.getByTestId('select-filter-procedure')).toBeInTheDocument();
        });

        fireEvent.change(screen.getByTestId('select-filter-procedure'), { target: { value: 'ENDO_RCT' } });
        fireEvent.change(screen.getByTestId('input-filter-date-from'), { target: { value: '2026-11-01' } });
        fireEvent.change(screen.getByTestId('input-filter-date-to'), { target: { value: '2026-11-30' } });

        await waitFor(() => {
            expect(appointmentsApi.getFollowUpDashboard).toHaveBeenCalledWith(
                expect.objectContaining({
                    procedure_code: 'ENDO_RCT',
                    date_from: expect.stringContaining('2026-11-01'),
                    date_to: expect.stringContaining('2026-11-30'),
                })
            );
        });
    });

    it('supports pagination controls and total_count handling', async () => {
        appointmentsApi.getFollowUpDashboard.mockResolvedValueOnce({
            data: {
                data: {
                    ...mockDashboardData,
                    total_count: 50,
                },
            },
        });

        renderComponent();

        await waitFor(() => {
            expect(screen.getByTestId('btn-next-page')).toBeInTheDocument();
            expect(screen.getByTestId('page-indicator')).toHaveTextContent('1 / 3');
        });

        fireEvent.click(screen.getByTestId('btn-next-page'));

        await waitFor(() => {
            expect(appointmentsApi.getFollowUpDashboard).toHaveBeenCalledWith(
                expect.objectContaining({ skip: 20, limit: 20 })
            );
        });
    });
});
