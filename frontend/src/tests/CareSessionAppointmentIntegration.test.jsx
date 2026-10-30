import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FinishCareSessionSheet from '@/features/care-sessions/FinishCareSessionSheet';
import CareSessionActiveBanner from '@/features/care-sessions/CareSessionActiveBanner';

describe('Slice S22: Care Session Appointment Integration & Next-Visit Request', () => {
    const mockSessionWithPendingSteps = {
        id: 1,
        tenant_id: 1,
        patient_id: 10,
        appointment_id: 42,
        status: 'in_progress',
        started_at: '2026-10-19T10:00:00Z',
        tooth_key: '46',
        steps: [
            { id: 1, step_code: 'access', title: 'Access Cavity Preparation', status: 'completed' },
            { id: 2, step_code: 'canal_measurement', title: 'Canal Working Length Measurement', status: 'completed' },
            { id: 3, step_code: 'clean_shape', title: 'Canal Instrumentation & Shaping', status: 'pending' },
            { id: 4, step_code: 'obturate', title: 'Canal Obturation', status: 'pending' },
        ],
        observations: [
            {
                id: 1,
                observation_code: 'working_length',
                tooth_key: '46',
                canal_id: 'MB',
                structured_value: { length_mm: 20.5, maf: 25 },
            },
        ],
    };

    const mockSessionCompletedSteps = {
        id: 2,
        tenant_id: 1,
        patient_id: 10,
        appointment_id: null,
        status: 'in_progress',
        started_at: '2026-10-19T11:00:00Z',
        tooth_key: '46',
        steps: [
            { id: 1, step_code: 'access', title: 'Access Cavity Preparation', status: 'completed' },
            { id: 2, step_code: 'obturate', title: 'Canal Obturation', status: 'completed' },
        ],
        observations: [],
    };

    it('renders FinishCareSessionSheet with Next-Visit Request section and toggle (G11-M02)', () => {
        render(
            <FinishCareSessionSheet
                isOpen={true}
                onClose={vi.fn()}
                session={mockSessionWithPendingSteps}
                onFinishSession={vi.fn()}
            />
        );

        expect(screen.getByTestId('next-visit-request-section')).toBeInTheDocument();
        expect(screen.getByTestId('request-next-visit-toggle')).toBeInTheDocument();
    });

    it('auto-suggests reason and 45-min duration for RCT session with pending steps (G11-M06, G11-M07)', () => {
        render(
            <FinishCareSessionSheet
                isOpen={true}
                onClose={vi.fn()}
                session={mockSessionWithPendingSteps}
                onFinishSession={vi.fn()}
            />
        );

        // Toggle starts false, clicking enables it
        const toggle = screen.getByTestId('request-next-visit-toggle');
        expect(toggle.checked).toBe(false);
        fireEvent.click(toggle);
        expect(toggle.checked).toBe(true);

        // Reason input should be pre-filled with tooth and next step
        const reasonInput = screen.getByTestId('next-visit-reason-input');
        expect(reasonInput.value).toContain('Tooth 46');
        expect(reasonInput.value).toContain('Canal Instrumentation & Shaping');

        // Duration should default to 45 min for RCT
        const durationSelect = screen.getByTestId('next-visit-duration-select');
        expect(Number(durationSelect.value)).toBe(45);
    });

    it('displays the G11-M08 no-auto-booking invariant notice prominently', () => {
        render(
            <FinishCareSessionSheet
                isOpen={true}
                onClose={vi.fn()}
                session={mockSessionWithPendingSteps}
                onFinishSession={vi.fn()}
            />
        );

        const toggle = screen.getByTestId('request-next-visit-toggle');
        fireEvent.click(toggle);

        const badge = screen.getByTestId('no-auto-booking-badge');
        expect(badge).toBeInTheDocument();
        expect(badge.textContent).toContain('No appointment is booked automatically');
    });

    it('allows changing duration via quick chips (G11-M07)', () => {
        render(
            <FinishCareSessionSheet
                isOpen={true}
                onClose={vi.fn()}
                session={mockSessionWithPendingSteps}
                onFinishSession={vi.fn()}
            />
        );

        const toggle = screen.getByTestId('request-next-visit-toggle');
        fireEvent.click(toggle);

        const chip60 = screen.getByTestId('duration-chip-60');
        fireEvent.click(chip60);

        const durationSelect = screen.getByTestId('next-visit-duration-select');
        expect(Number(durationSelect.value)).toBe(60);
    });

    it('submits onFinishSession with next_visit_request payload when toggle is active', async () => {
        const onFinishMock = vi.fn();
        render(
            <FinishCareSessionSheet
                isOpen={true}
                onClose={vi.fn()}
                session={mockSessionWithPendingSteps}
                onFinishSession={onFinishMock}
            />
        );

        // Enable next visit request
        const toggle = screen.getByTestId('request-next-visit-toggle');
        fireEvent.click(toggle);

        // Enter notes
        const notesInput = screen.getByTestId('finish-session-notes-input');
        fireEvent.change(notesInput, { target: { value: 'Finished instrumentation visit.' } });

        // Enter reception notes
        const receptionNotes = screen.getByTestId('next-visit-notes-input');
        fireEvent.change(receptionNotes, { target: { value: 'Schedule for next Tuesday' } });

        // Submit form
        const submitBtn = screen.getByTestId('confirm-finish-session-button');
        fireEvent.click(submitBtn);

        expect(onFinishMock).toHaveBeenCalledTimes(1);
        const submittedPayload = onFinishMock.mock.calls[0][0];

        expect(submittedPayload.notes).toBe('Finished instrumentation visit.');
        expect(submittedPayload.next_visit_request).toBeDefined();
        expect(submittedPayload.next_visit_request.care_session_id).toBe(1);
        expect(submittedPayload.next_visit_request.suggested_duration_minutes).toBe(45);
        expect(submittedPayload.next_visit_request.reason).toContain('Tooth 46');
        expect(submittedPayload.next_visit_request.notes).toBe('Schedule for next Tuesday');
    });

    it('submits onFinishSession without next_visit_request when toggle is untoggled', () => {
        const onFinishMock = vi.fn();
        render(
            <FinishCareSessionSheet
                isOpen={true}
                onClose={vi.fn()}
                session={mockSessionWithPendingSteps}
                onFinishSession={onFinishMock}
            />
        );

        // Toggle is default unchecked
        const toggle = screen.getByTestId('request-next-visit-toggle');
        expect(toggle.checked).toBe(false);

        // Submit form
        const submitBtn = screen.getByTestId('confirm-finish-session-button');
        fireEvent.click(submitBtn);

        expect(onFinishMock).toHaveBeenCalledTimes(1);
        const submittedPayload = onFinishMock.mock.calls[0][0];
        expect(submittedPayload.next_visit_request).toBeUndefined();
    });

    it('renders linked appointment badge in CareSessionActiveBanner when appointment_id is present (G11-M01)', () => {
        const { rerender } = render(
            <CareSessionActiveBanner
                session={mockSessionWithPendingSteps}
                onOpenWorkflow={vi.fn()}
                onOpenFinishSheet={vi.fn()}
            />
        );

        const badge = screen.getByTestId('linked-appointment-badge');
        expect(badge).toBeInTheDocument();
        expect(badge.textContent).toContain('Appt #42');

        // When appointment_id is null, badge is not rendered
        rerender(
            <CareSessionActiveBanner
                session={mockSessionCompletedSteps}
                onOpenWorkflow={vi.fn()}
                onOpenFinishSheet={vi.fn()}
            />
        );
        expect(screen.queryByTestId('linked-appointment-badge')).not.toBeInTheDocument();
    });
});
