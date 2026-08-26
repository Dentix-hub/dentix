import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import FeatureManager from './FeatureManager';

const apiMocks = vi.hoisted(() => ({
    apiGet: vi.fn(),
    apiPut: vi.fn(),
    apiPost: vi.fn(),
}));

vi.mock('@/api', () => ({
    api: {
        get: apiMocks.apiGet,
        put: apiMocks.apiPut,
        post: apiMocks.apiPost,
    },
}));

vi.mock('@/utils/logger', () => ({ default: { error: vi.fn() } }));
vi.mock('@/shared/ui', () => ({
    toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar' },
    }),
}));

describe('FeatureManager flag wiring and optimistic updates', () => {
    const sampleFlags = [
        {
            id: 1,
            key: 'ai_diagnosis_assistant',
            description: 'AI diagnostic suggestions',
            is_global_enabled: false,
            rollout_percentage: 100,
        },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        apiMocks.apiGet.mockResolvedValue({ data: sampleFlags });
    });

    it('loads and renders feature flags from API', async () => {
        render(<FeatureManager tenants={[]} />);

        expect(await screen.findByText('ai_diagnosis_assistant')).toBeInTheDocument();
        expect(screen.getByText('AI diagnostic suggestions')).toBeInTheDocument();
    });

    it('clicking toggle updates UI optimistically and calls PUT endpoint with next status', async () => {
        apiMocks.apiPut.mockResolvedValue({
            data: { ...sampleFlags[0], is_global_enabled: true },
        });

        render(<FeatureManager tenants={[]} />);

        expect(await screen.findByText('ai_diagnosis_assistant')).toBeInTheDocument();
        const toggleButton = screen.getByText('super_admin.features.disabled').closest('button');

        fireEvent.click(toggleButton);

        // Optimistically changes to enabled
        expect(screen.getByText('super_admin.features.global_enabled')).toBeInTheDocument();

        await waitFor(() => {
            expect(apiMocks.apiPut).toHaveBeenCalledWith('/api/v1/admin/features/ai_diagnosis_assistant', {
                is_global_enabled: true,
            });
        });
    });

    it('rolls back state if API call fails', async () => {
        apiMocks.apiPut.mockRejectedValue(new Error('Network error'));

        render(<FeatureManager tenants={[]} />);

        expect(await screen.findByText('ai_diagnosis_assistant')).toBeInTheDocument();
        const toggleButton = screen.getByText('super_admin.features.disabled').closest('button');

        fireEvent.click(toggleButton);

        await waitFor(() => {
            expect(screen.getByText('super_admin.features.disabled')).toBeInTheDocument();
        });
    });
});
