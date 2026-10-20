import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LabHandoffSheet from '@/features/care-sessions/LabHandoffSheet';
import FinishCareSessionSheet from '@/features/care-sessions/FinishCareSessionSheet';
import ClinicalChartInspector from '@/features/clinical-chart/components/ClinicalChartInspector';
import * as labsApi from '@/api/labs';

vi.mock('@/api/labs', () => ({
    getLaboratories: vi.fn(),
    dispatchLabHandoff: vi.fn(),
}));

describe('Slice S28: 1-Tap Lab Handoff Sheet & Non-Duplicating Billing', () => {
    const mockLabs = [
        { id: 1, name: 'Apex Dental Art Lab', phone: '0501234567' },
        { id: 2, name: 'Precision Prosthetics', phone: '0509876543' },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        labsApi.getLaboratories.mockResolvedValue({ data: { data: mockLabs } });
    });

    describe('G12-M06: LabHandoffSheet Component', () => {
        it('renders modal with prefilled patient, tooth number, and procedure work type', async () => {
            render(
                <LabHandoffSheet
                    isOpen={true}
                    onClose={vi.fn()}
                    patientId={42}
                    patientName="Ahmad Al-Harbi"
                    doctorName="Dr. Eslam"
                    toothKey="21"
                    workItem={{
                        id: 101,
                        code: 'PROS_CROWN',
                        title: 'Crown Restoration',
                        targets: [{ tooth_key: '21' }],
                    }}
                />
            );

            expect(screen.getByTestId('lab-handoff-sheet')).toBeInTheDocument();
            expect(screen.getByText(/Ahmad Al-Harbi/i)).toBeInTheDocument();
            expect(screen.getByText(/Tooth 21/i)).toBeInTheDocument();
            expect(screen.getByText(/0 Duplicate Billing \(R06\)/i)).toBeInTheDocument();

            // Wait for laboratories dropdown to populate
            await waitFor(() => {
                expect(screen.getByTestId('lab-select')).toBeInTheDocument();
            });
            expect(screen.getByText(/Apex Dental Art Lab/i)).toBeInTheDocument();
            expect(screen.getByText(/Precision Prosthetics/i)).toBeInTheDocument();
        });

        it('allows selecting shade and material chips, and entering custom notes', async () => {
            render(
                <LabHandoffSheet
                    isOpen={true}
                    onClose={vi.fn()}
                    patientId={42}
                    patientName="Ahmad Al-Harbi"
                    toothKey="21"
                    workItem={{ id: 101, code: 'PROS_CROWN' }}
                />
            );

            await waitFor(() => expect(labsApi.getLaboratories).toHaveBeenCalled());

            // Select shade chip
            const shadeChipA3 = screen.getByRole('button', { name: 'A3' });
            fireEvent.click(shadeChipA3);

            // Select material chip
            const materialChipEmax = screen.getByRole('button', { name: 'E-Max' });
            fireEvent.click(materialChipEmax);

            // Enter notes
            const notesInput = screen.getByTestId('notes-input');
            fireEvent.change(notesInput, { target: { value: 'Subgingival margin on buccal' } });
            expect(notesInput.value).toBe('Subgingival margin on buccal');
        });

        it('submits lab handoff and displays success banner (G12-M06, G12-M08, G12-M09, G12-M16)', async () => {
            labsApi.dispatchLabHandoff.mockResolvedValueOnce({
                data: {
                    data: {
                        id: 501,
                        patient_id: 42,
                        work_item_id: 101,
                        work_type: 'Crown Restoration',
                        tooth_number: '21',
                        shade: 'A2',
                        material: 'Zirconia',
                        status: 'pending',
                        cost: 300,
                        price_to_patient: 1200,
                    },
                },
            });

            const handleSuccess = vi.fn();
            render(
                <LabHandoffSheet
                    isOpen={true}
                    onClose={vi.fn()}
                    patientId={42}
                    patientName="Ahmad Al-Harbi"
                    toothKey="21"
                    workItem={{ id: 101, code: 'PROS_CROWN' }}
                    onSuccess={handleSuccess}
                />
            );

            await waitFor(() => expect(labsApi.getLaboratories).toHaveBeenCalled());

            // Select lab 1
            const labSelect = screen.getByTestId('lab-select');
            fireEvent.change(labSelect, { target: { value: '1' } });

            // Submit
            const submitBtn = screen.getByTestId('submit-lab-handoff');
            fireEvent.click(submitBtn);

            await waitFor(() => {
                expect(labsApi.dispatchLabHandoff).toHaveBeenCalledWith(
                    42,
                    101,
                    expect.objectContaining({
                        laboratory_id: 1,
                        work_type: 'Crown Restoration',
                        tooth_number: '21',
                        shade: 'A2',
                        material: 'Zirconia',
                    })
                );
            });

            // Verify success state
            await waitFor(() => {
                expect(screen.getByTestId('lab-handoff-success')).toBeInTheDocument();
            });
            expect(handleSuccess).toHaveBeenCalledWith(
                expect.objectContaining({ id: 501, work_item_id: 101 })
            );
        });

        it('handles idempotency cleanly when duplicate dispatch returns existing order (G12-M16)', async () => {
            labsApi.dispatchLabHandoff.mockResolvedValue({
                data: {
                    data: {
                        id: 501,
                        patient_id: 42,
                        work_item_id: 101,
                        work_type: 'Crown Restoration',
                        tooth_number: '21',
                        status: 'pending',
                    },
                },
            });

            render(
                <LabHandoffSheet
                    isOpen={true}
                    onClose={vi.fn()}
                    patientId={42}
                    patientName="Ahmad Al-Harbi"
                    toothKey="21"
                    workItem={{ id: 101, code: 'PROS_CROWN' }}
                />
            );

            await waitFor(() => expect(labsApi.getLaboratories).toHaveBeenCalled());

            const labSelect = screen.getByTestId('lab-select');
            fireEvent.change(labSelect, { target: { value: '1' } });

            const submitBtn = screen.getByTestId('submit-lab-handoff');
            fireEvent.click(submitBtn);

            await waitFor(() => {
                expect(screen.getByTestId('lab-handoff-success')).toBeInTheDocument();
            });
            expect(screen.getByText(/Lab Order #501 linked to Work Item #101/i)).toBeInTheDocument();
        });
    });

    describe('G12-M05 & G12-M06: FinishCareSessionSheet Lab Handoff Trigger', () => {
        it('renders lab handoff trigger section inside FinishCareSessionSheet', () => {
            const mockSession = {
                id: 10,
                patient_id: 42,
                steps: [
                    { id: 1, step_code: 'preparation', title: 'Tooth Preparation', status: 'completed' },
                    { id: 2, step_code: 'impression_scan', title: 'Digital Intraoral Scan', status: 'completed' },
                ],
                observations: [],
            };

            render(
                <FinishCareSessionSheet
                    isOpen={true}
                    onClose={vi.fn()}
                    session={mockSession}
                    onFinishSession={vi.fn()}
                />
            );

            expect(screen.getByTestId('lab-handoff-trigger-section')).toBeInTheDocument();
            expect(screen.getByTestId('open-lab-handoff-button')).toBeInTheDocument();
            expect(screen.getByText(/Preparation \/ impression step recorded/i)).toBeInTheDocument();
        });

        it('opens LabHandoffSheet when clicking Send to Lab from FinishCareSessionSheet', async () => {
            const mockSession = {
                id: 10,
                patient_id: 42,
                tooth_key: '21',
                steps: [
                    {
                        id: 1,
                        step_code: 'preparation',
                        title: 'Tooth Preparation',
                        status: 'completed',
                        work_item: { id: 101, code: 'PROS_CROWN', targets: [{ tooth_key: '21' }] },
                    },
                ],
                observations: [],
            };

            render(
                <FinishCareSessionSheet
                    isOpen={true}
                    onClose={vi.fn()}
                    session={mockSession}
                    onFinishSession={vi.fn()}
                />
            );

            const openLabBtn = screen.getByTestId('open-lab-handoff-button');
            fireEvent.click(openLabBtn);

            await waitFor(() => {
                expect(screen.getByTestId('lab-handoff-sheet')).toBeInTheDocument();
            });
        });
    });

    describe('G12-M04 & G12-M06: ClinicalChartInspector Lab Trigger', () => {
        it('displays Send to Lab button for lab-required procedures (e.g. PROS_CROWN)', () => {
            const mockToothState = {
                findings: [],
                procedures: [
                    {
                        id: 'proc_1',
                        code: 'PROS_CROWN',
                        name: 'Crown Restoration',
                        status: 'active',
                    },
                ],
            };

            render(
                <ClinicalChartInspector
                    copy={{ sendToLab: 'Send to Lab' }}
                    selection={{ toothKey: '21' }}
                    toothState={mockToothState}
                    patientId={42}
                />
            );

            expect(screen.getByTestId(/lab-handoff-/)).toBeInTheDocument();
        });

        it('does NOT display Send to Lab button for non-lab procedures (e.g. REST_COMPOSITE)', () => {
            const mockToothState = {
                findings: [],
                procedures: [
                    {
                        id: 'proc_2',
                        code: 'REST_COMPOSITE',
                        name: 'Composite Restoration',
                        status: 'completed',
                    },
                ],
            };

            render(
                <ClinicalChartInspector
                    copy={{ sendToLab: 'Send to Lab' }}
                    selection={{ toothKey: '16' }}
                    toothState={mockToothState}
                    patientId={42}
                />
            );

            expect(screen.queryByTestId(/lab-handoff-/)).not.toBeInTheDocument();
        });
    });
});
