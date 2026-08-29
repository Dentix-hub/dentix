import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DentalChartSVG from './DentalChartSVG';

const getCrownContract = (container) => Array.from(container.querySelectorAll('svg[data-layer="crown"]')).map((svg) => {
    const path = svg.querySelector('path');
    return {
        toothKey: svg.getAttribute('data-tooth-key'),
        width: svg.getAttribute('width'),
        height: svg.getAttribute('height'),
        viewBox: svg.getAttribute('viewBox'),
        path: path.getAttribute('d'),
        fill: path.getAttribute('fill'),
        stroke: path.getAttribute('stroke'),
        strokeWidth: path.getAttribute('stroke-width'),
    };
});

describe('DentalChartSVG optional root extension', () => {
    it('keeps the production chart root-free by default', () => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={false} />,
        );

        expect(container.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
        expect(container.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(0);
    });

    it('adds roots behind the same untouched crown geometry only when requested', () => {
        const props = { teethStatus: {}, onToothClick: vi.fn(), isPediatric: false };
        const { container, rerender } = render(<DentalChartSVG {...props} />);
        const baselineCrowns = getCrownContract(container);

        rerender(<DentalChartSVG {...props} showRoots />);

        expect(container.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(32);
        expect(getCrownContract(container)).toEqual(baselineCrowns);
        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="18"] g')).toHaveAttribute('transform', 'rotate(180 25 24)');
        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="38"] g')).not.toHaveAttribute('transform');
    });

    it('supports the complete primary dentition with the same optional layer', () => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric showRoots />,
        );

        expect(container.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(20);
        expect(container.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(20);
    });
});
