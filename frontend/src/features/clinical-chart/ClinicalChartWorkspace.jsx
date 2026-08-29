/**
 * Isolated entry point for the Dentix-native odontogram foundation.
 *
 * Clinical data is intentionally absent during the scaffold phase. Later phases
 * inject a Projection DTO and keep persistence outside this workspace.
 */
export default function ClinicalChartWorkspace() {
    return (
        <main
            className="min-h-screen bg-slate-50 px-4 py-6 text-slate-900 sm:px-6 lg:px-8"
            data-testid="clinical-chart-workspace"
            dir="rtl"
        >
            <section className="mx-auto max-w-7xl rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
                <header className="border-b border-slate-200 pb-4">
                    <p className="text-sm font-semibold text-blue-700">Dentix Native Renderer</p>
                    <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">
                        مخطط الأسنان
                    </h1>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                        مساحة تطوير معزولة لتأسيس تشريح الأسنان والجذور وقواعد العرض البرمجية.
                    </p>
                </header>

                <div
                    className="mt-5 flex min-h-72 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center"
                    role="status"
                >
                    <div>
                        <p className="font-semibold text-slate-700">Chart foundation ready</p>
                        <p className="mt-1 text-sm text-slate-500">
                            Anatomy and renderer layers are added in the next bounded phases.
                        </p>
                    </div>
                </div>
            </section>
        </main>
    );
}

