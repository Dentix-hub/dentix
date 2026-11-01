import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import GenericVisitWorkspace from './GenericVisitWorkspace';
import { getMaterials } from '@/api/inventory';
import { getCareSessionMaterialSuggestions, getCareSessionMaterialCost, recordCareSessionMaterials } from '@/api/patients';

const { createLink, imageLinkQuery } = vi.hoisted(() => ({ createLink: vi.fn(), imageLinkQuery: vi.fn() }));
vi.mock('@/api/inventory', () => ({ getMaterials: vi.fn() }));
vi.mock('@/api/patients', async (original) => ({
    ...await original(), getCareSessionMaterialSuggestions: vi.fn(), getCareSessionMaterialCost: vi.fn(), recordCareSessionMaterials: vi.fn(), getPatientCareSessions: vi.fn().mockResolvedValue({ data: [] }),
}));
vi.mock('@/hooks/usePatientDetails', () => ({
    usePatientAttachments: () => ({ data: [{ id: 55, filename: 'Synthetic radiograph.jpg', file_type: 'image/jpeg', file_path: '/synthetic.jpg' }] }),
    usePatientClinicalAttachmentLinks: (...args) => { imageLinkQuery(...args); return { data: [] }; },
    useCreateClinicalAttachmentLink: () => ({ mutateAsync: createLink }),
    useDeleteClinicalAttachmentLink: () => ({ mutateAsync: vi.fn() }),
}));

const t = (key, fallback) => fallback || key;
function workspace(client = new QueryClient({ defaultOptions: { queries: { retry: false } } })) {
    return render(<QueryClientProvider client={client}>
        <GenericVisitWorkspace isOpen session={{ id: 77, patient_id: 123, status: 'in_progress', steps: [], observations: [], procedures: [{ id: 1, work_item_id: 101 }, { id: 2, work_item_id: 102 }] }} patient={{ id: 123 }} patientWorkItems={[{ id: 101, code: 'REST_COMPOSITE', title: 'Composite' }, { id: 102, code: 'SURG_EXTRACTION', title: 'Extraction' }]} onClose={vi.fn()} onOpenFinishSheet={vi.fn()} t={t} />
    </QueryClientProvider>);
}
beforeEach(() => {
    vi.clearAllMocks();
    getMaterials.mockResolvedValue({ data: [{ id: 9, name: 'Synthetic gauze', base_unit: 'unit' }] });
    getCareSessionMaterialSuggestions.mockResolvedValue({ data: { suggestions: [] } });
    getCareSessionMaterialCost.mockResolvedValue({ data: { sessions: [] } });
    recordCareSessionMaterials.mockResolvedValue({ data: [{ id: 88 }] });
    createLink.mockResolvedValue({});
});

describe('Chairside resources through the actual generic workspace', () => {
    it('records material usage only after confirmation, for the selected procedure and visit', async () => {
        const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
        client.setQueryData(['inventory-stock'], [{ material_id: 9, quantity: 10 }]);
        workspace(client);
        fireEvent.click(screen.getByTestId('tab-proc-102'));
        fireEvent.click(screen.getByTestId('workspace-materials-btn'));
        await screen.findByText('Synthetic gauze (unit)');
        expect(getCareSessionMaterialSuggestions).toHaveBeenCalledWith(123, 102);
        expect(recordCareSessionMaterials).not.toHaveBeenCalled();
        fireEvent.change(screen.getByLabelText('Material'), { target: { value: '9' } });
        fireEvent.change(screen.getByLabelText('Quantity used'), { target: { value: '2' } });
        fireEvent.click(screen.getByRole('button', { name: 'Record usage' }));
        await waitFor(() => expect(recordCareSessionMaterials).toHaveBeenCalledWith(123, 77, { work_item_id: 102, items: [{ material_id: 9, quantity: 2 }] }));
        await waitFor(() => expect(client.getQueryState(['inventory-stock']).isInvalidated).toBe(true));
    });

    it('links an existing patient image with the active visit and selected procedure', async () => {
        workspace();
        fireEvent.click(screen.getByTestId('tab-proc-102'));
        fireEvent.click(screen.getByTestId('workspace-images-btn'));
        expect(imageLinkQuery).toHaveBeenCalledWith(123, { care_session_id: 77 });
        fireEvent.change(screen.getByLabelText('Link Image to Session'), { target: { value: '55' } });
        fireEvent.click(screen.getByTestId('btn-submit-link-attachment'));
        await waitFor(() => expect(createLink).toHaveBeenCalledWith({ patientId: 123, data: expect.objectContaining({ attachment_id: 55, care_session_id: 77, work_item_id: 102 }) }));
    });
});
