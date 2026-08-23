import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import HeadlineMetrics from '../features/finance/overview/components/HeadlineMetrics';
import ObligationsSection from '../features/finance/overview/components/ObligationsSection';
import FinancialTrendChart from '../features/finance/overview/components/FinancialTrendChart';
import RecentActivityPreview from '../features/finance/overview/components/RecentActivityPreview';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'ar' },
    }),
}));

describe('Finance Overview V2 Components', () => {
    describe('<HeadlineMetrics />', () => {
        it('renders all 4 headline metric cards with correct scopes', () => {
            render(
                <MemoryRouter>
                    <HeadlineMetrics
                        netInvoiced={120000}
                        collected={95000}
                        totalDeductions={40000}
                        netResult={55000}
                        dateLabel="أغسطس 2026"
                    />
                </MemoryRouter>
            );

            expect(screen.getByText('صافي الإيراد المحتسب')).toBeDefined();
            expect(screen.getByText('التحصيلات النقدية')).toBeDefined();
            expect(screen.getByText('إجمالي الاستقطاعات')).toBeDefined();
            expect(screen.getByText('صافي النتيجة التشغيلية')).toBeDefined();
            expect(screen.getByLabelText('120000 EGP')).toBeDefined();
            expect(screen.getByLabelText('95000 EGP')).toBeDefined();
            expect(screen.getByLabelText('40000 EGP')).toBeDefined();
            expect(screen.getByLabelText('55000 EGP')).toBeDefined();
        });

        it('renders loading skeleton when isLoading is true', () => {
            const { container } = render(
                <MemoryRouter>
                    <HeadlineMetrics isLoading />
                </MemoryRouter>
            );
            expect(container.querySelectorAll('.animate-pulse').length).toBe(4);
        });

        it('shows aggregated overview amounts as whole EGP without changing source values', () => {
            render(
                <MemoryRouter>
                    <HeadlineMetrics
                        netInvoiced={32500}
                        collected={23900}
                        totalDeductions={4369.35}
                        netResult={19530.65}
                    />
                </MemoryRouter>
            );

            expect(screen.getByLabelText('4369 EGP')).toBeDefined();
            expect(screen.getByLabelText('19531 EGP')).toBeDefined();
            expect(screen.queryByLabelText('4369.35 EGP')).toBeNull();
        });
    });

    describe('<ObligationsSection />', () => {
        it('renders patient debt, doctor dues, and staff payroll with canonical destination links', () => {
            render(
                <MemoryRouter>
                    <ObligationsSection
                        allTimeOutstanding={65000}
                        doctorDuesTotal={18000}
                        staffDuesTotal={12000}
                        dateLabel="أغسطس 2026"
                    />
                </MemoryRouter>
            );

            expect(screen.getByText('مستحقات المرضى (الديون التراكمية)')).toBeDefined();
            expect(screen.getByText('مستحقات الأطباء غير المسددة')).toBeDefined();
            expect(screen.getByText('التزامات رواتب الموظفين')).toBeDefined();
            expect(screen.getByLabelText('65000 EGP')).toBeDefined();
            expect(screen.getByLabelText('18000 EGP')).toBeDefined();
            expect(screen.getByLabelText('12000 EGP')).toBeDefined();

            const links = screen.getAllByRole('link');
            expect(links.some((l) => l.getAttribute('href') === '/finance/patient-accounts')).toBe(true);
            expect(links.some((l) => l.getAttribute('href') === '/finance/team/doctors')).toBe(true);
            expect(links.some((l) => l.getAttribute('href') === '/finance/team/payroll')).toBe(true);
        });

        it('shows prorated obligation totals as whole EGP in the overview', () => {
            render(
                <MemoryRouter>
                    <ObligationsSection staffDuesTotal={1419.35} />
                </MemoryRouter>
            );

            expect(screen.getByLabelText('1419 EGP')).toBeDefined();
            expect(screen.queryByLabelText('1419.35 EGP')).toBeNull();
        });
    });

    describe('<FinancialTrendChart />', () => {
        it('renders empty state when timeline data is empty', () => {
            render(<FinancialTrendChart timeline={[]} />);
            expect(screen.getByText('لا توجد حركات مالية مسجلة خلال هذه الفترة')).toBeDefined();
        });

        it('renders title and legend when timeline data is provided', () => {
            const timeline = [
                { date: '2026-08-01', revenue: 5000, expenses: 2000, net_profit: 3000 },
                { date: '2026-08-02', revenue: 8000, expenses: 3500, net_profit: 4500 },
            ];

            render(<FinancialTrendChart timeline={timeline} />);
            expect(screen.getAllByText('حركة التدفق المالي (التحصيلات مقابل المصروفات)').length).toBeGreaterThan(0);
        });
    });

    describe('<RecentActivityPreview />', () => {
        it('renders recent payments and expenses with canonical drill-down link', () => {
            const sampleActivities = [
                {
                    id: 'pay-1',
                    type: 'payment',
                    dateStr: '2026-08-15',
                    title: 'أحمد محمود',
                    subtitle: 'دفعة جلسة حشو',
                    amount: 800,
                    isIncome: true,
                    to: '/finance/cash-movements/payments',
                },
                {
                    id: 'exp-1',
                    type: 'expense',
                    dateStr: '2026-08-14',
                    title: 'فاتورة كهرباء',
                    subtitle: 'مصروف تشغيلي',
                    amount: 1500,
                    isIncome: false,
                    to: '/finance/cash-movements/expenses',
                },
            ];

            render(
                <MemoryRouter>
                    <RecentActivityPreview activities={sampleActivities} />
                </MemoryRouter>
            );

            expect(screen.getByText('أحمد محمود')).toBeDefined();
            expect(screen.getByText('فاتورة كهرباء')).toBeDefined();
            expect(screen.getByLabelText('800 EGP')).toBeDefined();
            expect(screen.getByLabelText('1500 EGP')).toBeDefined();
            expect(screen.getByText('عرض الكل').closest('a').getAttribute('href')).toBe('/finance/cash-movements/activity');
        });

        it('renders empty message when no activities are present', () => {
            render(
                <MemoryRouter>
                    <RecentActivityPreview activities={[]} />
                </MemoryRouter>
            );
            expect(screen.getByText('لا توجد معاملات مسجلة مؤخراً')).toBeDefined();
        });
    });
});
