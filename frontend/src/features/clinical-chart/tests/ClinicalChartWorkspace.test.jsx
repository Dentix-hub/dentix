import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ClinicalChartWorkspace from '../ClinicalChartWorkspace';

describe('ClinicalChartWorkspace scaffold', () => {
    it('renders two isolated read-only Dentix charts', () => {
        const { container } = render(<ClinicalChartWorkspace />);

        expect(screen.getByTestId('clinical-chart-workspace')).toBeInTheDocument();
        expect(screen.getAllByTestId('clinical-chart-instance')).toHaveLength(2);
        expect(screen.getByRole('heading', { name: 'المخطط الحالي' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'المخطط السابق' })).toBeInTheDocument();
        expect(container.querySelectorAll('[data-interaction-mode="read-only"]')).toHaveLength(2);
        expect(container.querySelectorAll('[data-layer="roots"]')).toHaveLength(64);
        expect(container.querySelectorAll('[data-layer="surfaces"]')).toHaveLength(0);
        expect(screen.queryByText('Crown geometry parity')).not.toBeInTheDocument();
        expect(screen.queryByText('Root anatomy families')).not.toBeInTheDocument();
    });

    it('shows a compact header, legend, and inline inspectors without a modal workflow', () => {
        render(<ClinicalChartWorkspace />);

        expect(screen.getByRole('heading', { name: 'مقارنة مخطط الأسنان' })).toBeInTheDocument();
        const legend = screen.getByRole('list', { name: 'دليل ألوان مخطط الأسنان' });
        expect(within(legend).getByText('تسوس')).toBeInTheDocument();
        expect(within(legend).getByText('حشو تجميلي')).toBeInTheDocument();
        expect(screen.getAllByTestId('clinical-chart-inspector')).toHaveLength(2);
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('keeps focus selection isolated between chart instances', () => {
        const { container } = render(<ClinicalChartWorkspace />);
        const current = container.querySelector('[data-chart-instance="odontogram-current"]');
        const history = container.querySelector('[data-chart-instance="odontogram-history"]');

        fireEvent.change(screen.getByLabelText('تركيز المعاينة - المخطط الحالي'), {
            target: { value: '46:D' },
        });

        expect(current).toHaveAttribute('data-selected-focus', '46:D');
        expect(history).toHaveAttribute('data-selected-focus', '');
        const currentInspector = within(current).getByRole('complementary', {
            name: 'المخطط الحالي - لوحة الفحص',
        });
        expect(within(currentInspector).getByText('46')).toBeInTheDocument();
        expect(within(currentInspector).getByText('بعيد (D)')).toBeInTheDocument();
    });

    it('keeps root and clinical-layer filters isolated between chart instances', () => {
        const { container } = render(<ClinicalChartWorkspace />);
        const current = container.querySelector('[data-chart-instance="odontogram-current"]');
        const history = container.querySelector('[data-chart-instance="odontogram-history"]');

        fireEvent.click(screen.getByLabelText('إظهار الجذور - المخطط الحالي'));
        fireEvent.click(screen.getByLabelText('إظهار الحالات والإجراءات - المخطط الحالي'));

        expect(current.querySelectorAll('[data-layer="roots"]')).toHaveLength(0);
        expect(history.querySelectorAll('[data-layer="roots"]')).toHaveLength(32);
        expect(current.querySelectorAll('[data-effect]')).toHaveLength(0);
        expect(history.querySelector('[data-interaction-mode="read-only"]')).toBeInTheDocument();
    });

    it('switches the feature between Arabic RTL and English LTR', () => {
        render(<ClinicalChartWorkspace />);
        const workspace = screen.getByTestId('clinical-chart-workspace');

        expect(workspace).toHaveAttribute('dir', 'rtl');
        expect(workspace).toHaveAttribute('lang', 'ar');
        fireEvent.click(screen.getByRole('button', { name: 'English' }));

        expect(workspace).toHaveAttribute('dir', 'ltr');
        expect(workspace).toHaveAttribute('lang', 'en');
        expect(screen.getByRole('heading', { name: 'Odontogram comparison' })).toBeInTheDocument();
        expect(screen.getByLabelText('Preview focus - Current chart')).toBeInTheDocument();
    });

    it('provides mobile quadrant navigation with practical accessible labels', () => {
        const { container } = render(<ClinicalChartWorkspace />);
        const current = container.querySelector('[data-chart-instance="odontogram-current"]');
        const targetTooth = current.querySelector('[data-layer="crown"][data-tooth-key="14"]');
        targetTooth.scrollIntoView = vi.fn();
        const quadrantNav = within(current).getByRole('navigation', {
            name: 'انتقال سريع بين الأرباع',
        });

        fireEvent.click(within(quadrantNav).getByRole('button', {
            name: 'الربع العلوي الأيمن',
        }));

        expect(targetTooth.scrollIntoView).toHaveBeenCalledWith({
            behavior: 'smooth',
            block: 'nearest',
            inline: 'center',
        });
        expect(within(quadrantNav).getAllByRole('button')).toHaveLength(4);
    });

    it('exposes visible focus styles on all feature controls', () => {
        render(<ClinicalChartWorkspace />);

        expect(screen.getByRole('button', { name: 'English' })).toHaveClass('focus-visible:ring-2');
        expect(screen.getByLabelText('تركيز المعاينة - المخطط الحالي')).toHaveClass('focus-visible:ring-2');
        expect(screen.getByLabelText('إظهار الجذور - المخطط الحالي')).toHaveClass('focus-visible:ring-2');
        expect(screen.getAllByRole('button', { name: 'الربع العلوي الأيمن' })[0])
            .toHaveClass('focus-visible:ring-2');
    });
});
