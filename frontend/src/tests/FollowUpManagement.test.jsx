import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import FollowUpManagementModal from '@/features/care-sessions/FollowUpManagementModal';
import * as patientsApi from '@/api/patients';

vi.mock('@/api/patients', () => ({
    stopNextVisitRequest: vi.fn(),
    postponeNextVisitRequest: vi.fn(),
    resumeNextVisitRequest: vi.fn(),
    handoffNextVisitRequest: vi.fn(),
}));

describe('Slice S25 / G11-M10..M13: FollowUpManagementModal', () => {
    let queryClient;

    beforeEach(() => {
        queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false } },
        });
        vi.clearAllMocks();
    });

    const renderWithClient = (ui) => {
        return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
    };

    const mockRequest = {
        id: 77,
        patient_id: 10,
        patient_name: 'John Doe',
        reason: 'Tooth 16: Obturation',
        status: 'requested',
    };

    const mockDoctors = [
        { id: 2, name: 'Dr. Sarah Smith' },
        { id: 3, name: 'Dr. Ahmed Ali' },
    ];

    it('submits postpone request with date and reason', async () => {
        patientsApi.postponeNextVisitRequest.mockResolvedValueOnce({ data: { status: 'postponed' } });
        const successSpy = vi.fn();
        const closeSpy = vi.fn();

        renderWithClient(
            <FollowUpManagementModal
                isOpen={true}
                onClose={closeSpy}
                request={mockRequest}
                doctors={mockDoctors}
                onSuccess={successSpy}
            />
        );

        expect(screen.getByTestId('follow-up-management-modal')).toBeInTheDocument();
        expect(screen.getByText(/Request #77/)).toBeInTheDocument();

        // Fill postpone date & reason
        const dateInput = screen.getByTestId('postpone-date-input');
        const reasonInput = screen.getByTestId('postpone-reason-input');

        fireEvent.change(dateInput, { target: { value: '2026-11-10T10:00' } });
        fireEvent.change(reasonInput, { target: { value: 'Patient traveling for work' } });

        fireEvent.click(screen.getByTestId('confirm-followup-action-btn'));

        await waitFor(() => {
            expect(patientsApi.postponeNextVisitRequest).toHaveBeenCalledWith(
                10,
                77,
                expect.objectContaining({
                    reason: 'Patient traveling for work',
                })
            );
            expect(successSpy).toHaveBeenCalled();
            expect(closeSpy).toHaveBeenCalled();
        });
    });

    it('submits stop reminders request with required reason', async () => {
        patientsApi.stopNextVisitRequest.mockResolvedValueOnce({ data: { status: 'stopped' } });
        const successSpy = vi.fn();
        const closeSpy = vi.fn();

        renderWithClient(
            <FollowUpManagementModal
                isOpen={true}
                onClose={closeSpy}
                request={mockRequest}
                doctors={mockDoctors}
                onSuccess={successSpy}
            />
        );

        // Switch to Stop tab
        fireEvent.click(screen.getByTestId('tab-stop'));

        const reasonInput = screen.getByTestId('stop-reason-input');
        fireEvent.change(reasonInput, { target: { value: 'Patient completed treatment at another clinic' } });

        fireEvent.click(screen.getByTestId('confirm-followup-action-btn'));

        await waitFor(() => {
            expect(patientsApi.stopNextVisitRequest).toHaveBeenCalledWith(
                10,
                77,
                { reason: 'Patient completed treatment at another clinic' }
            );
            expect(successSpy).toHaveBeenCalled();
            expect(closeSpy).toHaveBeenCalled();
        });
    });

    it('submits handoff request with selected doctor and clinical notes', async () => {
        patientsApi.handoffNextVisitRequest.mockResolvedValueOnce({ data: { status: 'requested' } });
        const successSpy = vi.fn();
        const closeSpy = vi.fn();

        renderWithClient(
            <FollowUpManagementModal
                isOpen={true}
                onClose={closeSpy}
                request={mockRequest}
                doctors={mockDoctors}
                onSuccess={successSpy}
            />
        );

        // Switch to Handoff tab
        fireEvent.click(screen.getByTestId('tab-handoff'));

        // Select doctor
        const selectDoc = screen.getByTestId('handoff-doctor-select');
        fireEvent.change(selectDoc, { target: { value: '3' } });

        // Fill reason & notes
        const reasonInput = screen.getByTestId('handoff-reason-input');
        const notesInput = screen.getByTestId('handoff-notes-input');

        fireEvent.change(reasonInput, { target: { value: 'Referral for surgical root resection' } });
        fireEvent.change(notesInput, { target: { value: 'Patient has high blood pressure' } });

        fireEvent.click(screen.getByTestId('confirm-followup-action-btn'));

        await waitFor(() => {
            expect(patientsApi.handoffNextVisitRequest).toHaveBeenCalledWith(
                10,
                77,
                {
                    handoff_to_user_id: 3,
                    reason: 'Referral for surgical root resection',
                    notes: 'Patient has high blood pressure',
                }
            );
            expect(successSpy).toHaveBeenCalled();
            expect(closeSpy).toHaveBeenCalled();
        });
    });
});
