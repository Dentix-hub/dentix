import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, render, screen, fireEvent } from '@testing-library/react';
import { useCareSessionDraft } from '@/features/care-sessions/useCareSessionDraft';
import FinishCareSessionSheet from '@/features/care-sessions/FinishCareSessionSheet';
import * as patientsApi from '@/api/patients';

vi.mock('@/api/patients', () => ({
    getCareSessionDraft: vi.fn(),
    saveCareSessionDraft: vi.fn(),
    deleteCareSessionDraft: vi.fn(),
}));

describe('Slice S25 / G10-M17: Care Session Server Drafts Autosave Hook', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
        localStorage.clear();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('loads existing draft from server on mount', async () => {
        patientsApi.getCareSessionDraft.mockResolvedValueOnce({
            data: {
                draft_data: { notes: 'Working on canal MB', activeStepId: 2 },
                version_id: 3,
                updated_at: '2026-10-31T12:00:00Z',
            },
        });

        const { result } = renderHook(() =>
            useCareSessionDraft({ patientId: 42, careSessionId: 10 })
        );

        await act(async () => {
            // resolve initial mount effect
        });

        expect(patientsApi.getCareSessionDraft).toHaveBeenCalledWith(42);
        expect(result.current.draftData).toEqual({ notes: 'Working on canal MB', activeStepId: 2 });
        expect(result.current.status).toBe('saved');
    });

    it('debounces autosave when draft data is updated', async () => {
        patientsApi.getCareSessionDraft.mockResolvedValueOnce({ data: null });
        patientsApi.saveCareSessionDraft.mockResolvedValueOnce({
            data: { version_id: 2, draft_data: { notes: 'Canal MB prep' } },
        });

        const { result } = renderHook(() =>
            useCareSessionDraft({ patientId: 42, careSessionId: 10 })
        );

        await act(async () => {});

        act(() => {
            result.current.updateDraft({ notes: 'Canal MB prep' });
        });

        // Not saved immediately due to debounce
        expect(patientsApi.saveCareSessionDraft).not.toHaveBeenCalled();

        // Advance debounce timer (1500ms)
        await act(async () => {
            vi.advanceTimersByTime(1500);
        });

        expect(patientsApi.saveCareSessionDraft).toHaveBeenCalledTimes(1);
        expect(patientsApi.saveCareSessionDraft).toHaveBeenCalledWith(
            42,
            expect.objectContaining({
                draft_data: { notes: 'Canal MB prep' },
                care_session_id: 10,
                expected_version_id: 1,
            })
        );
        expect(result.current.status).toBe('saved');
    });

    it('handles 409 concurrency conflict from server', async () => {
        patientsApi.getCareSessionDraft.mockResolvedValueOnce({ data: null });
        patientsApi.saveCareSessionDraft.mockRejectedValueOnce({
            response: {
                status: 409,
                data: {
                    draft_data: { notes: 'Server newer notes' },
                    version_id: 5,
                },
            },
        });

        const { result } = renderHook(() =>
            useCareSessionDraft({ patientId: 42 })
        );

        await act(async () => {});

        act(() => {
            result.current.updateDraft({ notes: 'Local notes' });
        });

        await act(async () => {
            vi.advanceTimersByTime(1500);
        });

        expect(result.current.hasConflict).toBe(true);
        expect(result.current.status).toBe('conflict');
    });

    it('discards draft and removes from server and storage', async () => {
        patientsApi.getCareSessionDraft.mockResolvedValueOnce({ data: null });
        patientsApi.deleteCareSessionDraft.mockResolvedValueOnce({});

        const { result } = renderHook(() =>
            useCareSessionDraft({ patientId: 42 })
        );

        await act(async () => {});

        await act(async () => {
            await result.current.discardDraft();
        });

        expect(patientsApi.deleteCareSessionDraft).toHaveBeenCalledWith(42);
        expect(result.current.draftData).toEqual({});
        expect(result.current.status).toBe('idle');
    });

    it('resets state and prevents draft leakage across patient boundaries during navigation (Review 3 Issue 1)', async () => {
        // Patient A has existing draft
        patientsApi.getCareSessionDraft.mockImplementation((pid) => {
            if (pid === 42) {
                return Promise.resolve({
                    data: {
                        draft_data: { notes: "Patient A's private clinical note" },
                        version_id: 2,
                    },
                });
            }
            // Patient B (99) has no draft on server (404)
            const err = new Error('Not found');
            err.response = { status: 404, data: { detail: 'Draft not found' } };
            return Promise.reject(err);
        });

        // 1. Mount with Patient A
        const { result, rerender } = renderHook(
            ({ patientId, careSessionId }) => useCareSessionDraft({ patientId, careSessionId }),
            { initialProps: { patientId: 42, careSessionId: 10 } }
        );

        await act(async () => {});

        expect(result.current.draftData).toEqual({ notes: "Patient A's private clinical note" });
        expect(result.current.status).toBe('saved');
        expect(result.current.versionId).toBe(2);

        // 2. Patient A updates draft (triggers debounce timer)
        act(() => {
            result.current.updateDraft({ notes: "Patient A's unsaved quick note" });
        });
        expect(result.current.draftData).toEqual({ notes: "Patient A's unsaved quick note" });

        // 3. User navigates to Patient B before debounce completes!
        rerender({ patientId: 99, careSessionId: 20 });

        // State for Patient B must be cleanly reset immediately
        expect(result.current.draftData).toEqual({});
        expect(result.current.versionId).toBe(1);
        expect(result.current.status).toBe('idle');

        // Resolve loadExistingDraft for Patient B (returns 404)
        await act(async () => {
            vi.advanceTimersByTime(2000);
        });

        // Patient B must still have clean empty state, NOT Patient A's note
        expect(result.current.draftData).toEqual({});
        expect(result.current.versionId).toBe(1);
        expect(result.current.status).toBe('idle');

        // Verify save was NEVER called for Patient 99 with Patient 42's note
        const callsForPatientB = patientsApi.saveCareSessionDraft.mock.calls.filter(
            (call) => call[0] === 99
        );
        expect(callsForPatientB).toHaveLength(0);
    });
});

describe('FinishCareSessionSheet Draft Restoration & Autosave Integration (Review 2 Issue 1)', () => {
    const mockSession = {
        id: 10,
        status: 'in_progress',
        steps: [{ id: 1, title: 'Step 1', status: 'completed' }],
        observations: [],
    };

    it('populates form from draftData and triggers onDraftChange on typing', () => {
        const onDraftChange = vi.fn();
        const initialDraft = {
            notes: 'Recovered clinical progress notes',
            requestNextVisit: true,
            nextVisitReason: 'Tooth 46: Obturation',
            nextVisitDuration: 45,
            nextVisitNotes: 'Check root canal after 7 days',
        };

        render(
            <FinishCareSessionSheet
                isOpen={true}
                onClose={vi.fn()}
                session={mockSession}
                onFinishSession={vi.fn()}
                draftData={initialDraft}
                onDraftChange={onDraftChange}
            />
        );

        // 1. Recovered draft data populates the form inputs
        const notesInput = screen.getByTestId('finish-session-notes-input');
        expect(notesInput.value).toBe('Recovered clinical progress notes');

        const reasonInput = screen.getByTestId('next-visit-reason-input');
        expect(reasonInput.value).toBe('Tooth 46: Obturation');

        const nextVisitNotesInput = screen.getByTestId('next-visit-notes-input');
        expect(nextVisitNotesInput.value).toBe('Check root canal after 7 days');

        // 2. Typing in notes triggers onDraftChange
        fireEvent.change(notesInput, { target: { value: 'Updated clinical progress notes' } });
        expect(onDraftChange).toHaveBeenCalledWith({ notes: 'Updated clinical progress notes' });

        // 3. Typing in next visit reason triggers onDraftChange
        fireEvent.change(reasonInput, { target: { value: 'Tooth 46: Final restoration' } });
        expect(onDraftChange).toHaveBeenCalledWith({ nextVisitReason: 'Tooth 46: Final restoration' });
    });
});
