import { getCrownGeometry } from '../rendering/crownGeometry';
import { getRootGeometry } from '../rendering/rootGeometry';

const DEMO_TEETH = Object.freeze(['11', '14', '16', '75']);

function AnatomyTooth({ toothKey }) {
    const crown = getCrownGeometry(toothKey);
    const roots = getRootGeometry(toothKey);
    const isPrimary = crown.source === 'dental-chart-svg-primary-family';
    const isMaxillary = Number(toothKey[0]) <= 2 || [5, 6].includes(Number(toothKey[0]));
    const primaryCrownTransform = isMaxillary ? 'translate(20 88) scale(1.2)' : 'translate(20 0) scale(1.2)';
    const mirrorTransform = crown.isMirror ? 'translate(100 0) scale(-1 1)' : undefined;

    return (
        <figure className="rounded-xl border border-slate-200 bg-white p-3 text-center">
            <svg
                aria-label={`تشريح السن ${toothKey}`}
                className="mx-auto h-52 w-32 overflow-visible drop-shadow-sm"
                data-root-count={roots.length}
                data-testid={`anatomy-tooth-${toothKey}`}
                role="img"
                viewBox="0 0 100 160"
            >
                <g transform={mirrorTransform}>
                    <g data-layer="roots">
                        {roots.map((root) => (
                            <path
                                d={root.path}
                                fill={root.style.fill}
                                key={root.outlineRef}
                                stroke={root.style.stroke}
                                strokeLinejoin="round"
                                strokeWidth={root.style.strokeWidth}
                            />
                        ))}
                    </g>
                    <g data-layer="crown" transform={isPrimary ? primaryCrownTransform : undefined}>
                        {Object.entries(crown.paths).map(([surface, path]) => (
                            <path
                                d={path}
                                fill={crown.style.fill}
                                key={surface}
                                stroke={crown.style.stroke}
                                strokeWidth={crown.style.strokeWidth}
                            />
                        ))}
                    </g>
                </g>
            </svg>
            <figcaption className="mt-2 font-mono text-sm font-bold text-slate-600" dir="ltr">
                FDI {toothKey}
            </figcaption>
        </figure>
    );
}

export default function RootAnatomyPreview() {
    return (
        <section aria-labelledby="root-preview-title" className="mt-6">
            <h2 className="text-lg font-bold text-slate-900" id="root-preview-title">Root anatomy families</h2>
            <p className="mt-1 text-sm text-slate-500">جذور برمجية متوافقة مع نفس خطوط وتناسب التاج الحالي.</p>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4" dir="ltr">
                {DEMO_TEETH.map((toothKey) => <AnatomyTooth key={toothKey} toothKey={toothKey} />)}
            </div>
        </section>
    );
}
