import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useCareSessionDraft } from '@/features/care-sessions/useCareSessionDraft';
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
});
