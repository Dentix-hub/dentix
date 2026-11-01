import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CanalTargetSelector from '@/features/care-sessions/CanalTargetSelector';
import WorkingLengthEntryTable from '@/features/care-sessions/WorkingLengthEntryTable';
import FinishCareSessionSheet from '@/features/care-sessions/FinishCareSessionSheet';
import RctStructuredCard from '@/features/care-sessions/RctStructuredCard';
import CareSessionActiveBanner from '@/features/care-sessions/CareSessionActiveBanner';

describe('Slice S20: Chairside RCT Structured UI & Canal Targeting', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('G10-M09: CanalTargetSelector', () => {
        it('renders anatomical roots and canal presets for Tooth 46', () => {
            const onToggle = vi.fn();
            render(
                <CanalTargetSelector
                    toothKey="46"
                    selectedCanals={[{ canalId: 'MB', rootId: 'mesial' }]}
                    onToggleCanal={onToggle}
                />
            );

            expect(screen.getByTestId('canal-target-selector')).toBeInTheDocument();
            expect(screen.getByText(/Canal Targets/i)).toBeInTheDocument();
            expect(screen.getByText(/Tooth 46/i)).toBeInTheDocument();

            // Root groups
            expect(screen.getAllByText(/Mesial \(M\)/i).length).toBeGreaterThan(0);
            expect(screen.getAllByText(/Distal \(D\)/i).length).toBeGreaterThan(0);

            // Default canal chips
            expect(screen.getByTestId('canal-chip-MB')).toBeInTheDocument();
            expect(screen.getByTestId('canal-chip-ML')).toBeInTheDocument();
            expect(screen.getByTestId('canal-chip-D')).toBeInTheDocument();

            // Selected state
            expect(screen.getByTestId('canal-chip-MB')).toHaveAttribute('aria-pressed', 'true');
            expect(screen.getByTestId('canal-chip-ML')).toHaveAttribute('aria-pressed', 'false');
        });

        it('toggles canal selection when clicking a canal chip', () => {
            const onToggle = vi.fn();
            render(
                <CanalTargetSelector
                    toothKey="46"
                    selectedCanals={[]}
                    onToggleCanal={onToggle}
                />
            );

            fireEvent.click(screen.getByTestId('canal-chip-ML'));
            expect(onToggle).toHaveBeenCalledWith({
                canalId: 'ML',
                rootId: 'mesial',
            });

            fireEvent.click(screen.getByTestId('canal-chip-D'));
            expect(onToggle).toHaveBeenCalledWith({
                canalId: 'D',
                rootId: 'distal',
            });
        });

        it('allows adding and selecting a custom canal', () => {
            const onToggle = vi.fn();
            render(
                <CanalTargetSelector
                    toothKey="46"
                    selectedCanals={[]}
                    onToggleCanal={onToggle}
                />
            );

            const input = screen.getByTestId('custom-canal-input');
            fireEvent.change(input, { target: { value: 'MM' } }); // Middle Mesial

            const addButton = screen.getByTestId('add-custom-canal-button');
            fireEvent.click(addButton);

            expect(onToggle).toHaveBeenCalledWith({
                canalId: 'MM',
                rootId: 'mesial',
            });
        });

        it('adds a custom canal inside a visit form without nesting or submitting forms', () => {
            const onSubmit = vi.fn((event) => event.preventDefault());
            const onToggle = vi.fn();
            const { container } = render(
                <form onSubmit={onSubmit}>
                    <CanalTargetSelector toothKey="46" selectedCanals={[]} onToggleCanal={onToggle} />
                </form>
            );
            expect(container.querySelectorAll('form')).toHaveLength(1);
            fireEvent.change(screen.getByTestId('custom-canal-input'), { target: { value: 'MM' } });
            fireEvent.keyDown(screen.getByTestId('custom-canal-input'), { key: 'Enter' });
            expect(onToggle).toHaveBeenCalledWith({ canalId: 'MM', rootId: 'mesial' });
            expect(onSubmit).not.toHaveBeenCalled();
        });
    });

    describe('G10-M10: WorkingLengthEntryTable', () => {
        it('shows empty placeholder when no canals are selected', () => {
            render(
                <WorkingLengthEntryTable
                    toothKey="46"
                    selectedCanals={[]}
                    onSaveMeasurement={vi.fn()}
                />
            );

            expect(screen.getByTestId('working-length-empty')).toBeInTheDocument();
        });

        it('renders measurement entry rows for selected canals', () => {
            render(
                <WorkingLengthEntryTable
                    toothKey="46"
                    selectedCanals={[
                        { canalId: 'MB', rootId: 'mesial' },
                        { canalId: 'ML', rootId: 'mesial' },
                        { canalId: 'D', rootId: 'distal' },
                    ]}
                    onSaveMeasurement={vi.fn()}
                />
            );

            expect(screen.getByTestId('working-length-table')).toBeInTheDocument();
            expect(screen.getByTestId('canal-entry-row-MB')).toBeInTheDocument();
            expect(screen.getByTestId('canal-entry-row-ML')).toBeInTheDocument();
            expect(screen.getByTestId('canal-entry-row-D')).toBeInTheDocument();
        });

        it('captures structured length, reference point, MAF, and saves measurement', () => {
            const onSave = vi.fn();
            render(
                <WorkingLengthEntryTable
                    toothKey="46"
                    selectedCanals={[{ canalId: 'MB', rootId: 'mesial' }]}
                    onSaveMeasurement={onSave}
                />
            );

            // Enter length
            const lengthInput = screen.getByTestId('input-length-MB');
            fireEvent.change(lengthInput, { target: { value: '21.5' } });

            // Choose reference point
            const refSelect = screen.getByTestId('select-ref-MB');
            fireEvent.change(refSelect, { target: { value: 'MB cusp' } });

            // Choose MAF size
            const mafSelect = screen.getByTestId('select-maf-MB');
            fireEvent.change(mafSelect, { target: { value: '#25' } });

            fireEvent.change(screen.getByTestId('input-taper-MB'), { target: { value: '0.04' } });

            // Enter notes
            const notesInput = screen.getByTestId('input-notes-MB');
            fireEvent.change(notesInput, { target: { value: 'Definite apical stop' } });

            // Click save
            const saveBtn = screen.getByTestId('btn-save-measurement-MB');
            fireEvent.click(saveBtn);

            expect(onSave).toHaveBeenCalledWith({
                canal_id: 'MB',
                root_id: 'mesial',
                tooth_key: '46',
                length_mm: 21.5,
                reference_point: 'MB cusp',
                maf: '#25',
                taper: 0.04,
                notes: 'Definite apical stop',
            });
        });

        it('renders previously recorded canal measurements badge', () => {
            render(
                <WorkingLengthEntryTable
                    toothKey="46"
                    selectedCanals={[{ canalId: 'MB', rootId: 'mesial' }]}
                    recordedObservations={[
                        {
                            id: 101,
                            observation_code: 'working_length',
                            tooth_key: '46',
                            canal_id: 'MB',
                            root_id: 'mesial',
                            structured_value: {
                                length_mm: 21.5,
                                reference_point: 'MB cusp',
                                maf: '#25 / .04',
                            },
                        },
                    ]}
                    onSaveMeasurement={vi.fn()}
                />
            );

            expect(screen.getByTestId('latest-measurement-MB')).toBeInTheDocument();
            expect(screen.getByTestId('latest-measurement-MB')).toHaveTextContent('21.5 mm');
            expect(screen.getByTestId('latest-measurement-MB')).toHaveTextContent('MB cusp');
        });
    });

    describe('G10-M11: FinishCareSessionSheet', () => {
        const mockSession = {
            id: 42,
            status: 'in_progress',
            started_at: '2026-10-19T10:00:00Z',
            steps: [
                { id: 1, step_code: 'assessment', title: 'Assessment', status: 'completed' },
                { id: 2, step_code: 'access', title: 'Access', status: 'completed' },
                { id: 3, step_code: 'canal_measurement', title: 'Length', status: 'partial' },
                { id: 4, step_code: 'clean_shape', title: 'Clean & Shape', status: 'pending' },
            ],
            observations: [
                {
                    id: 201,
                    observation_code: 'working_length',
                    canal_id: 'MB',
                    structured_value: { length_mm: 21.5, maf: '#25 / .04' },
                },
                {
                    id: 202,
                    observation_code: 'working_length',
                    canal_id: 'ML',
                    structured_value: { length_mm: 21.0, maf: '#25 / .04' },
                },
            ],
        };

        it('displays steps summary breakdown and recorded canal lengths', () => {
            render(
                <FinishCareSessionSheet
                    isOpen={true}
                    onClose={vi.fn()}
                    session={mockSession}
                    onFinishSession={vi.fn()}
                />
            );

            expect(screen.getByTestId('finish-care-session-form')).toBeInTheDocument();
            expect(screen.getByText('Session #42')).toBeInTheDocument();

            // Step counts
            expect(screen.getByText('Completed')).toBeInTheDocument();
            expect(screen.getByText('Partial')).toBeInTheDocument();
            expect(screen.getByText('Pending')).toBeInTheDocument();

            // Observations summary
            expect(screen.getByTestId('finish-sheet-canal-measurements')).toBeInTheDocument();
            expect(screen.getByText('21.5 mm')).toBeInTheDocument();
            expect(screen.getByText(/21(\.0)? mm/)).toBeInTheDocument();
        });

        it('allows inputting clinical finalization notes and finishes session', async () => {
            const onFinish = vi.fn().mockResolvedValue({});
            const onClose = vi.fn();

            render(
                <FinishCareSessionSheet
                    isOpen={true}
                    onClose={onClose}
                    session={mockSession}
                    onFinishSession={onFinish}
                />
            );

            const notesInput = screen.getByTestId('finish-session-notes-input');
            fireEvent.change(notesInput, {
                target: { value: 'Patient tolerated treatment well. Temporary dressing placed.' },
            });

            const submitBtn = screen.getByTestId('confirm-finish-session-button');
            fireEvent.click(submitBtn);

            await waitFor(() => {
                expect(onFinish).toHaveBeenCalledWith({
                    notes: 'Patient tolerated treatment well. Temporary dressing placed.',
                });
                expect(onClose).toHaveBeenCalled();
            });
        });
    });

    describe('G10-M08: RctStructuredCard', () => {
        const mockRctSession = {
            id: 77,
            status: 'in_progress',
            steps: [
                { id: 11, step_code: 'assessment', title: 'Clinical Assessment', status: 'completed' },
                { id: 12, step_code: 'access', title: 'Access Cavity Preparation', status: 'in_progress' },
                { id: 13, step_code: 'canal_measurement', title: 'Working Length Determination', status: 'pending' },
                { id: 14, step_code: 'clean_shape', title: 'Cleaning & Shaping', status: 'pending' },
                { id: 15, step_code: 'obturate', title: 'Canal Obturation', status: 'pending' },
                { id: 16, step_code: 'restore', title: 'Coronal Seal', status: 'pending' },
            ],
            observations: [],
        };

        it('renders all canonical RCT workflow steps and step action buttons', () => {
            const onUpdateStep = vi.fn();
            render(
                <RctStructuredCard
                    session={mockRctSession}
                    toothKey="46"
                    onUpdateStepStatus={onUpdateStep}
                    onSaveObservation={vi.fn()}
                    onFinishSession={vi.fn()}
                />
            );

            expect(screen.getByTestId('rct-structured-card')).toBeInTheDocument();
            expect(screen.getByText(/Tooth 46/i)).toBeInTheDocument();

            // All 6 steps rendered
            expect(screen.getByTestId('rct-step-row-assessment')).toBeInTheDocument();
            expect(screen.getByTestId('rct-step-row-access')).toBeInTheDocument();
            expect(screen.getByTestId('rct-step-row-canal_measurement')).toBeInTheDocument();
            expect(screen.getByTestId('rct-step-row-clean_shape')).toBeInTheDocument();
            expect(screen.getByTestId('rct-step-row-obturate')).toBeInTheDocument();
            expect(screen.getByTestId('rct-step-row-restore')).toBeInTheDocument();

            // Complete button action
            const completeBtn = screen.getByTestId('btn-complete-access');
            fireEvent.click(completeBtn);
            expect(onUpdateStep).toHaveBeenCalledWith(12, { status: 'completed' });
        });

        it('supports marking step as partial with remarks (G10-M05, G10-M15)', () => {
            const onUpdateStep = vi.fn();
            render(
                <RctStructuredCard
                    session={mockRctSession}
                    toothKey="46"
                    onUpdateStepStatus={onUpdateStep}
                    onSaveObservation={vi.fn()}
                    onFinishSession={vi.fn()}
                />
            );

            // Click partial button on access step
            const partialBtn = screen.getByTestId('btn-partial-access');
            fireEvent.click(partialBtn);

            // Shows inline partial prompt
            expect(screen.getByTestId('partial-prompt-access')).toBeInTheDocument();

            // Type note
            const noteInput = screen.getByTestId('input-partial-note-access');
            fireEvent.change(noteInput, { target: { value: 'Pulp chamber exposed, calcified orifice.' } });

            // Confirm partial
            const confirmBtn = screen.getByTestId('btn-confirm-partial-access');
            fireEvent.click(confirmBtn);

            expect(onUpdateStep).toHaveBeenCalledWith(12, {
                status: 'partial',
                notes: 'Pulp chamber exposed, calcified orifice.',
            });
        });

        it('switches between Workflow Steps and Canals & Measurements tabs', () => {
            render(
                <RctStructuredCard
                    session={mockRctSession}
                    toothKey="46"
                    onUpdateStepStatus={vi.fn()}
                    onSaveObservation={vi.fn()}
                    onFinishSession={vi.fn()}
                />
            );

            // Click Canals tab
            const canalsTab = screen.getByTestId('tab-rct-canals');
            fireEvent.click(canalsTab);

            expect(screen.getByTestId('canal-target-selector')).toBeInTheDocument();
            expect(screen.getByTestId('working-length-table')).toBeInTheDocument();

            // Switch back to Steps tab
            const stepsTab = screen.getByTestId('tab-rct-steps');
            fireEvent.click(stepsTab);

            expect(screen.getByTestId('rct-steps-container')).toBeInTheDocument();
        });

        it('opens finish session sheet on clicking Finish Session button', () => {
            render(
                <RctStructuredCard
                    session={mockRctSession}
                    toothKey="46"
                    onUpdateStepStatus={vi.fn()}
                    onSaveObservation={vi.fn()}
                    onFinishSession={vi.fn()}
                />
            );

            const finishBtn = screen.getByTestId('btn-open-finish-sheet');
            fireEvent.click(finishBtn);

            expect(screen.getByTestId('finish-care-session-form')).toBeInTheDocument();
        });
    });

    describe('CareSessionActiveBanner', () => {
        const activeSession = {
            id: 88,
            status: 'in_progress',
            started_at: '2026-10-19T09:30:00Z',
            steps: [
                { id: 1, status: 'completed' },
                { id: 2, status: 'completed' },
                { id: 3, status: 'pending' },
            ],
            observations: [{ id: 10 }],
        };

        it('renders active care session status banner with step counts and actions', () => {
            const onOpenWorkflow = vi.fn();
            const onOpenFinish = vi.fn();

            render(
                <CareSessionActiveBanner
                    session={activeSession}
                    onOpenWorkflow={onOpenWorkflow}
                    onOpenFinishSheet={onOpenFinish}
                />
            );

            expect(screen.getByTestId('care-session-active-banner')).toBeInTheDocument();
            expect(screen.getByText(/Active Care Session/i)).toBeInTheDocument();
            expect(screen.getByText(/#88/i)).toBeInTheDocument();
            expect(screen.getByText(/2 of 3 steps addressed/i)).toBeInTheDocument();

            // Button actions
            fireEvent.click(screen.getByTestId('btn-open-active-workflow'));
            expect(onOpenWorkflow).toHaveBeenCalled();

            fireEvent.click(screen.getByTestId('btn-banner-finish-session'));
            expect(onOpenFinish).toHaveBeenCalled();
        });

        it('renders null when session is not in_progress', () => {
            const { container } = render(
                <CareSessionActiveBanner
                    session={{ id: 88, status: 'completed' }}
                    onOpenWorkflow={vi.fn()}
                    onOpenFinishSheet={vi.fn()}
                />
            );

            expect(container.firstChild).toBeNull();
        });
    });
});
