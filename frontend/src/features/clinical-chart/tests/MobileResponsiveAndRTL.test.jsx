import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DentalChartSVG from '../../dental/DentalChartSVG';
import ClinicalChartShell from '../components/ClinicalChartShell';
import ClinicalChartWorkspace from '../ClinicalChartWorkspace';

describe('Phase A15 — Mobile, Tablet, Responsive, RTL & Accessibility', () => {
    describe('A15-M01: Desktop layout verification', () => {
        it('renders full 32-tooth arch cleanly on desktop within standard max width', () => {
            render(<ClinicalChartWorkspace />);

            const workspace = screen.getByTestId('clinical-chart-workspace');
            expect(workspace).toHaveClass('p-4', 'sm:p-6');

            const container = workspace.querySelector('.max-w-7xl');
            expect(container).toBeInTheDocument();

            // All 32 teeth crowns are present simultaneously
            expect(document.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
        });
    });

    describe('A15-M02: Tablet width verification', () => {
        it('provides smooth horizontal scroll container with touch panning for tablet viewports', () => {
            render(<DentalChartSVG />);

            const scrollContainer = document.querySelector('.overflow-x-auto');
            expect(scrollContainer).toBeInTheDocument();
            expect(scrollContainer).toHaveClass('touch-pan-x', 'overscroll-x-contain');

            // Midline divider is preserved
            const midline = document.querySelectorAll('.w-0\\.5');
            expect(midline.length).toBeGreaterThanOrEqual(2);
        });
    });

    describe('A15-M03: Mobile width verification', () => {
        it('applies mobile-first responsive padding and overflow safeguards', () => {
            render(<DentalChartSVG />);

            const outerBox = document.querySelector('[data-notation-mode]');
            expect(outerBox).toHaveClass('min-w-0', 'p-3', 'sm:rounded-3xl', 'sm:p-5');
        });
    });

    describe('A15-M04: Quadrant-friendly mobile behavior', () => {
        it('supports focusing on a single quadrant to optimize mobile tapping without arch scrolling', () => {
            render(<DentalChartSVG focusQuadrant="UR" />);

            expect(document.querySelector('[data-focus-quadrant="UR"]')).toBeInTheDocument();

            // Only Upper Right quadrant is rendered (8 teeth)
            expect(document.querySelector('[data-quadrant="UR"]')).toBeInTheDocument();
            expect(document.querySelector('[data-quadrant="UL"]')).toBeNull();
            expect(document.querySelector('[data-quadrant="LL"]')).toBeNull();
            expect(document.querySelector('[data-quadrant="LR"]')).toBeNull();

            expect(document.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(8);
        });

        it('supports focusing on upper arch or lower arch', () => {
            const { rerender } = render(<DentalChartSVG focusQuadrant="upper" />);

            expect(document.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(16);
            expect(document.querySelector('[data-quadrant="UR"]')).toBeInTheDocument();
            expect(document.querySelector('[data-quadrant="UL"]')).toBeInTheDocument();
            expect(document.querySelector('[data-quadrant="LL"]')).toBeNull();

            // Switch to lower
            rerender(<DentalChartSVG focusQuadrant="lower" />);
            expect(document.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(16);
            expect(document.querySelector('[data-quadrant="LL"]')).toBeInTheDocument();
            expect(document.querySelector('[data-quadrant="LR"]')).toBeInTheDocument();
            expect(document.querySelector('[data-quadrant="UR"]')).toBeNull();
        });

        it('switches quadrant focus via ClinicalChartShell header selector', () => {
            render(<ClinicalChartShell />);

            const quadrantSelect = screen.getByTestId('shell-quadrant-select');
            expect(quadrantSelect.value).toBe('all');
            expect(document.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);

            // Select UR
            fireEvent.change(quadrantSelect, { target: { value: 'UR' } });
            expect(quadrantSelect.value).toBe('UR');
            expect(document.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(8);

            // Switch back to all
            fireEvent.change(quadrantSelect, { target: { value: 'all' } });
            expect(document.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
        });
    });

    describe('A15-M05: Arabic RTL layout verification', () => {
        it('preserves anatomical LTR orientation inside SVG canvas even when parent page is RTL', () => {
            render(
                <div dir="rtl">
                    <ClinicalChartShell />
                </div>,
            );

            // Outer wrapper respects RTL
            const outerRtl = screen.getByTestId('clinical-chart-shell').closest('[dir="rtl"]');
            expect(outerRtl).toBeInTheDocument();

            // Anatomical chart MUST have explicit dir="ltr" to prevent anatomical axis inversion
            const anatomicalChart = document.querySelector('[data-notation-mode] > div[dir="ltr"]');
            expect(anatomicalChart).toBeInTheDocument();

            // Upper Left (patient's left, viewer's right) comes first in DOM order
            const quads = document.querySelectorAll('[data-quadrant]');
            expect(quads[0]).toHaveAttribute('data-quadrant', 'UL');
            expect(quads[1]).toHaveAttribute('data-quadrant', 'UR');
        });
    });

    describe('A15-M06: English LTR layout verification', () => {
        it('renders cleanly when parent container is dir="ltr"', () => {
            render(
                <div dir="ltr">
                    <ClinicalChartShell />
                </div>,
            );

            expect(screen.getByTestId('clinical-chart-shell')).toBeInTheDocument();
            expect(screen.getByTestId('chart-shell-header')).toBeInTheDocument();
        });
    });

    describe('A15-M07: Keyboard focus states', () => {
        it('ensures interactive surfaces have accessible keyboard focus attributes and respond to Enter/Space', () => {
            const onSurfaceClick = vi.fn();
            render(
                <DentalChartSVG
                    enableSurfaceSelection
                    onSurfaceClick={onSurfaceClick}
                />,
            );

            const surfaceButton = screen.getByRole('button', { name: 'Tooth UR1 — Mesial (M)' });
            expect(surfaceButton).toHaveAttribute('tabindex', '0');
            expect(surfaceButton.className.baseVal).toContain('focus:fill-blue-100');

            // Keyboard Space press triggers selection
            fireEvent.keyDown(surfaceButton, { key: ' ' });
            expect(onSurfaceClick).toHaveBeenCalledTimes(1);

            // Keyboard Enter press triggers selection
            fireEvent.keyDown(surfaceButton, { key: 'Enter' });
            expect(onSurfaceClick).toHaveBeenCalledTimes(2);
        });
    });

    describe('A15-M08: High-contrast visibility verification', () => {
        it('uses accessible high-contrast border and text classes for status and findings', () => {
            render(<ClinicalChartShell />);

            const legend = screen.getByTestId('clinical-chart-legend');
            expect(legend).toBeInTheDocument();

            // Legend items have strong contrast borders and backgrounds
            const redItem = within(legend).getByText(/تسوس سريري \(Caries\)/i).closest('div');
            expect(redItem).toHaveClass('border-red-500', 'text-red-700');

            const blueItem = within(legend).getByText(/حشوة مركبة \(Composite\)/i).closest('div');
            expect(blueItem).toHaveClass('border-blue-500', 'text-blue-700');
        });
    });
});
