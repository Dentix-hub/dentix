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
