import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { getPatientCareSessions } from '@/api/patients';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import GenericVisitWorkspace from '@/features/care-sessions/GenericVisitWorkspace';
import TreatmentHistory from '@/features/patients/PatientTabs/TreatmentHistory';

const { historicalProps } = vi.hoisted(() => ({ historicalProps: vi.fn() }));

vi.mock('@/api/patients', () => ({
    addCareSessionProcedure: vi.fn(),
    removeCareSessionProcedure: vi.fn(),
    addCareSessionStep: vi.fn(),
    getPatientCareSessions: vi.fn().mockResolvedValue({ data: { data: [] } }),
    updateClinicalWorkItemStatus: vi.fn(),
}));

vi.mock('@/api/admin', () => ({
    getDoctors: vi.fn().mockResolvedValue({ data: { doctors: [] } }),
}));

vi.mock('@/features/care-sessions/HistoricalCareSessionModal', () => ({
    default: (props) => {
        historicalProps(props);
        return <div>Historical entry</div>;
    },
}));

vi.mock('@/store/auth.store', () => ({
    useAuthStore: (selector) =>
        selector({
            user: { id: 1, role: 'doctor', permissions: ['clinical:write'] },
        }),
}));

const t = (key, fallback) => fallback || key;

function wrap(node) {
    return render(
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
            {node}
        </QueryClientProvider>
    );
}

function workspace(code = 'ENDO_RCT', extra = {}) {
    const item = {
        id: 10,
        code,
        status: 'active',
        kind: 'procedure',
        targets: [{ tooth_key: '46', target_kind: 'canal', root_id: 'mesial', canal_id: 'MB' }],
    };
    return (
        <GenericVisitWorkspace
            isOpen
            session={{
                id: 1,
                patient_id: 1,
                status: 'in_progress',
                procedures: [{ id: 11, work_item_id: 10, template_snapshot: { custom_fields: [] } }],
                steps: [],
                observations: [],
            }}
            patient={{ id: 1, name: 'Synthetic' }}
            patientWorkItems={[item]}
            onClose={vi.fn()}
            onOpenFinishSheet={vi.fn()}
            onSaveObservation={vi.fn()}
            t={t}
            {...extra}
        />
    );
}

describe('GenericVisitWorkspace and TreatmentHistory regressions', () => {
    it('recalls the previous procedure notes and next action for a non-RCT visit', async () => {
        getPatientCareSessions.mockResolvedValueOnce({ data: [{ id: 99, status: 'completed', actual_visit_date: '2026-10-01T10:00:00Z', created_at: '2026-10-01T10:00:00Z', notes: 'Last visit summary', procedures: [{ id: 12, work_item_id: 10, procedure_notes: 'Provisional crown fitted', next_action: 'Check margin fit' }] }] });
        wrap(workspace('PROS_CROWN'));
        expect(await screen.findByTestId('workspace-previous-context')).toHaveTextContent('Provisional crown fitted');
        expect(screen.getByTestId('workspace-previous-context')).toHaveTextContent('Check margin fit');
    });

    it('keeps measurements isolated when switching between two RCT procedures', () => {
        const items = [10, 20].map((id, index) => ({ id, kind: 'procedure', code: 'ENDO_RCT', targets: [{ target_kind: 'canal', tooth_key: String(46 - index), canal_id: 'MB', root_id: 'mesial' }] }));
        wrap(workspace('ENDO_RCT', { patientWorkItems: items, session: { id: 1, patient_id: 1, procedures: items.map((item) => ({ id: item.id, work_item_id: item.id })), steps: [], observations: [] } }));
        fireEvent.change(screen.getByTestId('input-length-MB'), { target: { value: '21.5' } });
        fireEvent.change(screen.getByTestId('input-notes-MB'), { target: { value: 'First tooth only' } });
        fireEvent.click(screen.getByTestId('tab-proc-20'));
        expect(screen.getByTestId('input-length-MB')).toHaveValue(null);
        expect(screen.getByTestId('input-notes-MB')).toHaveValue('');
    });

    it('retains functional RCT measurement controls in the replacement workspace', () => {
        wrap(workspace());
        expect(screen.getByTestId('workspace-rct-tools')).toBeInTheDocument();
        expect(screen.queryByTestId('working-length-empty')).not.toBeInTheDocument();
        expect(screen.getByTestId('working-length-table')).toBeInTheDocument();
    });

    it('enforces required custom fields before finish', () => {
        const finish = vi.fn();
        wrap(
            workspace('REST_COMPOSITE', {
                onOpenFinishSheet: finish,
                session: {
                    id: 1,
                    patient_id: 1,
                    status: 'in_progress',
                    procedures: [
                        {
                            id: 11,
                            work_item_id: 10,
                            template_snapshot: {
                                custom_fields: [
                                    { field_id: 'shade', field_type: 'text', label: 'Shade', is_required: true },
                                ],
                            },
                        },
                    ],
                    steps: [],
                    observations: [],
                },
            })
        );
        const section = screen.getByTestId('generic-visit-workspace');
        const buttons = Array.from(section.querySelectorAll('button'));
        const finishButton = buttons.find((b) => /Finish Visit/i.test(b.textContent));
        expect(finishButton).toBeTruthy();
        fireEvent.click(finishButton);
        expect(finish).not.toHaveBeenCalled();
    });

    it('does not guess a native procedure ID from a legacy treatment row', () => {
        wrap(
            <TreatmentHistory
                patientId={1}
                history={[{ id: 77, procedure: 'Extraction', status: 'Done', date: '2026-10-01', tooth_number: '46' }]}
                careSessions={[]}
                t={t}
            />
        );
        const button = screen.getByTestId('record-past-visit-btn');
        fireEvent.click(button);
        const props = historicalProps.mock.lastCall[0];
        expect(props.patientWorkItems).toEqual([]);
    });
});
