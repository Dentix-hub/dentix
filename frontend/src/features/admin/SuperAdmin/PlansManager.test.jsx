import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PlansManager from './PlansManager';
import { parseFeatures, serializeFeatures } from './planFeatureUtils';
import { createSubscriptionPlan, deleteSubscriptionPlan } from '@/api';
import { toast } from '@/shared/ui';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, options) => {
            if (options?.name) return `${key} ${options.name}`;
            return key;
        },
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/api', () => ({
    createSubscriptionPlan: vi.fn(),
    deleteSubscriptionPlan: vi.fn(),
    api: {
        delete: vi.fn(),
    },
}));

vi.mock('@/shared/ui', async () => {
    const actual = await vi.importActual('@/shared/ui');
    return {
        ...actual,
        toast: {
            success: vi.fn(),
            error: vi.fn(),
        },
    };
});

describe('PlansManager MS-14 (features, creation, validation, AI limits, and deletion)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

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

    it('validates required fields on plan creation', async () => {
        render(
            <PlansManager
                plans={[]}
                editingPlan={null}
                setEditingPlan={vi.fn()}
                editedPlanData={{}}
                setEditedPlanData={vi.fn()}
                handleSavePlan={vi.fn()}
            />
        );

        // Open create card
        fireEvent.click(screen.getByText('super_admin.plans.add_plan'));

        // Submit without filling fields
        fireEvent.click(screen.getByText('super_admin.plans.create_button'));

        expect(toast.error).toHaveBeenCalledWith('super_admin.plans.error_missing_code');
        expect(createSubscriptionPlan).not.toHaveBeenCalled();
    });

    it('submits valid plan creation with sanitized numbers and AI fields', async () => {
        createSubscriptionPlan.mockResolvedValueOnce({ data: { success: true } });
        const onRefresh = vi.fn();

        render(
            <PlansManager
                plans={[]}
                editingPlan={null}
                setEditingPlan={vi.fn()}
                editedPlanData={{}}
                setEditedPlanData={vi.fn()}
                handleSavePlan={vi.fn()}
                onRefresh={onRefresh}
            />
        );

        fireEvent.click(screen.getByText('super_admin.plans.add_plan'));

        const codeInput = screen.getByLabelText('super_admin.plans.plan_id_label');
        const nameInput = screen.getByLabelText('super_admin.plans.plan_name_label');
        const priceInput = screen.getByLabelText((content) => content.includes('super_admin.plans.price_label'));
        const durationInput = screen.getByLabelText('super_admin.plans.duration_label');

        fireEvent.change(codeInput, { target: { value: 'enterprise_plan' } });
        fireEvent.change(nameInput, { target: { value: 'باقة الشركات' } });
        fireEvent.change(priceInput, { target: { value: '5000' } });
        fireEvent.change(durationInput, { target: { value: '365' } });

        fireEvent.click(screen.getByText('super_admin.plans.create_button'));

        await waitFor(() => {
            expect(createSubscriptionPlan).toHaveBeenCalledWith(expect.objectContaining({
                name: 'enterprise_plan',
                display_name_ar: 'باقة الشركات',
                price: 5000,
                duration_days: 365,
                is_ai_enabled: false,
                is_default: false,
            }));
            expect(toast.success).toHaveBeenCalledWith('super_admin.plans.create_success');
            expect(onRefresh).toHaveBeenCalled();
        });
    });

    it('confirms plan deletion using ConfirmDialog and invokes deleteSubscriptionPlan', async () => {
        deleteSubscriptionPlan.mockResolvedValueOnce({ data: { success: true } });
        const onRefresh = vi.fn();
        const mockPlans = [
            {
                id: 42,
                name: 'basic_plan',
                display_name_ar: 'الخطة البسيطة',
                price: 50,
                duration_days: 30,
                features: '[]',
            },
        ];

        render(
            <PlansManager
                plans={mockPlans}
                editingPlan={null}
                setEditingPlan={vi.fn()}
                editedPlanData={{}}
                setEditedPlanData={vi.fn()}
                handleSavePlan={vi.fn()}
                onRefresh={onRefresh}
            />
        );

        // Click delete button
        const deleteBtn = screen.getByLabelText('super_admin.plans.delete_plan');
        fireEvent.click(deleteBtn);

        // Confirm dialog should be open
        expect(screen.getByText('super_admin.plans.delete_title')).toBeInTheDocument();

        // Confirm
        const confirmBtn = screen.getByRole('button', { name: 'common.delete' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(deleteSubscriptionPlan).toHaveBeenCalledWith(42);
            expect(toast.success).toHaveBeenCalledWith('super_admin.plans.delete_success');
            expect(onRefresh).toHaveBeenCalled();
        });
    });
});
