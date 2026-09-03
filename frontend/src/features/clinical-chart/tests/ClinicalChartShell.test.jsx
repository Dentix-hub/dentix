import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalChartShell, {
    ClinicalChartInspector,
    ClinicalChartLegend,
    ClinicalChartSelectionSummary,
} from '../components/ClinicalChartShell';
import ClinicalChartWorkspace from '../ClinicalChartWorkspace';
import { TARGET_COVERAGE_PROJECTION } from '../fixtures/demoProjectionFixtures';

describe('Phase A14 — Minimalist Shell UI, Legend & Inspector', () => {
    describe('A14-M01: Chart shell header controls', () => {
        it('renders shell header with title, notation selector, and layer toggles', () => {
            render(<ClinicalChartShell />);

            expect(screen.getByTestId('chart-shell-header')).toBeInTheDocument();
            expect(screen.getByTestId('shell-notation-select')).toBeInTheDocument();
            expect(screen.getByTestId('shell-toggle-roots')).toBeInTheDocument();
            expect(screen.getByTestId('shell-toggle-surfaces')).toBeInTheDocument();
            expect(screen.getByTestId('shell-clear-selection')).toBeInTheDocument();
        });

        it('switches notation mode from Palmer to FDI via shell header', () => {
            render(<ClinicalChartShell />);

            const select = screen.getByTestId('shell-notation-select');
            expect(select.value).toBe('palmer');

            // Switch to FDI
            fireEvent.change(select, { target: { value: 'fdi' } });
            expect(select.value).toBe('fdi');

            // DentalChartSVG updates to FDI notation
            expect(document.querySelector('[data-notation-mode="fdi"]')).toBeInTheDocument();
            expect(screen.getAllByText(/FDI World Dental Federation Notation/i)).toHaveLength(2);
        });

        it('toggles roots layer and surfaces layer via shell header buttons', () => {
            render(<ClinicalChartShell />);

            expect(document.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(32);

            // Toggle roots off
            fireEvent.click(screen.getByTestId('shell-toggle-roots'));
            expect(document.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(0);

            // Toggle roots on
            fireEvent.click(screen.getByTestId('shell-toggle-roots'));
            expect(document.querySelectorAll('svg[data-layer="roots"]')).toHaveLength(32);

            // Toggle surfaces off
            expect(document.querySelectorAll('g[data-layer="surfaces"]')).toHaveLength(32);
            fireEvent.click(screen.getByTestId('shell-toggle-surfaces'));
            expect(document.querySelectorAll('g[data-layer="surfaces"]')).toHaveLength(0);
        });
    });

    describe('A14-M02: Simple clinical legend', () => {
        it('renders color-coded legend badges for findings and procedures', () => {
            render(<ClinicalChartLegend />);

            const legend = screen.getByTestId('clinical-chart-legend');
            expect(legend).toBeInTheDocument();

            // All key clinical categories are represented in the legend
            expect(within(legend).getByText(/تسوس سريري \(Caries\)/i)).toBeInTheDocument();
            expect(within(legend).getByText(/حشوة مركبة \(Composite\)/i)).toBeInTheDocument();
            expect(within(legend).getByText(/علاج جذور \(RCT\)/i)).toBeInTheDocument();
            expect(within(legend).getByText(/تاج تركيبي \(Crown\)/i)).toBeInTheDocument();
            expect(within(legend).getByText(/جسر أسنان \(Bridge\)/i)).toBeInTheDocument();
            expect(within(legend).getByText(/زراعة سنية \(Implant\)/i)).toBeInTheDocument();
            expect(within(legend).getByText(/خلع مخطط \(Planned Extract\)/i)).toBeInTheDocument();
            expect(within(legend).getByText(/سن مخلوع \/ مفقود \(Missing\)/i)).toBeInTheDocument();
        });
    });

    describe('A14-M03: Simple inspector panel', () => {
        it('renders empty instructional placeholder when no tooth is selected', () => {
            render(<ClinicalChartInspector projection={TARGET_COVERAGE_PROJECTION} selection={null} />);

            const inspector = screen.getByTestId('clinical-chart-inspector');
            expect(within(inspector).getByText(/لوحة فحص الأسنان \(Inspector\)/i)).toBeInTheDocument();
            expect(within(inspector).getByText(/انقر على أي سن أو سطح في المخطط/i)).toBeInTheDocument();
        });

        it('displays tooth anatomy, notation aliases, and clinical procedures when a tooth is selected', () => {
            const selection = { kind: 'surface', toothKey: '46', surfaceCode: 'D' };
            render(
                <ClinicalChartInspector
                    projection={TARGET_COVERAGE_PROJECTION}
                    selection={selection}
                />,
            );

            const inspector = screen.getByTestId('clinical-chart-inspector');
            expect(within(inspector).getByText(/FDI: 46/i)).toBeInTheDocument();
            expect(within(inspector).getByText(/Palmer: LR6/i)).toBeInTheDocument();
            expect(within(inspector).getByText(/Univ: #30/i)).toBeInTheDocument();
            expect(within(inspector).getByText(/طاحن \(Molar\)/i)).toBeInTheDocument();
            expect(within(inspector).getByText(/الفك السفلي/i)).toBeInTheDocument();
            expect(within(inspector).getByText(/السطح D \(Distal\)/i)).toBeInTheDocument();

            // Shows registered finding (Caries) from TARGET_COVERAGE_PROJECTION
            expect(within(inspector).getByText(/تشخيص: CARIES/i)).toBeInTheDocument();
        });
    });

    describe('A14-M04: Simple selection summary', () => {
        it('renders empty state prompt when nothing is selected', () => {
            render(<ClinicalChartSelectionSummary selection={null} />);

            expect(screen.getByTestId('selection-summary-banner')).toHaveTextContent(
                /لم يتم تحديد أي سن أو سطح/i,
            );
        });

        it('renders active tooth and surface summary with clear button', () => {
            let cleared = false;
            const selection = { kind: 'surface', toothKey: '46', surfaceCode: 'O' };
            render(
                <ClinicalChartSelectionSummary
                    onClear={() => { cleared = true; }}
                    selection={selection}
                />,
            );

            const banner = screen.getByTestId('selection-summary-banner');
            expect(banner).toHaveTextContent(/FDI: 46 \(LR6\)/i);
            expect(banner).toHaveTextContent(/السطح:.*O/i);

            const clearBtn = screen.getByTestId('clear-selection-summary-btn');
            fireEvent.click(clearBtn);
            expect(cleared).toBe(true);
        });
    });

    describe('A14-M05: Intentionally simple shell UI integration', () => {
        it('integrates complete shell with legend, inspector, and selection workflow', () => {
            render(<ClinicalChartShell />);

            expect(screen.getByTestId('clinical-chart-shell')).toBeInTheDocument();
            expect(screen.getByTestId('chart-shell-header')).toBeInTheDocument();
            expect(screen.getByTestId('selection-summary-banner')).toBeInTheDocument();
            expect(screen.getByTestId('clinical-chart-legend')).toBeInTheDocument();
            expect(screen.getByTestId('clinical-chart-inspector')).toBeInTheDocument();

            // Select surface O on tooth 46 (Palmer LR6)
            const surface46O = screen.getByRole('button', { name: /Tooth LR6 — Occlusal \(O\)/i });
            fireEvent.click(surface46O);

            // Selection summary updates
            expect(screen.getByTestId('selection-summary-banner')).toHaveTextContent(/FDI: 46/i);

            // Clear selection via shell header button
            const clearBtn = screen.getByTestId('shell-clear-selection');
            expect(clearBtn).not.toBeDisabled();
            fireEvent.click(clearBtn);

            // Returns to empty selection
            expect(screen.getByTestId('selection-summary-banner')).toHaveTextContent(/لم يتم تحديد/i);
        });

        it('switches to Shell & Inspector tab in ClinicalChartWorkspace', () => {
            render(<ClinicalChartWorkspace />);

            // Switch to shell tab
            fireEvent.click(screen.getByTestId('tab-shell-chart'));

            expect(screen.getByTestId('clinical-chart-shell')).toBeInTheDocument();
            expect(screen.getByTestId('chart-shell-header')).toBeInTheDocument();
        });
    });
});
