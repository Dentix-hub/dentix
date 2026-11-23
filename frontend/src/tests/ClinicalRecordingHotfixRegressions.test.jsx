import { useState } from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act, renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import GenericVisitWorkspace from '@/features/care-sessions/GenericVisitWorkspace';
import FinishCareSessionSheet from '@/features/care-sessions/FinishCareSessionSheet';
import LabHandoffSheet from '@/features/care-sessions/LabHandoffSheet';
import { useCareSessionDraft } from '@/features/care-sessions/useCareSessionDraft';
import QuickTreatmentSheet from '@/features/clinical-chart/components/QuickTreatmentSheet';
import TreatmentHistory from '@/features/patients/PatientTabs/TreatmentHistory';
import { useTreatmentOperations } from '@/features/patients/hooks/useTreatmentOperations';
import { useAuthStore } from '@/store/auth.store';
import * as patientsApi from '@/api/patients';
import * as labsApi from '@/api/labs';
import * as api from '@/api';

vi.mock('@/api/patients', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        addCareSessionProcedure: vi.fn(),
        removeCareSessionProcedure: vi.fn(),
        addCareSessionStep: vi.fn(),
        getPatientCareSessions: vi.fn().mockResolvedValue({ data: { data: [] } }),
        getPatientClinicalWorkItems: vi.fn().mockResolvedValue({ data: [] }),
        getCareSessionDraft: vi.fn().mockResolvedValue({ data: null }),
        saveCareSessionDraft: vi.fn(),
        deleteCareSessionDraft: vi.fn().mockResolvedValue({}),
        updateClinicalWorkItemStatus: vi.fn(),
    };
});

vi.mock('@/api/labs', () => ({
    getLaboratories: vi.fn(),
    dispatchLabHandoff: vi.fn(),
}));

vi.mock('@/api/inventory', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        getStockSummary: vi.fn().mockResolvedValue({ data: [] }),
        getMaterials: vi.fn().mockResolvedValue({ data: [] }),
        getActiveSessions: vi.fn().mockResolvedValue({ data: [] }),
    };
});

vi.mock('@/api', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        getLaboratories: vi.fn().mockResolvedValue({ data: [] }),
        getPatientLabOrders: vi.fn().mockResolvedValue({ data: [] }),
        createTreatment: vi.fn().mockResolvedValue({ data: { id: 99 } }),
        updateTreatment: vi.fn().mockResolvedValue({ data: { id: 99 } }),
        updateToothStatus: vi.fn().mockResolvedValue({ data: { id: 1, tooth_number: 16, condition: 'Missing' } }),
        createLabOrder: vi.fn().mockResolvedValue({ data: { id: 50 } }),
        getProcedurePrices: vi.fn().mockResolvedValue({ data: { price_lists: [] } }),
    };
});

vi.mock('@/api/admin', () => ({
    getDoctors: vi.fn().mockResolvedValue({ data: { doctors: [] } }),
}));

const t = (_key, fallback) => (typeof fallback === 'string' ? fallback : _key);

function withQueryClient(node) {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
        <QueryClientProvider client={qc}>
            <MemoryRouter>{node}</MemoryRouter>
        </QueryClientProvider>
    );
}

describe('Finding 1: Structured 422 error safety in active-session Add Procedure', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        patientsApi.getPatientCareSessions.mockResolvedValue({ data: { data: [] } });
    });

    it('renders a readable inline error banner instead of crashing on structured 422 detail array', async () => {
        patientsApi.addCareSessionProcedure.mockRejectedValueOnce({
            response: {
                status: 422,
                data: {
                    detail: [
                        {
                            type: 'int_parsing',
                            loc: ['path', 'work_item_id'],
                            msg: 'Input should be a valid integer',
                            input: 'bad',
                        },
                    ],
                },
            },
        });

        const workItems = [
            { id: 10, kind: 'procedure', code: 'ENDO_RCT', title: 'Root Canal', status: 'active', targets: [{ tooth_key: '46' }] },
            { id: 20, kind: 'procedure', code: 'PROS_CROWN', title: 'Crown', status: 'active', targets: [{ tooth_key: '21' }] },
        ];

        withQueryClient(
            <GenericVisitWorkspace
                isOpen
                session={{
                    id: 1,
                    patient_id: 42,
                    status: 'in_progress',
                    procedures: [{ id: 11, work_item_id: 10, template_snapshot: { custom_fields: [] } }],
                    steps: [],
                    observations: [],
                }}
                patient={{ id: 42, name: 'Synthetic Patient' }}
                patientWorkItems={workItems}
                onClose={vi.fn()}
                onOpenFinishSheet={vi.fn()}
                t={t}
            />
        );

        fireEvent.click(screen.getByTestId('btn-add-proc-to-visit'));
        fireEvent.click(screen.getByText('Crown'));

        const banner = await screen.findByTestId('workspace-error-banner');
        expect(banner).toHaveTextContent(/Input should be a valid integer/i);
        // Workspace remains open and usable
        expect(screen.getByTestId('generic-visit-workspace')).toBeInTheDocument();
    });

    it('adds a valid second procedure to an active visit and selects it', async () => {
        patientsApi.addCareSessionProcedure.mockResolvedValueOnce({
            data: { id: 12, work_item_id: 20 },
        });
        const refetchSession = vi.fn().mockResolvedValue({});
        const workItems = [
            { id: 10, kind: 'procedure', code: 'ENDO_RCT', title: 'Root Canal', status: 'active', targets: [{ tooth_key: '46' }] },
            { id: 20, kind: 'procedure', code: 'PROS_CROWN', title: 'Crown', status: 'active', targets: [{ tooth_key: '21' }] },
        ];

        withQueryClient(
            <GenericVisitWorkspace
                isOpen
                session={{
                    id: 1,
                    patient_id: 42,
                    status: 'in_progress',
                    procedures: [{ id: 11, work_item_id: 10, template_snapshot: { custom_fields: [] } }],
                    steps: [],
                    observations: [],
                }}
                patient={{ id: 42, name: 'Synthetic Patient' }}
                patientWorkItems={workItems}
                refetchSession={refetchSession}
                onClose={vi.fn()}
                onOpenFinishSheet={vi.fn()}
                t={t}
            />
        );

        fireEvent.click(screen.getByTestId('btn-add-proc-to-visit'));
        fireEvent.click(screen.getByText('Crown'));

        await waitFor(() => {
            expect(patientsApi.addCareSessionProcedure).toHaveBeenCalledWith(42, 1, 20);
        });
        expect(refetchSession).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('workspace-error-banner')).not.toBeInTheDocument();
    });

    it('formats structured 422 arrays and nested object details safely for both entry points', async () => {
        const { formatApiError } = await import('@/utils/formatApiError');
        const validationErr = {
            response: {
                status: 422,
                data: {
                    detail: [
                        { type: 'int_parsing', loc: ['path', 'work_item_id'], msg: 'Input should be a valid integer' },
                        { type: 'missing', loc: ['body', 'reason'], msg: 'Field required' },
                    ],
                },
            },
        };
        const formatted = formatApiError(validationErr, 'Fallback');
        expect(typeof formatted).toBe('string');
        expect(formatted).toContain('Input should be a valid integer');
        expect(formatted).toContain('Field required');

        expect(formatApiError({ response: { data: { detail: { message: 'Already linked' } } } }, 'Fallback')).toBe('Already linked');
        expect(formatApiError({ response: { data: { detail: [{}] } } }, 'Safe fallback')).toBe('Safe fallback');
    });
});

describe('Finding 2: Care session draft durability, beforeunload confirmation, and zero client storage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
        localStorage.clear();
        sessionStorage.clear();
        patientsApi.getCareSessionDraft.mockResolvedValue({ data: null });
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('arms beforeunload confirmation before autosave dispatches, disarms after server ack, and writes zero PHI to browser storage', async () => {
        patientsApi.saveCareSessionDraft.mockResolvedValueOnce({
            data: { version_id: 2, draft_data: { proc_notes_10: 'Prepared MB canal' } },
        });

        const { result } = renderHook(() =>
            useCareSessionDraft({ patientId: 42, careSessionId: 10 })
        );
        await act(async () => {});

        act(() => {
            result.current.updateDraft({ proc_notes_10: 'Prepared MB canal' });
        });

        // No patient/clinical text in localStorage or sessionStorage
        expect(localStorage.length).toBe(0);
        expect(sessionStorage.length).toBe(0);

        // Before autosave completes, beforeunload must prompt to prevent silent loss
        const unloadBeforeSave = new Event('beforeunload', { cancelable: true });
        window.dispatchEvent(unloadBeforeSave);
        expect(unloadBeforeSave.defaultPrevented).toBe(true);

        // Let autosave complete
        await act(async () => {
            vi.advanceTimersByTime(1500);
        });

        expect(patientsApi.saveCareSessionDraft).toHaveBeenCalledTimes(1);
        expect(result.current.status).toBe('saved');

        // After server ack, beforeunload no longer blocks navigation
        const unloadAfterSave = new Event('beforeunload', { cancelable: true });
        window.dispatchEvent(unloadAfterSave);
        expect(unloadAfterSave.defaultPrevented).toBe(false);
    });

    it('serializes edits during an in-flight save without losing newer keystrokes or triggering stale version conflicts', async () => {
        let resolveFirst;
        patientsApi.saveCareSessionDraft
            .mockImplementationOnce(
                () => new Promise((resolve) => {
                    resolveFirst = resolve;
                })
            )
            .mockResolvedValueOnce({
                data: { version_id: 3, draft_data: { proc_notes_10: 'Final text' } },
            });

        const { result } = renderHook(() =>
            useCareSessionDraft({ patientId: 42, careSessionId: 10 })
        );
        await act(async () => {});

        act(() => {
            result.current.updateDraft({ proc_notes_10: 'Initial text' });
        });

        // Trigger first save (in-flight)
        await act(async () => {
            vi.advanceTimersByTime(1500);
        });
        expect(patientsApi.saveCareSessionDraft).toHaveBeenCalledTimes(1);

        // Clinician keeps typing while first save is still in-flight
        act(() => {
            result.current.updateDraft({ proc_notes_10: 'Final text' });
        });

        // Resolve first save -> should automatically queue/send follow-up save with version 2
        await act(async () => {
            resolveFirst({ data: { version_id: 2, draft_data: { proc_notes_10: 'Initial text' } } });
        });

        await act(async () => {
            vi.advanceTimersByTime(1500);
        });

        expect(patientsApi.saveCareSessionDraft).toHaveBeenCalledTimes(2);
        expect(patientsApi.saveCareSessionDraft).toHaveBeenNthCalledWith(
            2,
            42,
            expect.objectContaining({
                draft_data: { proc_notes_10: 'Final text' },
                expected_version_id: 2,
            })
        );
        expect(result.current.status).toBe('saved');
    });

    it('keeps beforeunload armed on server failure and disarms after discardDraft on session finish', async () => {
        patientsApi.saveCareSessionDraft.mockRejectedValueOnce(new Error('Server 500'));

        const { result } = renderHook(() =>
            useCareSessionDraft({ patientId: 42, careSessionId: 10 })
        );
        await act(async () => {});

        act(() => {
            result.current.updateDraft({ proc_next_action_10: 'Obturation' });
        });

        await act(async () => {
            vi.advanceTimersByTime(1500);
        });

        expect(result.current.status).toBe('error');
        expect(result.current.draftData.proc_next_action_10).toBe('Obturation');

        const unloadOnError = new Event('beforeunload', { cancelable: true });
        window.dispatchEvent(unloadOnError);
        expect(unloadOnError.defaultPrevented).toBe(true);

        // Discarding on finish clears dirty state and disarms beforeunload
        await act(async () => {
            await result.current.discardDraft();
        });

        const unloadAfterDiscard = new Event('beforeunload', { cancelable: true });
        window.dispatchEvent(unloadAfterDiscard);
        expect(unloadAfterDiscard.defaultPrevented).toBe(false);
    });

    it('flushes both fields through the same server API when the document is hidden', async () => {
        const draft = { proc_notes_10: 'Immediate reload note', proc_next_action_10: 'Obturation next visit' };
        patientsApi.saveCareSessionDraft.mockResolvedValueOnce({
            data: { care_session_id: 10, version_id: 2, draft_data: draft },
        });
        const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');
        try {
            const { result, unmount } = renderHook(() =>
                useCareSessionDraft({ patientId: 42, careSessionId: 10 })
            );
            await act(async () => {});
            act(() => result.current.updateDraft(draft));
            await act(async () => {
                document.dispatchEvent(new Event('visibilitychange'));
            });
            expect(patientsApi.saveCareSessionDraft).toHaveBeenCalledExactlyOnceWith(42, {
                care_session_id: 10, draft_data: draft, expected_version_id: 1,
            });
            expect(result.current.status).toBe('saved');
            expect(localStorage.length).toBe(0);
            expect(sessionStorage.length).toBe(0);
            unmount();

            patientsApi.getCareSessionDraft.mockResolvedValueOnce({
                data: { care_session_id: 10, version_id: 2, draft_data: draft },
            });
            const reopened = renderHook(() =>
                useCareSessionDraft({ patientId: 42, careSessionId: 10 })
            );
            await act(async () => {});
            expect(reopened.result.current.draftData).toEqual(draft);
        } finally {
            visibility.mockRestore();
        }
    });

    it('rejects a finish flush when the in-flight autosave conflicts', async () => {
        const conflict = { response: { status: 409, data: { detail: { current_version_id: 2 } } } };
        let rejectSave;
        patientsApi.saveCareSessionDraft.mockImplementationOnce(
            () => new Promise((_resolve, reject) => { rejectSave = reject; })
        );
        const { result } = renderHook(() =>
            useCareSessionDraft({ patientId: 42, careSessionId: 10 })
        );
        await act(async () => {});
        act(() => result.current.updateDraft({ proc_notes_10: 'Keep local entry' }));
        await act(async () => { vi.advanceTimersByTime(1500); });

        await act(async () => {
            const flush = expect(result.current.saveNow()).rejects.toBe(conflict);
            rejectSave(conflict);
            await flush;
        });

        expect(patientsApi.saveCareSessionDraft).toHaveBeenCalledTimes(1);
        expect(result.current.status).toBe('conflict');
        expect(result.current.draftData.proc_notes_10).toBe('Keep local entry');
    });

    it('keeps the server version without importing a previous visit’s draft text', async () => {
        patientsApi.getCareSessionDraft.mockResolvedValueOnce({
            data: { care_session_id: 9, version_id: 3, draft_data: { proc_notes_10: 'Prior visit note' } },
        });
        patientsApi.saveCareSessionDraft.mockResolvedValueOnce({ data: { version_id: 4 } });
        const { result } = renderHook(() =>
            useCareSessionDraft({ patientId: 42, careSessionId: 10 })
        );
        await act(async () => {});
        expect(result.current.draftData).toEqual({});
        act(() => result.current.updateDraft({ proc_next_action_10: 'Current action' }));
        await act(async () => { vi.advanceTimersByTime(1500); });

        expect(patientsApi.saveCareSessionDraft).toHaveBeenCalledExactlyOnceWith(42, {
            care_session_id: 10,
            expected_version_id: 3,
            draft_data: { proc_next_action_10: 'Current action' },
        });
    });

    it('flushes pending notes and next action immediately on input blur in GenericVisitWorkspace', () => {
        const onDraftChange = vi.fn();
        const onFlushDraft = vi.fn().mockResolvedValue({});

        withQueryClient(
            <GenericVisitWorkspace
                isOpen
                session={{
                    id: 1,
                    patient_id: 42,
                    status: 'in_progress',
                    procedures: [{ id: 11, work_item_id: 10, template_snapshot: { custom_fields: [] } }],
                    steps: [],
                    observations: [],
                }}
                patient={{ id: 42, name: 'Synthetic Patient' }}
                patientWorkItems={[{ id: 10, kind: 'procedure', code: 'ENDO_RCT', title: 'RCT', status: 'active' }]}
                draftData={{}}
                onDraftChange={onDraftChange}
                onFlushDraft={onFlushDraft}
                hasUnsavedDraftChanges={true}
                careSessionDraftStatus="unsaved"
                onClose={vi.fn()}
                onOpenFinishSheet={vi.fn()}
                t={t}
            />
        );

        const notesInput = screen.getByTestId('workspace-proc-notes-input');
        fireEvent.change(notesInput, { target: { value: 'Canal irrigated' } });
        expect(onDraftChange).toHaveBeenCalledWith({ proc_notes_10: 'Canal irrigated' });
        fireEvent.blur(notesInput);
        expect(onFlushDraft).toHaveBeenCalledTimes(1);

        const nextInput = screen.getByTestId('workspace-proc-next-action-input');
        fireEvent.change(nextInput, { target: { value: 'Final obturation' } });
        expect(onDraftChange).toHaveBeenCalledWith({ proc_next_action_10: 'Final obturation' });
        fireEvent.blur(nextInput);
        expect(onFlushDraft).toHaveBeenCalledTimes(2);
    });
});

describe('Finding 3a: FinishCareSessionSheet authoritative lab target resolution & ambiguity handling', () => {
    const mockLabs = [{ id: 1, name: 'Apex Ceramic Lab' }];

    beforeEach(() => {
        vi.clearAllMocks();
        labsApi.getLaboratories.mockResolvedValue({ data: { data: mockLabs } });
        labsApi.dispatchLabHandoff.mockResolvedValue({
            data: { data: { id: 501, work_item_id: 202, status: 'pending' } },
        });
    });

    it('resolves the lab-ready Crown work_item_id and tooth from real CareSessionRead shape without nested step.work_item', async () => {
        const realSession = {
            id: 10,
            patient_id: 42,
            status: 'in_progress',
            procedures: [
                { id: 1, work_item_id: 101, template_code: 'ENDO_RCT', template_snapshot: { title: 'Root Canal' } },
                { id: 2, work_item_id: 202, template_code: 'PROS_CROWN', template_snapshot: { title: 'Crown Restoration' } },
            ],
            // Real CareSessionStepRead has work_item_id, NO nested work_item
            steps: [
                { id: 11, work_item_id: 101, step_code: 'access', title: 'Access Opening', status: 'completed' },
                { id: 12, work_item_id: 202, step_code: 'impression_scan', title: 'Impression Scan', status: 'completed' },
            ],
            observations: [{ id: 1, work_item_id: 101, tooth_key: '46', observation_code: 'working_length' }],
        };
        const patientWorkItems = [
            { id: 101, kind: 'procedure', code: 'ENDO_RCT', status: 'active', targets: [{ tooth_key: '46' }] },
            { id: 202, kind: 'procedure', code: 'PROS_CROWN', status: 'active', targets: [{ tooth_key: '21' }] },
        ];

        render(
            <FinishCareSessionSheet
                isOpen
                onClose={vi.fn()}
                session={realSession}
                patientWorkItems={patientWorkItems}
                onFinishSession={vi.fn()}
                t={t}
            />
        );

        fireEvent.click(screen.getByTestId('open-lab-handoff-button'));
        await waitFor(() => expect(screen.getByTestId('lab-handoff-sheet')).toBeInTheDocument());
        await waitFor(() => expect(screen.getByTestId('lab-select')).toBeInTheDocument());

        expect(screen.getByTestId('tooth-number-input').value).toBe('21');

        fireEvent.change(screen.getByTestId('lab-select'), { target: { value: '1' } });
        fireEvent.click(screen.getByTestId('submit-lab-handoff'));

        await waitFor(() => {
            expect(labsApi.dispatchLabHandoff).toHaveBeenCalledWith(
                42,
                202,
                expect.objectContaining({
                    laboratory_id: 1,
                    tooth_number: '21',
                    work_type: 'Crown Restoration',
                })
            );
        });
    });

    it('requires explicit selection when multiple lab-eligible procedures are ambiguous and routes to the chosen one', async () => {
        const ambiguousSession = {
            id: 12,
            patient_id: 42,
            status: 'in_progress',
            procedures: [
                { id: 1, work_item_id: 201, template_code: 'PROS_CROWN', template_snapshot: { title: 'Crown Restoration' } },
                { id: 2, work_item_id: 202, template_code: 'PROS_BRIDGE', template_snapshot: { title: 'Fixed Bridge' } },
            ],
            steps: [
                { id: 21, work_item_id: 201, step_code: 'impression_scan', title: 'Impression', status: 'completed' },
                { id: 22, work_item_id: 202, step_code: 'impression_scan', title: 'Impression', status: 'completed' },
            ],
            observations: [],
        };
        const patientWorkItems = [
            { id: 201, kind: 'procedure', code: 'PROS_CROWN', status: 'active', targets: [{ tooth_key: '21' }] },
            { id: 202, kind: 'procedure', code: 'PROS_BRIDGE', status: 'active', targets: [{ tooth_key: '14' }] },
        ];

        render(
            <FinishCareSessionSheet
                isOpen
                onClose={vi.fn()}
                session={ambiguousSession}
                patientWorkItems={patientWorkItems}
                onFinishSession={vi.fn()}
                t={t}
            />
        );

        // Must NOT silently dispatch without an explicit choice
        const openBtn = screen.getByTestId('open-lab-handoff-button');
        expect(openBtn).toBeDisabled();

        const selector = screen.getByTestId('lab-target-procedure-select');
        fireEvent.change(selector, { target: { value: '202' } });
        expect(openBtn).toBeEnabled();

        fireEvent.click(openBtn);
        await waitFor(() => expect(screen.getByTestId('lab-handoff-sheet')).toBeInTheDocument());
        expect(screen.getByTestId('tooth-number-input').value).toBe('14');
    });

    it('routes to the later lab-ready procedure even when earlier steps have nested non-lab work_item', async () => {
        const enrichedSession = {
            id: 13,
            patient_id: 42,
            status: 'in_progress',
            procedures: [
                { id: 1, work_item_id: 101, template_code: 'ENDO_RCT' },
                { id: 2, work_item_id: 202, template_code: 'PROS_CROWN' },
            ],
            steps: [
                {
                    id: 1,
                    work_item_id: 101,
                    step_code: 'access',
                    title: 'Access Opening',
                    status: 'completed',
                    work_item: { id: 101, code: 'ENDO_RCT', targets: [{ tooth_key: '46' }] },
                },
                {
                    id: 2,
                    work_item_id: 202,
                    step_code: 'impression_scan',
                    title: 'Impression Scan',
                    status: 'completed',
                    work_item: { id: 202, code: 'PROS_CROWN', targets: [{ tooth_key: '21' }] },
                },
            ],
            observations: [],
        };

        render(
            <FinishCareSessionSheet
                isOpen
                onClose={vi.fn()}
                session={enrichedSession}
                onFinishSession={vi.fn()}
                t={t}
            />
        );

        fireEvent.click(screen.getByTestId('open-lab-handoff-button'));
        await waitFor(() => expect(screen.getByTestId('lab-handoff-sheet')).toBeInTheDocument());
        expect(screen.getByTestId('tooth-number-input').value).toBe('21');
    });

    it('disables Send to Lab when session has only non-lab procedures (no eligible target)', () => {
        const nonLabSession = {
            id: 14,
            patient_id: 42,
            status: 'in_progress',
            procedures: [{ id: 1, work_item_id: 101, template_code: 'ENDO_RCT' }],
            steps: [{ id: 1, work_item_id: 101, step_code: 'access', title: 'Access', status: 'completed' }],
            observations: [],
        };

        render(
            <FinishCareSessionSheet
                isOpen
                onClose={vi.fn()}
                session={nonLabSession}
                patientWorkItems={[{ id: 101, kind: 'procedure', code: 'ENDO_RCT', status: 'active', targets: [{ tooth_key: '46' }] }]}
                onFinishSession={vi.fn()}
                t={t}
            />
        );

        expect(screen.getByTestId('open-lab-handoff-button')).toBeDisabled();
    });

    it('guards submission inside LabHandoffSheet when workItem has no valid ID', async () => {
        render(
            <LabHandoffSheet
                isOpen
                onClose={vi.fn()}
                patientId={42}
                workItem={null}
                toothKey="21"
                t={t}
            />
        );

        await waitFor(() => expect(labsApi.getLaboratories).toHaveBeenCalled());
        const submitBtn = screen.getByTestId('submit-lab-handoff');
        expect(submitBtn).toBeDisabled();
        fireEvent.click(submitBtn);
        expect(labsApi.dispatchLabHandoff).not.toHaveBeenCalled();
    });
});

describe('Finding 4: QuickTreatmentSheet Missing choice persists without resetting inputs or creating treatment rows for condition-only', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('preserves user inputs and emits explicit Missing when parent updates selectedToothCondition', async () => {
        const onSave = vi.fn().mockResolvedValue({});

        function StatefulParent() {
            const [selectedToothCondition, setSelectedToothCondition] = useState('Healthy');
            const [initialData] = useState({
                id: 55,
                date: '2026-11-23',
                diagnosis: 'Healthy',
                procedure: 'Composite Filling',
                cost: 400,
                tooth_number: 'UR6',
                notes: 'Initial note',
                status: 'Done',
            });

            return (
                <QuickTreatmentSheet
                    isOpen
                    isEditing
                    onClose={vi.fn()}
                    onSave={onSave}
                    initialData={initialData}
                    procedures={[{ id: 1, name: 'Composite Filling', price: 400 }]}
                    selectedToothCondition={selectedToothCondition}
                    setSelectedToothCondition={setSelectedToothCondition}
                />
            );
        }

        withQueryClient(<StatefulParent />);

        // Modify cost before clicking Missing
        const costInput = screen.getByTestId('quick-treatment-cost-input');
        fireEvent.change(costInput, { target: { value: '525' } });
        expect(costInput.value).toBe('525');

        // Click Missing condition chip (triggers parent setSelectedToothCondition('Missing'))
        fireEvent.click(screen.getByRole('button', { name: /مفقود|Missing/i }));

        // Cost edit must NOT have been wiped by form re-initialization!
        expect(screen.getByTestId('quick-treatment-cost-input').value).toBe('525');

        fireEvent.click(screen.getByTestId('quick-treatment-save-button'));

        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        expect(onSave).toHaveBeenCalledWith(
            expect.objectContaining({
                cost: 525,
                explicit_tooth_condition: 'Missing',
            })
        );
    });

    it('does not attach incidental initial Healthy condition when user never clicked a condition chip', async () => {
        const onSave = vi.fn().mockResolvedValue({});
        withQueryClient(
            <QuickTreatmentSheet
                isOpen
                isEditing
                onClose={vi.fn()}
                onSave={onSave}
                initialData={{
                    id: 55,
                    date: '2026-11-23',
                    diagnosis: 'Healthy',
                    procedure: 'Composite Filling',
                    cost: 400,
                    tooth_number: 'UR6',
                    status: 'Done',
                }}
                procedures={[{ id: 1, name: 'Composite Filling', price: 400 }]}
                selectedToothCondition="Healthy"
                setSelectedToothCondition={vi.fn()}
            />
        );

        fireEvent.click(screen.getByTestId('quick-treatment-save-button'));
        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        expect(onSave.mock.calls[0][0].explicit_tooth_condition).toBeUndefined();
    });

    it('condition-only save updates tooth_status with Missing without calling createTreatment', async () => {
        const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
        const wrapper = ({ children }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
        const refetchHistory = vi.fn().mockResolvedValue({});
        const refetchTeeth = vi.fn().mockResolvedValue({});
        const refetchWorkspace = vi.fn().mockResolvedValue({});
        const setIsTreatmentSheetOpen = vi.fn();
        const setEditingTreatmentId = vi.fn();

        const { result } = renderHook(
            () =>
                useTreatmentOperations({
                    patientId: 101,
                    refetchHistory,
                    refetchTeeth,
                    refetchWorkspace,
                    setIsTreatmentSheetOpen,
                    setEditingTreatmentId,
                    editingTreatmentId: null,
                    selectedToothCondition: 'Healthy',
                }),
            { wrapper }
        );

        await act(async () => {
            await result.current.handleSaveTreatment({
                procedure: '',
                tooth_number: 'UR6',
                cost: 0,
                explicit_tooth_condition: 'Missing',
            });
        });

        expect(api.createTreatment).not.toHaveBeenCalled();
        expect(api.updateToothStatus).toHaveBeenCalledWith({
            patient_id: 101,
            tooth_number: 16,
            condition: 'Missing',
        });
        expect(setIsTreatmentSheetOpen).toHaveBeenCalledWith(false);
    });
});

describe('Finding 5: Proposed native procedures surfaced truthfully in TreatmentHistory without duplicates or legacy actions', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useAuthStore.setState({ user: { id: 1, role: 'doctor', permissions: ['clinical:write'] } });
    });

    it('surfaces unlinked proposed procedures with Proposed status, suppresses duplicates, and hides legacy edit/delete actions', async () => {
        const onEdit = vi.fn();
        const onDelete = vi.fn();

        patientsApi.getPatientClinicalWorkItems.mockResolvedValueOnce({
            data: [
                // Unlinked proposed procedure -> MUST appear
                {
                    id: 301,
                    kind: 'procedure',
                    code: 'SURG_EXTRACTION',
                    status: 'proposed',
                    created_at: '2026-11-23T10:00:00Z',
                    targets: [{ target_kind: 'tooth', tooth_key: '46' }],
                    notes: 'Proposed extraction from Quick Actions',
                },
                // Already linked to legacy treatment row (work_item_id: 302) -> MUST NOT duplicate
                {
                    id: 302,
                    kind: 'procedure',
                    code: 'ENDO_RCT',
                    status: 'proposed',
                    created_at: '2026-11-23T09:00:00Z',
                    targets: [{ target_kind: 'tooth', tooth_key: '16' }],
                },
                // Finding (not procedure) -> MUST NOT appear as procedure
                {
                    id: 303,
                    kind: 'finding',
                    code: 'CARIES',
                    status: 'proposed',
                    created_at: '2026-11-23T09:00:00Z',
                    targets: [{ target_kind: 'tooth', tooth_key: '11' }],
                },
            ],
        });

        const legacyHistory = [
            {
                id: 50,
                work_item_id: 302,
                date: '2026-11-23T09:00:00Z',
                tooth_number: 16,
                diagnosis: 'Pulpitis',
                procedure: 'Root Canal Treatment',
                status: 'In Progress',
            },
        ];

        withQueryClient(
            <TreatmentHistory
                nativeWritesEnabled
                patientId={42}
                history={legacyHistory}
                careSessions={[]}
                onEdit={onEdit}
                onDelete={onDelete}
            />
        );

        const proposedRow = await screen.findByTestId('proposed-work-item-row-301');
        expect(proposedRow).toBeInTheDocument();
        expect(proposedRow).toHaveTextContent(/Proposed|مقترح/i);
        expect(proposedRow).toHaveTextContent(/Surgical Extraction|خلع/i);
        // Must NOT show In Progress or legacy Edit/Delete buttons for proposed row
        expect(proposedRow).not.toHaveTextContent(/In Progress/i);
        expect(proposedRow.querySelectorAll('button[title="Edit"], button[title="Delete"]')).toHaveLength(0);

        // Linked work item 302 must NOT render a duplicate proposed row
        expect(screen.queryByTestId('proposed-work-item-row-302')).not.toBeInTheDocument();
        // Finding 303 must NOT appear
        expect(screen.queryByTestId('proposed-work-item-row-303')).not.toBeInTheDocument();
        // Legacy linked row remains intact
        expect(screen.getByText('Root Canal Treatment')).toBeInTheDocument();
    });

    it('renders proposed procedures even when legacy /treatments history is empty', async () => {
        patientsApi.getPatientClinicalWorkItems.mockResolvedValueOnce({
            data: [
                {
                    id: 401,
                    kind: 'procedure',
                    code: 'SURG_EXTRACTION',
                    status: 'proposed',
                    created_at: '2026-11-23T10:00:00Z',
                    targets: [{ target_kind: 'tooth', tooth_key: '36' }],
                },
            ],
        });

        withQueryClient(
            <TreatmentHistory
                nativeWritesEnabled
                patientId={42}
                history={[]}
                careSessions={[]}
            />
        );

        const row = await screen.findByTestId('proposed-work-item-row-401');
        expect(row).toBeInTheDocument();
        expect(row).toHaveTextContent(/Proposed|مقترح/i);
        expect(screen.queryByText(/No treatment or visit history recorded yet/i)).not.toBeInTheDocument();
    });
});
