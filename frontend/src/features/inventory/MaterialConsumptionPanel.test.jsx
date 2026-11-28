import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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
});
