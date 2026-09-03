import { getOrganicToothType } from '@/features/dental/v3/assets/dentalPaths';
import { getCrownGeometry } from '../rendering/crownGeometry';

const SOURCE_UNIVERSAL_TOOTH = 3;
const NORMALIZED_FDI_TOOTH = '16';

function CrownSvg({ label, paths, testId }) {
    return (
        <figure className="rounded-xl border border-slate-200 bg-white p-4 text-center">
            <svg
                aria-label={label}
                className="mx-auto h-48 w-32 overflow-visible"
                data-testid={testId}
                role="img"
                viewBox="0 0 100 160"
            >
                {Object.entries(paths).map(([surface, path]) => (
                    <path
                        d={path}
                        fill="#ffffff"
                        key={surface}
                        stroke="#cbd5e1"
                        strokeWidth="1"
                    />
                ))}
            </svg>
            <figcaption className="mt-2 text-sm font-semibold text-slate-600">{label}</figcaption>
        </figure>
    );
}

export default function CrownParityPreview() {
    const source = getOrganicToothType(SOURCE_UNIVERSAL_TOOTH);
    const normalized = getCrownGeometry(NORMALIZED_FDI_TOOTH);

    return (
        <section aria-labelledby="crown-parity-title" className="mt-5">
            <div className="mb-4">
                <h2 className="text-lg font-bold text-slate-900" id="crown-parity-title">
                    Crown geometry parity
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                    Same Dentix crown paths before and after normalized FDI lookup.
                </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2" dir="ltr">
                <CrownSvg label="Current source · Universal 3" paths={source.CrownBox} testId="source-crown" />
                <CrownSvg label="Normalized lookup · FDI 16" paths={normalized.paths} testId="normalized-crown" />
            </div>
        </section>
    );
}
