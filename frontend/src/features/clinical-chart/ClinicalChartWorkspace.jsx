import DentalChartSVG from '@/features/dental/DentalChartSVG';

/**
 * Isolated entry point for the Dentix-native odontogram foundation.
 *
 * Clinical data is intentionally absent during the scaffold phase. Later phases
 * inject a Projection DTO and keep persistence outside this workspace.
 */
export default function ClinicalChartWorkspace() {
    return (
        <main className="min-h-screen bg-background p-4 sm:p-6" data-testid="clinical-chart-workspace">
            <div className="mx-auto max-w-7xl">
                <DentalChartSVG teethStatus={{}} onToothClick={() => {}} isPediatric={false} />
            </div>
        </main>
    );
}
