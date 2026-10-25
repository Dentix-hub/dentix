import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import OnboardingChecklistWidget from './OnboardingChecklistWidget';
import * as useOnboardingModule from '../hooks/useOnboarding';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
    useNavigate: () => mockNavigate,
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => fallback || key,
        i18n: { language: 'ar' },
    }),
}));

describe('OnboardingChecklistWidget component', () => {
    const mockDismiss = vi.fn();
    const mockRestore = vi.fn();

    const sampleStatus = {
        enabled: true,
        role: 'admin',
        dismissed: false,
        seen_tips: [],
        progress: {
            total: 5,
            completed: 2,
            percentage: 40,
        },
        sections: [
            {
                id: 'manager',
                title: 'إعداد العيادة',
                steps: [
                    {
                        id: 'm1_clinic_data',
                        key: 'M1',
                        title: 'بيانات العيادة',
                        description: 'أدخل عنوان العيادة أو رقم الهاتف للتواصل',
                        link: '/settings?tab=general',
                        done: true,
                        highlight: false,
                    },
                    {
                        id: 'm2_procedures',
                        key: 'M2',
                        title: 'قائمة الإجراءات والخدمات',
                        description: 'حدد الاسم والسعر والشكل واللون لكل إجراء لتسهيل العمل على المخطط',
                        link: '/settings?tab=services',
                        done: false,
                        highlight: true,
                    },
                ],
            },
            {
                id: 'doctor',
                title: 'العمل السريري والمخطط',
                steps: [
                    {
                        id: 'd5_lab_tour',
                        key: 'D5',
                        title: 'جولة المعامل والتركيبات',
                        description: 'أضف معملاً، أنشئ طلب تركيبة، وسجل استلامها من المعمل',
                        link: '/labs',
                        done: false,
                        highlight: false,
                        sub_steps: [
                            { key: 'lab_added', title: 'إضافة معمل', done: true },
                            { key: 'order_created', title: 'إنشاء طلب عمل', done: false },
                            { key: 'order_received', title: 'استلام الطلب من المعمل', done: false },
                        ],
                    },
                ],
            },
        ],
        steps: [
            {
                id: 'm1_clinic_data',
                key: 'M1',
                title: 'بيانات العيادة',
                description: 'أدخل عنوان العيادة أو رقم الهاتف للتواصل',
                link: '/settings?tab=general',
                done: true,
                highlight: false,
            },
            {
                id: 'm2_procedures',
                key: 'M2',
                title: 'قائمة الإجراءات والخدمات',
                description: 'حدد الاسم والسعر والشكل واللون لكل إجراء لتسهيل العمل على المخطط',
                link: '/settings?tab=services',
                done: false,
                highlight: true,
            },
            {
                id: 'd5_lab_tour',
                key: 'D5',
                title: 'جولة المعامل والتركيبات',
                description: 'أضف معملاً، أنشئ طلب تركيبة، وسجل استلامها من المعمل',
                link: '/labs',
                done: false,
                highlight: false,
                sub_steps: [
                    { key: 'lab_added', title: 'إضافة معمل', done: true },
                    { key: 'order_created', title: 'إنشاء طلب عمل', done: false },
                    { key: 'order_received', title: 'استلام الطلب من المعمل', done: false },
                ],
            },
        ],
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders nothing when onboarding is disabled', () => {
        vi.spyOn(useOnboardingModule, 'useOnboarding').mockReturnValue({
            status: { enabled: false },
            isLoading: false,
            dismiss: mockDismiss,
            restore: mockRestore,
        });

        const { container } = render(<OnboardingChecklistWidget />);
        expect(container.firstChild).toBeNull();
    });

    it('renders checklist widget with progress and steps when enabled', () => {
        vi.spyOn(useOnboardingModule, 'useOnboarding').mockReturnValue({
            status: sampleStatus,
            isLoading: false,
            dismiss: mockDismiss,
            restore: mockRestore,
        });

        render(<OnboardingChecklistWidget />);

        // Progress bar percentage
        expect(screen.getByText('40%')).toBeInTheDocument();
        expect(screen.getByText('بيانات العيادة')).toBeInTheDocument();
        expect(screen.getByText('قائمة الإجراءات والخدمات')).toBeInTheDocument();

        // M2 highlighted badge
        expect(screen.getByText('مهم للمخطط')).toBeInTheDocument();

        // D5 sub-steps
        expect(screen.getByText(/1\. إضافة معمل/i)).toBeInTheDocument();
        expect(screen.getByText(/2\. إنشاء طلب عمل/i)).toBeInTheDocument();
        expect(screen.getByText(/3\. استلام الطلب من المعمل/i)).toBeInTheDocument();
    });

    it('navigates when action button is clicked', () => {
        vi.spyOn(useOnboardingModule, 'useOnboarding').mockReturnValue({
            status: sampleStatus,
            isLoading: false,
            dismiss: mockDismiss,
            restore: mockRestore,
        });

        render(<OnboardingChecklistWidget />);

        const navButtons = screen.getAllByRole('button', { name: /الانتقال للخطوة/i });
        fireEvent.click(navButtons[0]);
        expect(mockNavigate).toHaveBeenCalledWith('/settings?tab=services');
    });

    it('calls dismiss when X button is clicked', () => {
        vi.spyOn(useOnboardingModule, 'useOnboarding').mockReturnValue({
            status: sampleStatus,
            isLoading: false,
            dismiss: mockDismiss,
            restore: mockRestore,
        });

        render(<OnboardingChecklistWidget />);

        const dismissBtn = screen.getByRole('button', { name: /إخفاء القائمة/i });
        fireEvent.click(dismissBtn);
        expect(mockDismiss).toHaveBeenCalledWith(true);
    });

    it('renders restore notice when dismissed is true and allows restore', () => {
        vi.spyOn(useOnboardingModule, 'useOnboarding').mockReturnValue({
            status: { ...sampleStatus, dismissed: true },
            isLoading: false,
            dismiss: mockDismiss,
            restore: mockRestore,
        });

        render(<OnboardingChecklistWidget />);

        expect(screen.getByText(/قائمة البداية السريعة مخفية/i)).toBeInTheDocument();
        const restoreBtn = screen.getByRole('button', { name: /إظهار الدليل/i });
        fireEvent.click(restoreBtn);
        expect(mockRestore).toHaveBeenCalled();
    });
});
