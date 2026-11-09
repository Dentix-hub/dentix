import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import WorkflowTemplateEditor from './WorkflowTemplateEditor';
import * as workflowTemplatesApi from '@/api/workflowTemplates';

vi.mock('@/api/workflowTemplates', () => ({
    createWorkflowTemplate: vi.fn(),
    updateWorkflowTemplate: vi.fn(),
}));

describe('WorkflowTemplateEditor', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders template builder with initial steps and fields', () => {
        render(<WorkflowTemplateEditor onCancel={vi.fn()} onSaveSuccess={vi.fn()} />);

        expect(screen.getByText(/Create Clinic Workflow Template/i)).toBeInTheDocument();
        expect(screen.getByTestId('input-template-code')).toBeInTheDocument();
        expect(screen.getByTestId('input-template-title')).toBeInTheDocument();
        expect(screen.getByTestId('tab-steps')).toBeInTheDocument();
        expect(screen.getByTestId('tab-custom-fields')).toBeInTheDocument();
    });

    it('validates against empty code and missing steps', async () => {
        render(<WorkflowTemplateEditor onCancel={vi.fn()} onSaveSuccess={vi.fn()} />);

        // Clear prefilled code
        const codeInput = screen.getByTestId('input-template-code');
        fireEvent.change(codeInput, { target: { value: '' } });

        const saveBtn = screen.getByTestId('btn-save-template');
        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(screen.getByTestId('template-validation-error')).toBeInTheDocument();
        });
    });

    it('keeps identities distinct after deleting and adding steps and fields', async () => {
        const definition = { steps: [1, 2, 3].map((number) => ({ step_code: `step_${number}`, step_order: number, title: `Stage ${number}` })), custom_fields: [1, 2, 3].map((number) => ({ field_id: `custom_field_${number}`, field_type: 'text', label: `Field ${number}` })) };
        const original = JSON.parse(JSON.stringify(definition));
        workflowTemplatesApi.updateWorkflowTemplate.mockResolvedValue({ data: { id: 2 } });
        render(<WorkflowTemplateEditor template={{ id: 1, template_code: 'REST_COMPOSITE', title: 'Restorative', definition }} onCancel={vi.fn()} onSaveSuccess={vi.fn()} />);
        fireEvent.click(screen.getByTestId('btn-remove-step-1'));
        fireEvent.click(screen.getByTestId('btn-add-step'));
        const generatedStep = screen.getByTestId('step-code-2').value;
        expect(['step_1', 'step_2', 'step_3']).not.toContain(generatedStep);
        fireEvent.click(screen.getByTestId('tab-custom-fields'));
        fireEvent.click(screen.getByTestId('btn-remove-field-1'));
        fireEvent.click(screen.getByTestId('btn-add-field'));
        expect(['custom_field_1', 'custom_field_2', 'custom_field_3']).not.toContain(screen.getByTestId('field-id-2').value);
        fireEvent.click(screen.getByTestId('btn-save-template'));
        await waitFor(() => expect(workflowTemplatesApi.updateWorkflowTemplate).toHaveBeenCalledTimes(1));
        const saved = workflowTemplatesApi.updateWorkflowTemplate.mock.lastCall[1].definition;
        expect(new Set(saved.steps.map((step) => step.step_code)).size).toBe(3);
        expect(new Set(saved.custom_fields.map((field) => field.field_id)).size).toBe(3);
        expect(definition).toEqual(original);
    });

    it('allows adding custom fields and saving template', async () => {
        const mockOnSuccess = vi.fn();
        workflowTemplatesApi.createWorkflowTemplate.mockResolvedValueOnce({ data: { id: 1 } });

        render(<WorkflowTemplateEditor onCancel={vi.fn()} onSaveSuccess={mockOnSuccess} />);

        // Fill basic metadata
        fireEvent.change(screen.getByTestId('input-template-code'), {
            target: { value: 'SURG_BIOPSY' },
        });
        fireEvent.change(screen.getByTestId('input-template-title'), {
            target: { value: 'Oral Mucosal Biopsy Protocol' },
        });

        // Switch to custom fields tab and add a custom field
        const customFieldsTab = screen.getByTestId('tab-custom-fields');
        fireEvent.click(customFieldsTab);

        const addFieldBtn = screen.getByTestId('btn-add-field');
        fireEvent.click(addFieldBtn);

        const fieldIdInput = screen.getByTestId('field-id-0');
        fireEvent.change(fieldIdInput, { target: { value: 'specimen_site' } });

        const fieldLabelInput = screen.getByTestId('field-label-0');
        fireEvent.change(fieldLabelInput, { target: { value: 'Specimen Anatomical Site' } });

        // Save
        const saveBtn = screen.getByTestId('btn-save-template');
        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(workflowTemplatesApi.createWorkflowTemplate).toHaveBeenCalledTimes(1);
            expect(workflowTemplatesApi.createWorkflowTemplate).toHaveBeenCalledWith(
                expect.objectContaining({
                    template_code: 'SURG_BIOPSY',
                    title: 'Oral Mucosal Biopsy Protocol',
                    definition: expect.objectContaining({
                        steps: expect.any(Array),
                        custom_fields: expect.arrayContaining([
                            expect.objectContaining({
                                field_id: 'specimen_site',
                                label: 'Specimen Anatomical Site',
                            }),
                        ]),
                    }),
                })
            );
            expect(mockOnSuccess).toHaveBeenCalledTimes(1);
        });
    });
});
