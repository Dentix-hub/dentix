import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';

import { formatMoney, getCurrencySymbol } from '../features/finance/utils/currencyFormatter';
import { getPresetDates, formatRangeLabel, DATE_PRESETS } from '../features/finance/utils/datePresets';
import { financeKeys } from '../features/finance/queryKeys';
import Money from '../features/finance/components/Money';
import ScopeBadge from '../features/finance/components/ScopeBadge';
import MetricCard from '../features/finance/components/MetricCard';
import FilterBar from '../features/finance/components/FilterBar';
import DataTable from '../features/finance/components/DataTable';

// Mock react-i18next
vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'ar' },
    }),
}));

describe('Finance V2 Foundation Utilities', () => {
    describe('formatMoney & getCurrencySymbol', () => {
        it('formats positive and negative amounts correctly', () => {
            const formattedPos = formatMoney(1500, { currency: 'EGP', locale: 'en-US' });
            expect(formattedPos).toContain('1,500');
            expect(formattedPos).toContain('EGP');

            const formattedNeg = formatMoney(-250.5, { currency: 'EGP', locale: 'en-US' });
            expect(formattedNeg).toContain('-250.5');
        });

        it('handles compact notation', () => {
            const formatted = formatMoney(15000, { currency: 'EGP', locale: 'en-US', compact: true });
            expect(formatted).toContain('15K');
        });

        it('handles zero and invalid amounts gracefully', () => {
            expect(formatMoney(0, { currency: 'EGP', locale: 'en-US' })).toContain('0');
            expect(formatMoney(null, { currency: 'EGP', locale: 'en-US' })).toContain('0');
            expect(formatMoney(undefined, { currency: 'EGP', locale: 'en-US' })).toContain('0');
        });

        it('returns proper currency symbols', () => {
            expect(getCurrencySymbol('EGP')).toBe('ج.م');
            expect(getCurrencySymbol('USD')).toBe('$');
            expect(getCurrencySymbol('SAR')).toBe('ر.س');
        });
    });

    describe('datePresets', () => {
        it('defines standard preset IDs', () => {
            const ids = DATE_PRESETS.map((p) => p.id);
            expect(ids).toContain('today');
            expect(ids).toContain('yesterday');
            expect(ids).toContain('this_week');
            expect(ids).toContain('this_month');
            expect(ids).toContain('last_month');
            expect(ids).toContain('custom');
        });

        it('calculates valid date strings for all presets', () => {
            const todayDates = getPresetDates('today');
            expect(todayDates.from).toMatch(/^\d{4}-\d{2}-\d{2}$/);
            expect(todayDates.to).toBe(todayDates.from);

            const thisMonth = getPresetDates('this_month');
            expect(thisMonth.from.endsWith('-01')).toBe(true);

            const lastMonth = getPresetDates('last_month');
            expect(lastMonth.from.endsWith('-01')).toBe(true);
        });

        it('formats range labels in Arabic and English', () => {
            const labelAr = formatRangeLabel('2026-08-01', '2026-08-15', 'ar');
            expect(labelAr.length).toBeGreaterThan(0);

            const labelEn = formatRangeLabel('2026-08-01', '2026-08-15', 'en');
            expect(labelEn).toContain('–');
        });
    });

    describe('queryKeys factory', () => {
        it('builds structured and distinct query keys', () => {
            const overviewKey = financeKeys.overview({ from: '2026-08-01', to: '2026-08-15' });
            expect(overviewKey).toEqual(['finance', 'overview', { from: '2026-08-01', to: '2026-08-15' }]);

            const docDetailKey = financeKeys.doctorDetail(5, { month: '2026-08' });
            expect(docDetailKey).toEqual(['finance', 'compensation', 'doctors', 5, { month: '2026-08' }]);

            const payrollKey = financeKeys.payroll('2026-08');
            expect(payrollKey).toEqual(['finance', 'compensation', 'payroll', '2026-08']);
        });
    });
});

describe('Finance V2 Shared UI Primitives', () => {
    describe('<Money />', () => {
        it('renders with correct text and ltr direction', () => {
            const { container } = render(<Money amount={2500} currency="EGP" />);
            const span = container.querySelector('span');
            expect(span).toBeDefined();
            expect(span.getAttribute('dir')).toBe('ltr');
            expect(span.getAttribute('aria-label')).toBe('2500 EGP');
            expect(span.textContent).toContain('EGP');
        });

        it('applies colored styling when requested', () => {
            const { container: posContainer } = render(<Money amount={100} colored />);
            expect(posContainer.querySelector('span').className).toContain('text-emerald');

            const { container: negContainer } = render(<Money amount={-100} colored />);
            expect(negContainer.querySelector('span').className).toContain('text-rose');
        });
    });

    describe('<ScopeBadge />', () => {
        it('renders period scope correctly', () => {
            render(<ScopeBadge scope="period" label="الفترة المحددة" />);
            expect(screen.getByText('الفترة المحددة')).toBeDefined();
        });

        it('renders all-time scope with amber badge', () => {
            const { container } = render(<ScopeBadge scope="all_time" label="الرصيد التراكمي" />);
            expect(screen.getByText('الرصيد التراكمي')).toBeDefined();
            expect(container.querySelector('span').className).toContain('text-amber');
        });
    });

    describe('<MetricCard />', () => {
        it('renders metric title, amount, and scope', () => {
            render(
                <MetricCard
                    title="التحصيلات النقدية"
                    amount={75000}
                    currency="EGP"
                    scope="period"
                    scopeLabel="أغسطس 2026"
                />
            );

            expect(screen.getByText('التحصيلات النقدية')).toBeDefined();
            expect(screen.getByText('أغسطس 2026')).toBeDefined();
            expect(screen.getByLabelText('75000 EGP')).toBeDefined();
        });

        it('renders loading skeleton when isLoading is true', () => {
            const { container } = render(<MetricCard title="إجمالي الإنتاج" isLoading />);
            expect(container.querySelector('.animate-pulse')).toBeDefined();
        });

        it('renders clickable link if to prop is passed', () => {
            render(
                <MemoryRouter>
                    <MetricCard
                        title="المصروفات"
                        amount={12000}
                        to="/finance/expenses"
                    />
                </MemoryRouter>
            );

            const link = screen.getByRole('link');
            expect(link.getAttribute('href')).toBe('/finance/expenses');
        });
    });

    describe('<FilterBar />', () => {
        it('renders labeled search/filter controls and accessible removal actions', () => {
            const onSearchMock = vi.fn();
            const onFilterMock = vi.fn();
            const onResetMock = vi.fn();

            render(
                <MemoryRouter>
                    <FilterBar
                        searchValue="أحمد"
                        onSearchChange={onSearchMock}
                        filters={[
                            {
                                id: 'status',
                                label: 'الحالة',
                                value: 'paid',
                                options: [
                                    { value: 'all', label: 'الكل' },
                                    { value: 'paid', label: 'مسدد' },
                                ],
                                onChange: onFilterMock,
                            },
                        ]}
                        onReset={onResetMock}
                    />
                </MemoryRouter>
            );

            expect(screen.getByRole('textbox', { name: 'بحث...' })).toBeDefined();
            expect(screen.getByRole('combobox', { name: 'الحالة' })).toBeDefined();
            expect(screen.getByText('الحالة: مسدد')).toBeDefined();
            expect(screen.getByRole('button', { name: 'إزالة فلتر البحث' })).toBeDefined();
            expect(screen.getByRole('button', { name: 'إزالة الفلتر الحالة: مسدد' })).toBeDefined();

            const resetBtn = screen.getByText('إعادة ضبط');
            fireEvent.click(resetBtn);
            expect(onResetMock).toHaveBeenCalledTimes(1);
        });
    });

    describe('<DataTable />', () => {
        const columns = [
            { id: 'id', header: 'المعرف', accessor: 'id', sortable: true },
            { id: 'patient', header: 'المريض', accessor: 'patientName' },
            { id: 'amount', header: 'المبلغ', accessor: 'amount', align: 'end' },
        ];

        const sampleData = [
            { id: 1, patientName: 'أحمد محمود', amount: '500 EGP' },
            { id: 2, patientName: 'سارة خالد', amount: '1,200 EGP' },
        ];

        it('renders table headers and rows correctly', () => {
            render(
                <DataTable
                    columns={columns}
                    data={sampleData}
                    page={1}
                    pageSize={10}
                    totalItems={2}
                />
            );

            expect(screen.getAllByText('المعرف').length).toBeGreaterThan(0);
            expect(screen.getAllByText('المريض').length).toBeGreaterThan(0);
            expect(screen.getAllByText('أحمد محمود').length).toBeGreaterThan(0);
            expect(screen.getAllByText('سارة خالد').length).toBeGreaterThan(0);
        });

        it('exposes sorting as a keyboard-accessible button with aria-sort state', () => {
            const onSortMock = vi.fn();
            render(
                <DataTable
                    columns={columns}
                    data={sampleData}
                    sortBy="id"
                    sortDirection="desc"
                    onSort={onSortMock}
                />
            );

            const sortButton = screen.getByRole('button', { name: 'المعرف' });
            expect(sortButton.getAttribute('type')).toBe('button');
            expect(sortButton.closest('th').getAttribute('aria-sort')).toBe('descending');
            fireEvent.click(sortButton);
            expect(onSortMock).toHaveBeenCalledWith('id', 'asc');
        });

        it('renders empty message when data is empty', () => {
            render(
                <DataTable
                    columns={columns}
                    data={[]}
                    emptyMessage="لا توجد سجلات مالية"
                />
            );

            expect(screen.getByText('لا توجد سجلات مالية')).toBeDefined();
        });

        it('renders error state and handles retry', () => {
            const onRetryMock = vi.fn();
            render(
                <DataTable
                    columns={columns}
                    data={[]}
                    isError
                    errorMessage="فشل الاتصال بالخادم"
                    onRetry={onRetryMock}
                />
            );

            expect(screen.getByText('فشل الاتصال بالخادم')).toBeDefined();
            const retryBtn = screen.getByText('إعادة المحاولة');
            fireEvent.click(retryBtn);
            expect(onRetryMock).toHaveBeenCalledTimes(1);
        });
    });
});
