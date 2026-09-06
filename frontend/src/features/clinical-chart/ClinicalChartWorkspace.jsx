import { useState } from 'react';
import ClinicalChartComparisonCard from './components/ClinicalChartComparisonCard';
import ClinicalChartWorkspaceShell from './components/ClinicalChartWorkspaceShell';
import {
    CLINICAL_CHART_COPY,
    CLINICAL_CHART_LOCALES,
} from './components/clinicalChartWorkspaceCopy';
import { A12_ADULT_DENTITION_FIXTURE } from './fixtures';
import { VISUAL_RULE_DEMO_PROJECTION } from './fixtures/visualRuleDemoProjection';

/**
 * Isolated entry point for the Dentix-native odontogram foundation.
 *
 * The comparison cards own presentation-only state. Both receive immutable demo
 * projections and remain disconnected from persistence and clinical workflows.
 */
export default function ClinicalChartWorkspace() {
    const [locale, setLocale] = useState(CLINICAL_CHART_LOCALES.AR);
    const copy = CLINICAL_CHART_COPY[locale];
    const direction = locale === CLINICAL_CHART_LOCALES.AR ? 'rtl' : 'ltr';

    return (
        <main
            className="min-h-screen bg-background p-3 sm:p-6"
            data-locale={locale}
            data-testid="clinical-chart-workspace"
            dir={direction}
            lang={locale}
        >
            <div className="mx-auto max-w-[1600px]">
                <ClinicalChartWorkspaceShell
                    copy={copy}
                    locale={locale}
                    onLocaleChange={setLocale}
                />
                <div className="grid min-w-0 gap-5">
                    <ClinicalChartComparisonCard
                        chartId="odontogram-current"
                        copy={copy}
                        projection={VISUAL_RULE_DEMO_PROJECTION}
                        subtitle={copy.currentSubtitle}
                        title={copy.currentTitle}
                    />
                    <ClinicalChartComparisonCard
                        chartId="odontogram-history"
                        copy={copy}
                        projection={A12_ADULT_DENTITION_FIXTURE}
                        subtitle={copy.historySubtitle}
                        title={copy.historyTitle}
                    />
                </div>
            </div>
        </main>
    );
}
