import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import AddMaterialModal from './AddMaterialModal';

const inventoryApi = vi.hoisted(() => ({
    createMaterial: vi.fn(),
    updateMaterial: vi.fn(),
    getCategories: vi.fn(),
    createCategory: vi.fn(),
}));
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));

vi.mock('@/api/inventory', () => inventoryApi);
vi.mock('@/shared/ui', () => ({
    Modal: ({ isOpen, children }) => (isOpen ? <div>{children}</div> : null),
    toast,
}));
vi.mock('react-i18next', () => ({
    useTranslation: () => ({ t: (key) => key }),
}));

function renderModal() {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
        },
    });
    return render(
        <QueryClientProvider client={queryClient}>
            <AddMaterialModal isOpen onClose={vi.fn()} />
        </QueryClientProvider>
    );
}

describe('AddMaterialModal', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        const category = {
            id: 17,
            name_ar: 'حشو',
            name_en: 'Filling',
            default_type: 'DIVISIBLE',
            default_unit: 'g',
        };
        inventoryApi.getCategories
            .mockResolvedValueOnce({ data: [] })
            .mockResolvedValue({ data: [category] });
        inventoryApi.createCategory.mockResolvedValue({ data: category });
        inventoryApi.createMaterial.mockResolvedValue({ data: { id: 99 } });
    });

    it('selects a newly created category before submitting the material', async () => {
        renderModal();
        await waitFor(() => expect(inventoryApi.getCategories).toHaveBeenCalled());

        fireEvent.click(screen.getByText('inventory.actions.add_category'));
        fireEvent.change(screen.getByPlaceholderText('Name (Ar)'), { target: { value: 'حشو' } });
        fireEvent.change(screen.getByPlaceholderText('Name (En)'), { target: { value: 'Filling' } });
        fireEvent.click(screen.getByText('common.save'));

        await waitFor(() => expect(inventoryApi.createCategory).toHaveBeenCalledTimes(1));
        await waitFor(() => expect(screen.getAllByRole('combobox')[0].value).toBe('17'));

        fireEvent.click(screen.getByText('inventory.materials.save_new'));

        await waitFor(() => expect(inventoryApi.createMaterial).toHaveBeenCalledWith(
            expect.objectContaining({
                category_id: 17,
                name: 'حشو',
                type: 'DIVISIBLE',
                base_unit: 'g',
            })
        ));
    });
});
