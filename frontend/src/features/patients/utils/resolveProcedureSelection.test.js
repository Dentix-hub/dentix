import { describe, it, expect, vi, beforeEach } from 'vitest';
import { resolveProcedureSelection } from './resolveProcedureSelection';
import * as api from '@/api';

vi.mock('@/api', () => ({
    getProcedurePrices: vi.fn(),
}));

describe('resolveProcedureSelection Contract Tests (U1.3)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    const mockProcedures = [
        {
            id: 10,
            name: 'Composite Filling',
            price: 500,
            suggestedMaterials: [
                { id: 101, name: 'Composite Resin', quantity: 1, unit: 'tube' },
                { id: 102, name: 'Bonding Agent', quantity: 1, unit: 'drop' },
            ],
        },
        {
            id: 20,
            name: 'Simple Extraction',
            price: 200,
            suggestedMaterials: [],
        },
    ];

    it('1. returns base procedure price when no defaultPriceListId is provided', async () => {
        const result = await resolveProcedureSelection({
            procedureName: 'Composite Filling',
            procedures: mockProcedures,
            defaultPriceListId: null,
            currentPriceListId: null,
        });

        expect(result.found).toBe(true);
        expect(result.cost).toBe(500);
        expect(result.price_list_id).toBeNull();
        expect(api.getProcedurePrices).not.toHaveBeenCalled();
    });

    it('2. uses price list price when final_price > 0 and sets price_list_id', async () => {
        api.getProcedurePrices.mockResolvedValueOnce({
            data: {
                price_lists: [
                    { price_list_id: 'pl-VIP', final_price: 400 },
                    { price_list_id: 'pl-Standard', final_price: 450 },
                ],
            },
        });

        const result = await resolveProcedureSelection({
            procedureName: 'Composite Filling',
            procedures: mockProcedures,
            defaultPriceListId: 'pl-VIP',
            currentPriceListId: null,
        });

        expect(result.found).toBe(true);
        expect(result.cost).toBe(400);
        expect(result.price_list_id).toBe('pl-VIP');
        expect(api.getProcedurePrices).toHaveBeenCalledWith(10);
    });

    it('3. falls back to base procedure price when price list final_price is 0', async () => {
        api.getProcedurePrices.mockResolvedValueOnce({
            data: {
                price_lists: [
                    { price_list_id: 'pl-Zero', final_price: 0 },
                ],
            },
        });

        const result = await resolveProcedureSelection({
            procedureName: 'Composite Filling',
            procedures: mockProcedures,
            defaultPriceListId: 'pl-Zero',
            currentPriceListId: null,
        });

        expect(result.found).toBe(true);
        expect(result.cost).toBe(500);
        expect(result.price_list_id).toBeNull();
    });

    it('4. falls back to base procedure price on price list fetch error', async () => {
        api.getProcedurePrices.mockRejectedValueOnce(new Error('Network error'));

        const result = await resolveProcedureSelection({
            procedureName: 'Composite Filling',
            procedures: mockProcedures,
            defaultPriceListId: 'pl-Error',
            currentPriceListId: null,
        });

        expect(result.found).toBe(true);
        expect(result.cost).toBe(500);
        expect(result.price_list_id).toBeNull();
    });

    it('5. maps autoMaterials from suggestedMaterials correctly', async () => {
        const result = await resolveProcedureSelection({
            procedureName: 'Composite Filling',
            procedures: mockProcedures,
        });

        expect(result.autoMaterials).toEqual([
            {
                material_id: 101,
                name: 'Composite Resin',
                quantity: 1,
                unit: 'tube',
                is_manual: false,
            },
            {
                material_id: 102,
                name: 'Bonding Agent',
                quantity: 1,
                unit: 'drop',
                is_manual: false,
            },
        ]);
    });

    it('returns found: false when procedure is not found in the list', async () => {
        const result = await resolveProcedureSelection({
            procedureName: 'Non-existent procedure',
            procedures: mockProcedures,
            defaultPriceListId: 'pl-VIP',
        });

        expect(result.found).toBe(false);
        expect(result.cost).toBe(0);
        expect(result.autoMaterials).toEqual([]);
    });
});
