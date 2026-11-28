import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MaterialConsumptionPanel from './MaterialConsumptionPanel';

const mockGetSuggestedMaterials = vi.fn();

vi.mock('@/api/inventory', () => ({
    getSuggestedMaterials: (...args) => mockGetSuggestedMaterials(...args),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'ar' },
    }),
}));

describe('MaterialConsumptionPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('propagates resolved suggestions including category_id=null direct materials automatically without extra user clicks', async () => {
        mockGetSuggestedMaterials.mockResolvedValue({
            data: [
                {
                    category_id: null,
                    category_name_ar: 'حشو تجميلي',
                    material_type: 'DIVISIBLE',
                    base_unit: 'g',
                    weight: 1,
                    material_id: 42,
                    material_name: 'Composite Z350',
                    brand: '3M',
                    alternatives: [],
                    has_active_session: false,
                    session_id: null,
                    confidence: 0.85,
                    reason: 'مادة مرتبطة بالإجراء: Composite Z350',
                },
            ],
        });

        const onMaterialsChange = vi.fn();
        const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

        render(
            <QueryClientProvider client={queryClient}>
                <MaterialConsumptionPanel
                    procedureId={7}
                    doctorId={2}
                    onMaterialsChange={onMaterialsChange}
                />
            </QueryClientProvider>,
        );

        await waitFor(() => {
            expect(onMaterialsChange).toHaveBeenCalledWith([
                expect.objectContaining({
                    category_id: null,
                    material_id: 42,
                    material_name: 'Composite Z350',
                    weight: 1,
                    material_type: 'DIVISIBLE',
                }),
            ]);
        });
        expect(screen.getByText('حشو تجميلي')).toBeInTheDocument();
    });

    it('keeps distinct keys for multiple direct materials in the same category and increments quantity on category_id=null item', async () => {
        mockGetSuggestedMaterials.mockResolvedValue({
            data: [
                {
                    category_id: 5,
                    category_name_ar: 'تخدير',
                    material_type: 'NON_DIVISIBLE',
                    base_unit: 'carpule',
                    weight: 1,
                    material_id: 101,
                    material_name: 'Articaine 4%',
                    is_direct_material: true,
                    alternatives: [],
                    has_active_session: false,
                    session_id: null,
                    confidence: 0.85,
                    reason: 'مادة مرتبطة بالإجراء: Articaine 4%',
                },
                {
                    category_id: 5,
                    category_name_ar: 'تخدير',
                    material_type: 'NON_DIVISIBLE',
                    base_unit: 'piece',
                    weight: 1,
                    material_id: 102,
                    material_name: 'Needle Short',
                    is_direct_material: true,
                    alternatives: [],
                    has_active_session: false,
                    session_id: null,
                    confidence: 0.85,
                    reason: 'مادة مرتبطة بالإجراء: Needle Short',
                },
                {
                    category_id: null,
                    category_name_ar: 'مادة إضافية',
                    material_type: 'NON_DIVISIBLE',
                    base_unit: 'unit',
                    weight: 1,
                    material_id: 103,
                    material_name: 'Matrix Band',
                    is_direct_material: true,
                    alternatives: [],
                    has_active_session: false,
                    session_id: null,
                    confidence: 0.85,
                    reason: 'مادة مرتبطة بالإجراء: Matrix Band',
                },
            ],
        });

        const onMaterialsChange = vi.fn();
        const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

        const { container } = render(
            <QueryClientProvider client={queryClient}>
                <MaterialConsumptionPanel
                    procedureId={9}
                    doctorId={2}
                    onMaterialsChange={onMaterialsChange}
                />
            </QueryClientProvider>,
        );

        await waitFor(() => {
            expect(onMaterialsChange).toHaveBeenCalled();
            const lastCall = onMaterialsChange.mock.calls.at(-1)[0];
            expect(lastCall.map((m) => m.material_id)).toEqual([101, 102, 103]);
        });

        expect(screen.getByText('Articaine 4%')).toBeInTheDocument();
        expect(screen.getByText('Needle Short')).toBeInTheDocument();
        expect(screen.getByText('Matrix Band')).toBeInTheDocument();

        const incrementButtons = container.querySelectorAll('button .lucide-plus');
        expect(incrementButtons.length).toBe(3);
        fireEvent.click(incrementButtons[2].closest('button'));

        await waitFor(() => {
            const lastCall = onMaterialsChange.mock.calls.at(-1)[0];
            const matrixBand = lastCall.find((m) => m.material_id === 103);
            expect(matrixBand?.quantity).toBe(2);
            expect(matrixBand?.source).toBe('panel');
        });
    });
});
