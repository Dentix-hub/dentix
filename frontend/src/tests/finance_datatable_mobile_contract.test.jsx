import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import DataTable from '../features/finance/components/DataTable';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
    }),
}));

describe('Finance DataTable mobile contract', () => {
    it('uses the same cell(item, meta) signature on desktop and mobile', () => {
        const cell = vi.fn((item, meta) => (
            <span data-testid={`cell-${meta.isMobile ? 'mobile' : 'desktop'}`}>
                {item.patientName}
            </span>
        ));
        const column = {
            id: 'patient',
            header: 'المريض',
            accessor: 'patientName',
            cell,
        };
        const item = { id: 7, patientName: 'أحمد محمود' };

        render(
            <DataTable
                columns={[column]}
                data={[item]}
                totalItems={1}
            />
        );

        expect(screen.getByTestId('cell-desktop')).toBeDefined();
        expect(screen.getByTestId('cell-mobile')).toBeDefined();
        expect(cell).toHaveBeenCalledTimes(2);

        const [desktopItem, desktopMeta] = cell.mock.calls[0];
        const [mobileItem, mobileMeta] = cell.mock.calls[1];

        expect(desktopItem).toBe(item);
        expect(mobileItem).toBe(item);
        expect(desktopMeta).toMatchObject({
            row: item,
            value: 'أحمد محمود',
            index: 0,
            column,
            isMobile: false,
        });
        expect(mobileMeta).toMatchObject({
            row: item,
            value: 'أحمد محمود',
            index: 0,
            column,
            isMobile: true,
        });
    });

    it('marks default mobile cards as a semantic list and isolates mixed-direction values', () => {
        const { container } = render(
            <DataTable
                columns={[
                    { id: 'label', header: 'المرجع', accessor: 'label' },
                ]}
                data={[{ id: 1, label: 'INV-1024 / أحمد' }]}
                totalItems={1}
            />
        );

        expect(container.querySelector('[role="list"]')).toBeDefined();
        expect(container.querySelector('[role="listitem"]')).toBeDefined();
        expect(screen.getAllByText('INV-1024 / أحمد').some((node) => node.getAttribute('dir') === 'auto')).toBe(true);
    });

    it('announces loading, empty, and error states to assistive technology', () => {
        const { rerender } = render(<DataTable isLoading />);
        expect(screen.getByRole('status')).toBeDefined();

        rerender(<DataTable data={[]} emptyMessage="لا توجد بيانات" />);
        expect(screen.getByRole('status')).toHaveTextContent('لا توجد بيانات');

        rerender(<DataTable data={[]} isError errorMessage="تعذر التحميل" />);
        expect(screen.getByRole('alert')).toHaveTextContent('تعذر التحميل');
    });
});
