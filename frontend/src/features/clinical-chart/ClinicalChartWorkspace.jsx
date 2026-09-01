import ClinicalChartComparisonCard from './components/ClinicalChartComparisonCard';
import ClinicalChartWorkspaceShell from './components/ClinicalChartWorkspaceShell';
import { A12_ADULT_DENTITION_FIXTURE } from './fixtures';
import { VISUAL_RULE_DEMO_PROJECTION } from './fixtures/visualRuleDemoProjection';

/**
 * Isolated entry point for the Dentix-native odontogram foundation.
 *
 * The comparison cards own presentation-only state. Both receive immutable demo
 * projections and remain disconnected from persistence and clinical workflows.
 */
export default function ClinicalChartWorkspace() {
    return (
        <main className="min-h-screen bg-background p-3 sm:p-6" data-testid="clinical-chart-workspace">
            <div className="mx-auto max-w-[1600px]" dir="rtl">
                <ClinicalChartWorkspaceShell />
                <div className="grid min-w-0 gap-5 xl:grid-cols-2">
                    <ClinicalChartComparisonCard chartId="odontogram-current" projection={VISUAL_RULE_DEMO_PROJECTION} subtitle="Current state" title="Current chart" />
                    <ClinicalChartComparisonCard chartId="odontogram-history" projection={A12_ADULT_DENTITION_FIXTURE} subtitle="Read-only historical snapshot" title="Previous chart" />
                </div>
            </div>
        </main>
    );
}
