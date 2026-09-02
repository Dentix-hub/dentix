import { CLINICAL_CHART_LOCALES } from './clinicalChartWorkspaceCopy';

const LEGEND_ITEMS = Object.freeze([
    Object.freeze({ key: 'caries', color: '#b91c1c' }),
    Object.freeze({ key: 'composite', color: '#2563eb' }),
    Object.freeze({ key: 'endodontic', color: '#7c3aed' }),
    Object.freeze({ key: 'prosthetic', color: '#ca8a04' }),
    Object.freeze({ key: 'implant', color: '#0f766e' }),
    Object.freeze({ key: 'missing', color: '#64748b' }),
]);

export default function ClinicalChartWorkspaceShell({ copy, locale, onLocaleChange }) {
    return (
        <header className="mb-5 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <p className="text-sm font-semibold text-blue-700">{copy.eyebrow}</p>
                    <h1 className="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">
                        {copy.workspaceTitle}
                    </h1>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                        {copy.workspaceDescription}
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <div aria-label="Language / اللغة" className="flex rounded-xl border border-slate-200 bg-slate-50 p-1" role="group">
                        {Object.values(CLINICAL_CHART_LOCALES).map((localeOption) => (
                            <button
                                aria-pressed={locale === localeOption}
                                className="min-h-10 rounded-lg px-3 text-sm font-bold text-slate-700 outline-none transition-colors hover:bg-white focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                                key={localeOption}
                                onClick={() => onLocaleChange(localeOption)}
                                type="button"
                            >
                                {localeOption === CLINICAL_CHART_LOCALES.AR ? 'العربية' : 'English'}
                            </button>
                        ))}
                    </div>
                    <span className="w-fit rounded-full bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700">
                        {copy.readOnly}
                    </span>
                </div>
            </div>

            <div aria-label={copy.legendLabel} className="mt-4 flex flex-wrap gap-x-5 gap-y-2 border-t border-slate-100 pt-4" role="list">
                {LEGEND_ITEMS.map(({ key, color }) => (
                    <div className="flex items-center gap-2 text-sm text-slate-700" key={key} role="listitem">
                        <span aria-hidden="true" className="h-3 w-3 rounded-full border border-black/10" style={{ backgroundColor: color }} />
                        <span>{copy.legend[key]}</span>
                    </div>
                ))}
            </div>
        </header>
    );
}
