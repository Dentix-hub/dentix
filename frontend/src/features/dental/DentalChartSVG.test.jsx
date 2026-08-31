import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DentalChartSVG from './DentalChartSVG';

const getCrownContract = (container) => Array.from(container.querySelectorAll('svg[data-layer="crown"]')).map((svg) => {
    const path = svg.querySelector('path');
    const orientation = svg.querySelector('[data-crown-orientation]');
    const scale = svg.querySelector('[data-crown-scale]');
    return {
        toothKey: svg.getAttribute('data-tooth-key'),
        width: svg.getAttribute('width'),
        height: svg.getAttribute('height'),
        viewBox: svg.getAttribute('viewBox'),
        path: path.getAttribute('d'),
        fill: path.getAttribute('fill'),
        stroke: path.getAttribute('stroke'),
        strokeWidth: path.getAttribute('stroke-width'),
        transform: orientation.getAttribute('transform'),
        scale: scale.getAttribute('transform'),
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

    it.each([false, true])('preserves every %s dentition crown without orientation or scale transforms', (isPediatric) => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={isPediatric} showRoots />,
        );

        const crowns = container.querySelectorAll('svg[data-layer="crown"]');
        expect(crowns).toHaveLength(isPediatric ? 20 : 32);
        crowns.forEach((crown) => {
            expect(crown.querySelector('[data-crown-orientation]')).not.toHaveAttribute('transform');
            expect(crown.querySelector('[data-crown-scale]')).toHaveAttribute('data-crown-scale', '1');
            expect(crown.querySelector('[data-crown-scale]')).not.toHaveAttribute('transform');
        });
    });

    it('renders root proportions from the same per-tooth display registry', () => {
        const { container } = render(
            <DentalChartSVG teethStatus={{}} onToothClick={vi.fn()} isPediatric={false} showRoots />,
        );

        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="11"] [data-root-scale]'))
            .toHaveAttribute('data-root-scale', '0.97 0.96');
        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="31"] [data-root-scale]'))
            .toHaveAttribute('data-root-scale', '0.95 0.92');
        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="12"] [data-root-scale]'))
            .toHaveAttribute('data-root-scale', '0.84 0.82');
        expect(container.querySelector('svg[data-layer="roots"][data-tooth-key="16"] [data-root-scale]'))
            .toHaveAttribute('data-root-scale', '0.9 0.84');
    });

    it('adds five accessible surface targets per tooth only in surface-selection mode', () => {
        const { container } = render(
            <DentalChartSVG
                teethStatus={{}}
                onToothClick={vi.fn()}
                isPediatric={false}
                showRoots
                enableSurfaceSelection
                onSurfaceClick={vi.fn()}
            />,
        );

        expect(container.querySelectorAll('[data-layer="surfaces"]')).toHaveLength(32);
        expect(screen.getAllByRole('button')).toHaveLength(160);
        expect(container.querySelectorAll('button')).toHaveLength(0);
        expect(container.querySelectorAll('[data-surface-code="O"]')).toHaveLength(20);
        expect(container.querySelectorAll('[data-surface-code="I"]')).toHaveLength(12);
    });

    it('emits neutral surface selection intents for pointer and keyboard input', () => {
        const onSurfaceClick = vi.fn();
        render(
            <DentalChartSVG
                teethStatus={{}}
                onToothClick={vi.fn()}
                isPediatric={false}
                enableSurfaceSelection
                onSurfaceClick={onSurfaceClick}
            />,
        );
        const mesialSurface = screen.getByRole('button', { name: 'Tooth UR1 — Mesial (M)' });

        fireEvent.click(mesialSurface);
        expect(onSurfaceClick).toHaveBeenLastCalledWith({ toothKey: '11', toothNumber: 8, surfaceCode: 'M' });

        fireEvent.keyDown(mesialSurface, { key: 'Enter' });
        expect(onSurfaceClick).toHaveBeenCalledTimes(2);
        expect(mesialSurface).toHaveAttribute('tabindex', '0');
        expect(mesialSurface.className.baseVal).toContain('focus:fill-blue-100');
    });

    it('shows a selected surface without changing the underlying crown path', () => {
        const { container } = render(
            <DentalChartSVG
                teethStatus={{}}
                onToothClick={vi.fn()}
                isPediatric={false}
                enableSurfaceSelection
                selectedSurface={{ toothKey: '46', surfaceCode: 'O' }}
                onSurfaceClick={vi.fn()}
            />,
        );
        const selected = container.querySelector('svg[data-tooth-key="46"] [data-surface-code="O"]');

        expect(selected).toHaveAttribute('aria-pressed', 'true');
        expect(selected.className.baseVal).toContain('fill-blue-200');
        expect(container.querySelector('svg[data-tooth-key="46"] [data-layer-role="base-anatomy"] path').getAttribute('d')).toBeTruthy();
    });

    it('keeps the direct chart non-interactive when read-only overrides surface mode', () => {
        const { container } = render(
            <DentalChartSVG
                teethStatus={{}}
                onToothClick={vi.fn()}
                isPediatric={false}
                enableSurfaceSelection
                onSurfaceClick={vi.fn()}
                readOnly
            />,
        );

        expect(screen.queryAllByRole('button')).toHaveLength(0);
        expect(container.querySelectorAll('[data-layer="surfaces"]')).toHaveLength(0);
        expect(container.firstChild).toHaveAttribute('data-interaction-mode', 'read-only');
    });
});
