import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import DualChartCompareWorkspace from '../components/DualChartCompareWorkspace';
import ClinicalChartWorkspace from '../ClinicalChartWorkspace';

describe('Phase A13 — Dual-Chart History Compare', () => {
    describe('A13-M01: Dual-chart page rendering', () => {
        it('renders two chart instances side-by-side in the dual-chart workspace', () => {
            render(<DualChartCompareWorkspace />);

            expect(screen.getByTestId('dual-chart-compare-workspace')).toBeInTheDocument();
            const panelA = screen.getByTestId('dual-chart-panel-a');
            const panelB = screen.getByTestId('dual-chart-panel-b');

            expect(panelA).toBeInTheDocument();
            expect(panelB).toBeInTheDocument();

            // Each panel renders an independent Dentix chart with 32 teeth
            expect(panelA.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
            expect(panelB.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);

            // Total 64 tooth units rendered concurrently
            expect(document.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(64);
        });

        it('switches to dual-chart mode via tabs in ClinicalChartWorkspace', () => {
            render(<ClinicalChartWorkspace />);

            // Initially in single mode
            expect(screen.queryByTestId('dual-chart-compare-workspace')).not.toBeInTheDocument();

            // Click the dual chart tab
            fireEvent.click(screen.getByTestId('tab-dual-chart'));

            // Now dual chart mode is active
            expect(screen.getByTestId('dual-chart-compare-workspace')).toBeInTheDocument();
            expect(screen.getByTestId('dual-chart-panel-a')).toBeInTheDocument();
            expect(screen.getByTestId('dual-chart-panel-b')).toBeInTheDocument();
        });
    });

    describe('A13-M02: State isolation', () => {
        it('isolates surface selection between Instance A and Instance B without bleed', () => {
            render(<DualChartCompareWorkspace />);

            const panelA = screen.getByTestId('dual-chart-panel-a');
            const panelB = screen.getByTestId('dual-chart-panel-b');

            // Find surface buttons on tooth 46 (Palmer LR6) in panel A and panel B
            const surfaceA46O = within(panelA).getByRole('button', { name: /Tooth LR6 — Occlusal \(O\)/i });
            const surfaceB46O = within(panelB).getByRole('button', { name: /Tooth LR6 — Occlusal \(O\)/i });

            expect(surfaceA46O).toBeInTheDocument();
            expect(surfaceB46O).toBeInTheDocument();

            // Select surface O on tooth 46 in Chart A
            fireEvent.click(surfaceA46O);

            // Panel A's tooth 46 has aria-pressed="true"
            expect(surfaceA46O).toHaveAttribute('aria-pressed', 'true');

            // Panel B's tooth 46 surface O MUST NOT be selected
            expect(surfaceB46O).toHaveAttribute('aria-pressed', 'false');

            // Select surface O on tooth 46 in Chart B
            fireEvent.click(surfaceB46O);
            expect(surfaceB46O).toHaveAttribute('aria-pressed', 'true');

            // Deselect on Chart A
            fireEvent.click(surfaceA46O);
            expect(surfaceA46O).toHaveAttribute('aria-pressed', 'false');
            // Chart B selection is preserved
            expect(surfaceB46O).toHaveAttribute('aria-pressed', 'true');
        });

        it('isolates fixture selection between instances independently', () => {
            render(<DualChartCompareWorkspace />);

            const selectA = screen.getByTestId('select-fixture-a');
            const selectB = screen.getByTestId('select-fixture-b');

            expect(selectA.value).toBe('cariesOnSurface');
            expect(selectB.value).toBe('modRestoration');

            // Change fixture on A to primary
            fireEvent.change(selectA, { target: { value: 'primaryDentition' } });
            expect(selectA.value).toBe('primaryDentition');
            // Panel B remains unchanged
            expect(selectB.value).toBe('modRestoration');

            const panelA = screen.getByTestId('dual-chart-panel-a');
            const panelB = screen.getByTestId('dual-chart-panel-b');

            // Primary dentition has 20 teeth in panel A
            expect(panelA.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(20);
            // Panel B still has 32 teeth
            expect(panelB.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
        });
    });

    describe('A13-M03: Independent layer filtering', () => {
        it('toggles roots layer on Chart A without hiding roots on Chart B', () => {
            render(<DualChartCompareWorkspace />);

            const panelA = screen.getByTestId('dual-chart-panel-a');
            const panelB = screen.getByTestId('dual-chart-panel-b');

            expect(panelA.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(32);
            expect(panelB.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(32);

            // Toggle roots off on Chart A
            fireEvent.click(screen.getByTestId('toggle-roots-a'));

            // Chart A roots are now hidden (0 rendered)
            expect(panelA.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(0);

            // Chart B roots remain fully visible (32 rendered)
            expect(panelB.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(32);

            // Toggle roots off on Chart B
            fireEvent.click(screen.getByTestId('toggle-roots-b'));
            expect(panelB.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(0);

            // Re-enable roots on Chart A
            fireEvent.click(screen.getByTestId('toggle-roots-a'));
            expect(panelA.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(32);
            expect(panelB.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(0);
        });

        it('toggles surfaces layer on Chart B without affecting surfaces on Chart A', () => {
            render(<DualChartCompareWorkspace />);

            const panelA = screen.getByTestId('dual-chart-panel-a');
            const panelB = screen.getByTestId('dual-chart-panel-b');

            expect(panelA.querySelectorAll('g[data-layer="surfaces"]')).toHaveLength(32);
            expect(panelB.querySelectorAll('g[data-layer="surfaces"]')).toHaveLength(32);

            // Toggle surfaces off on Chart B
            fireEvent.click(screen.getByTestId('toggle-surfaces-b'));

            // Chart B surfaces layer is unmounted (0 surface groups)
            expect(panelB.querySelectorAll('g[data-layer="surfaces"]')).toHaveLength(0);

            // Chart A surfaces remain active (32 surface groups, 160 surface buttons)
            expect(panelA.querySelectorAll('g[data-layer="surfaces"]')).toHaveLength(32);
            expect(within(panelA).getAllByRole('button', { name: /Tooth .* — .* \([A-Z]\)/i })).toHaveLength(160);
        });
    });

    describe('A13-M04: Read-only multi-instance support', () => {
        it('supports concurrent read-only mode across both instances', () => {
            render(<DualChartCompareWorkspace initialReadOnly={true} />);

            const panelA = screen.getByTestId('dual-chart-panel-a');
            const panelB = screen.getByTestId('dual-chart-panel-b');

            // When in read-only mode, surface selection is disabled so no surface buttons exist
            expect(panelA.querySelectorAll('g[data-layer="surfaces"]')).toHaveLength(0);
            expect(panelB.querySelectorAll('g[data-layer="surfaces"]')).toHaveLength(0);

            // Both charts still cleanly render visual tooth crowns and roots
            expect(panelA.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
            expect(panelB.querySelectorAll('svg[data-layer="crown"]')).toHaveLength(32);
        });

        it('allows toggling read-only on one instance while leaving the other interactive', () => {
            render(<DualChartCompareWorkspace initialReadOnly={false} />);

            const panelA = screen.getByTestId('dual-chart-panel-a');
            const panelB = screen.getByTestId('dual-chart-panel-b');

            // Initially both are interactive (160 surface buttons each)
            expect(within(panelA).getAllByRole('button', { name: /Tooth .* — .* \([A-Z]\)/i })).toHaveLength(160);
            expect(within(panelB).getAllByRole('button', { name: /Tooth .* — .* \([A-Z]\)/i })).toHaveLength(160);

            // Toggle Chart A to read-only
            fireEvent.click(screen.getByTestId('toggle-readonly-a'));

            // Chart A surface buttons are disabled/unmounted
            expect(panelA.querySelectorAll('g[data-layer="surfaces"]')).toHaveLength(0);

            // Chart B still has 160 interactive surface buttons
            expect(within(panelB).getAllByRole('button', { name: /Tooth .* — .* \([A-Z]\)/i })).toHaveLength(160);
        });
    });
});
