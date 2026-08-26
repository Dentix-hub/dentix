import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import PlansManager from './PlansManager';
import { parseFeatures, serializeFeatures } from './planFeatureUtils';


vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/api', () => ({
    createSubscriptionPlan: vi.fn(),
    api: {
        delete: vi.fn(),
    },
}));

vi.mock('@/shared/ui', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

describe('PlansManager features serialization & parser', () => {
    it('parses JSON array format correctly', () => {
        const raw = JSON.stringify(['ai_insights', 'multi_branch', 'custom_addon']);
        const parsed = parseFeatures(raw);
        expect(parsed.keys).toEqual(['ai_insights', 'multi_branch']);
        expect(parsed.custom).toBe('custom_addon');
    });

    it('parses comma-delimited strings without losing custom tags', () => {
        const raw = 'ai_insights, custom_support, telehealth';
        const parsed = parseFeatures(raw);
        expect(parsed.keys).toEqual(['ai_insights', 'telehealth']);
        expect(parsed.custom).toBe('custom_support');
    });

    it('serializes feature keys and custom notes together', () => {
        const serialized = serializeFeatures(['ai_insights', 'export_reports'], 'custom_1, custom_2');
        const list = JSON.parse(serialized);
        expect(list).toContain('ai_insights');
        expect(list).toContain('export_reports');
        expect(list).toContain('custom_1');
        expect(list).toContain('custom_2');
    });

    it('renders plans with features and toggles edit checklist', async () => {
        const mockPlans = [
            {
                id: 1,
                name: 'pro_plan',
                display_name_ar: 'الخطة الاحترافية',
                price: 100,
                duration_days: 30,
                max_users: 5,
                max_patients: 100,
                features: JSON.stringify(['ai_insights', 'patient_portal']),
                is_ai_enabled: true,
                ai_daily_limit: 50,
                is_default: true,
            },
        ];

        const setEditingPlan = vi.fn();
        const setEditedPlanData = vi.fn();
        const handleSavePlan = vi.fn();

        const { rerender } = render(
            <PlansManager
                plans={mockPlans}
                editingPlan={null}
                setEditingPlan={setEditingPlan}
                editedPlanData={{}}
                setEditedPlanData={setEditedPlanData}
                handleSavePlan={handleSavePlan}
            />
        );

        expect(screen.getByText('الخطة الاحترافية')).toBeInTheDocument();
        expect(screen.getByText('تحليلات ومساعد الذكاء الاصطناعي')).toBeInTheDocument();

        // Switch to editing plan 1
        rerender(
            <PlansManager
                plans={mockPlans}
                editingPlan={1}
                setEditingPlan={setEditingPlan}
                editedPlanData={{ features: JSON.stringify(['ai_insights', 'patient_portal']) }}
                setEditedPlanData={setEditedPlanData}
                handleSavePlan={handleSavePlan}
            />
        );

        // Feature checklist should be visible in edit mode
        expect(screen.getByText('إدارة الفروع المتعددة')).toBeInTheDocument();
    });
});
