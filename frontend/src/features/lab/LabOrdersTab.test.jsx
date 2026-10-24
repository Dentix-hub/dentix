import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LabOrdersTab from './LabOrdersTab';
import * as api from '@/api';

vi.mock('@/api', () => ({
    getPatientLabOrders: vi.fn(),
    getLaboratories: vi.fn(),
    getPatientTreatments: vi.fn(),
    createLabOrder: vi.fn(),
    updateLabOrder: vi.fn(),
    deleteLabOrder: vi.fn(),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
    }),
}));

const mockLabs = [
    { id: 1, name: 'Dental Art Lab' },
    { id: 2, name: 'Apex Ceramics' },
];

const mockTreatments = [
    { id: 42, procedure: 'Crown PFM', tooth_number: 16 },
    { id: 43, procedure: 'Composite Filling', tooth_number: 14 },
];

describe('LabOrdersTab (D2, D3, Step 6)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        api.getPatientLabOrders.mockResolvedValue({ data: [] });
        api.getLaboratories.mockResolvedValue({ data: mockLabs });
        api.getPatientTreatments.mockResolvedValue({ data: mockTreatments });
        api.createLabOrder.mockResolvedValue({ data: { id: 101 } });
    });

    it('displays treatment link dropdown in new lab order modal and auto-fills tooth and work_type', async () => {
        render(<LabOrdersTab patientId={12} treatments={mockTreatments} />);

        // Click Add Lab Order
        const addBtn = await screen.findByRole('button', { name: /add_empty|إضافة/i });
        fireEvent.click(addBtn);

        // Check treatment link select exists
        const treatmentSelect = await screen.findByLabelText(/ربط بإجراء علاجي/i);
        expect(treatmentSelect).toBeInTheDocument();
        expect(screen.getByText(/#42 — Crown PFM/i)).toBeInTheDocument();

        // Select Treatment #42
        fireEvent.change(treatmentSelect, { target: { value: '42' } });

        // Tooth number should be auto-filled to "16"
        const toothInput = screen.getByPlaceholderText(/tooth_placeholder/i);
        expect(toothInput.value).toBe('16');

        // Select laboratory
        const labSelect = screen.getAllByRole('combobox').find(select => select.required && select.value === '');
        fireEvent.change(labSelect, { target: { value: '1' } });

        // Save lab order
        const saveBtn = screen.getByRole('button', { name: /save_add/i });
        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(api.createLabOrder).toHaveBeenCalledTimes(1);
        });

        expect(api.createLabOrder).toHaveBeenCalledWith(expect.objectContaining({
            patient_id: 12,
            treatment_id: 42,
            laboratory_id: 1,
            tooth_number: '16',
            work_type: 'Crown PFM',
            price_to_patient: 0,
        }));
    });

    it('allows unlinked lab orders when treatment link is left empty', async () => {
        render(<LabOrdersTab patientId={12} treatments={mockTreatments} />);

        const addBtn = await screen.findByRole('button', { name: /add_empty|إضافة/i });
        fireEvent.click(addBtn);

        // Select laboratory and manual work type
        const labSelects = screen.getAllByRole('combobox');
        const labSelect = labSelects[1]; // second combobox is laboratory_id
        fireEvent.change(labSelect, { target: { value: '2' } });

        const workTypeSelect = labSelects[2]; // third combobox is work_type
        fireEvent.change(workTypeSelect, { target: { value: 'Crown' } });

        const toothInput = screen.getByPlaceholderText(/tooth_placeholder/i);
        fireEvent.change(toothInput, { target: { value: '21' } });

        const saveBtn = screen.getByRole('button', { name: /save_add/i });
        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(api.createLabOrder).toHaveBeenCalledTimes(1);
        });

        expect(api.createLabOrder).toHaveBeenCalledWith(expect.objectContaining({
            patient_id: 12,
            laboratory_id: 2,
            tooth_number: '21',
            work_type: 'Crown',
        }));
        expect(api.createLabOrder.mock.calls[0][0].treatment_id).toBeUndefined();
    });
});
