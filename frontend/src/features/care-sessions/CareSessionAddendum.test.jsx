import { it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TreatmentHistory from '@/features/patients/PatientTabs/TreatmentHistory';
import { useAuthStore } from '@/store/auth.store';
import { addCareSessionAddendum } from '@/api/patients';
import FinishCareSessionSheet from './FinishCareSessionSheet';

vi.mock('@/api/patients', async (original) => ({ ...await original(), addCareSessionAddendum: vi.fn().mockResolvedValue({ data: { id: 2 } }) }));
vi.mock('@/api/admin', () => ({ getDoctors: vi.fn().mockResolvedValue({ data: { doctors: [{ id: 10, full_name: 'Synthetic doctor' }] } }) }));

it('shows original visit documentation and its corrections together without counting a new visit', async () => {
    useAuthStore.setState({ user: { id: 10, role: 'doctor' } });
    const session = { id: 77, status: 'completed', notes: 'Original narrative', created_at: '2026-10-01T10:00:00Z', recorded_by_user_id: 10, observations: [{ id: 5, structured_value: { value: 'A2' }, observation_code: 'shade' }], procedures: [{ id: 2, work_item_id: 101, procedure_notes: 'Restoration', template_snapshot: { custom_fields: [{ field_id: 'shade', label: 'Shade' }], custom_field_values: { shade: 'A2' } } }] };
    const addendum = { id: 78, amends_session_id: 77, status: 'completed', notes: 'Prior correction', amendment_reason: 'Radiograph review', created_at: '2026-10-02T10:00:00Z', recorded_by_user_id: 10 };
    render(<QueryClientProvider client={new QueryClient()}><TreatmentHistory patientId={123} careSessions={[session, addendum]} history={[]} /></QueryClientProvider>);
    fireEvent.click(screen.getByTestId('view-sessions-tab'));
    expect(screen.getByTestId('view-sessions-tab')).toHaveTextContent('(1)');
    expect(screen.getByText('Original narrative')).toBeInTheDocument();
    expect(screen.getByTestId('visit-addendum-78')).toHaveTextContent('Prior correction');
    expect(screen.getByTestId('visit-addendum-78')).toHaveTextContent('Radiograph review');
    expect(screen.getByText('Shade:')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('add-visit-correction-77'));
    fireEvent.change(screen.getByLabelText('Correction / addendum'), { target: { value: 'Corrected narrative' } });
    fireEvent.change(screen.getByLabelText('Reason for correction'), { target: { value: 'Transcription error' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save correction' }));
    await waitFor(() => expect(addCareSessionAddendum).toHaveBeenCalledWith(123, 77, { notes: 'Corrected narrative', reason: 'Transcription error' }));
    expect(session.notes).toBe('Original narrative');
});

it('links a non-RCT follow-up and optional date to the actual procedures', async () => {
    const finish = vi.fn().mockResolvedValue(false);
    render(<FinishCareSessionSheet isOpen onClose={vi.fn()} session={{ id: 77, patient_id: 123, steps: [{ id: 1, title: 'Suture removal', work_item_id: 102, status: 'pending' }], procedures: [{ id: 3, work_item_id: 102, template_snapshot: { title: 'Extraction' } }, { id: 4, work_item_id: 101 }] }} onFinishSession={finish} />);
    fireEvent.click(screen.getByTestId('request-next-visit-toggle'));
    expect(screen.getByTestId('next-visit-reason-input').value).toContain('Extraction');
    expect(screen.getByTestId('next-visit-reason-input').value).not.toContain('Root Canal');
    fireEvent.change(screen.getByTestId('next-visit-date-input'), { target: { value: '2026-12-01T10:00' } });
    fireEvent.click(screen.getByTestId('confirm-finish-session-button'));
    await waitFor(() => expect(finish).toHaveBeenCalledWith(expect.objectContaining({ next_visit_request: expect.objectContaining({ work_item_id: 102, associated_work_item_ids: [102, 101], preferred_time_window_start: new Date('2026-12-01T10:00').toISOString() }) })));
});
