import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalChartWorkspace from '../ClinicalChartWorkspace';

describe('ClinicalChartWorkspace scaffold', () => {
    it('renders two isolated read-only Dentix charts', () => {
        const { container } = render(<ClinicalChartWorkspace />);

        expect(screen.getByTestId('clinical-chart-workspace')).toBeInTheDocument();
        expect(screen.getAllByTestId('clinical-chart-instance')).toHaveLength(2);
        expect(screen.getByRole('heading', { name: 'Current chart' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Previous chart' })).toBeInTheDocument();
        expect(container.querySelectorAll('[data-interaction-mode="read-only"]')).toHaveLength(2);
        expect(container.querySelectorAll('[data-layer="roots"]')).toHaveLength(64);
        expect(container.querySelectorAll('[data-layer="surfaces"]')).toHaveLength(0);
        expect(screen.queryByText('Crown geometry parity')).not.toBeInTheDocument();
        expect(screen.queryByText('Root anatomy families')).not.toBeInTheDocument();
    });

    it('shows a compact header, legend, and inline inspectors without a modal workflow', () => {
        render(<ClinicalChartWorkspace />);

        expect(screen.getByRole('heading', { name: 'Odontogram comparison' })).toBeInTheDocument();
        const legend = screen.getByRole('list', { name: 'Clinical chart legend' });
        expect(within(legend).getByText('Caries')).toBeInTheDocument();
        expect(within(legend).getByText('Composite')).toBeInTheDocument();
        expect(screen.getAllByTestId('clinical-chart-inspector')).toHaveLength(2);
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('keeps focus selection isolated between chart instances', () => {
        const { container } = render(<ClinicalChartWorkspace />);
        const current = container.querySelector('[data-chart-instance="odontogram-current"]');
        const history = container.querySelector('[data-chart-instance="odontogram-history"]');

        fireEvent.change(screen.getByLabelText('Preview focus - Current chart'), { target: { value: '46:D' } });

        expect(current).toHaveAttribute('data-selected-focus', '46:D');
        expect(history).toHaveAttribute('data-selected-focus', '');
        const currentInspector = within(current).getByRole('complementary', {
            name: 'Current chart inspector',
        });
        expect(within(currentInspector).getByText('46')).toBeInTheDocument();
        expect(within(currentInspector).getByText('Distal (D)')).toBeInTheDocument();

    });

    it('keeps root and clinical-layer filters isolated between chart instances', () => {
        const { container } = render(<ClinicalChartWorkspace />);
        const current = container.querySelector('[data-chart-instance="odontogram-current"]');
        const history = container.querySelector('[data-chart-instance="odontogram-history"]');

        fireEvent.click(screen.getByLabelText('Show roots - Current chart'));
        fireEvent.click(screen.getByLabelText('Show conditions and procedures - Current chart'));

        expect(current.querySelectorAll('[data-layer="roots"]')).toHaveLength(0);
        expect(history.querySelectorAll('[data-layer="roots"]')).toHaveLength(32);
        expect(current.querySelectorAll('[data-effect]')).toHaveLength(0);
        expect(history.querySelector('[data-interaction-mode="read-only"]')).toBeInTheDocument();
    });
});
