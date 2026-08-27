import { memo, useId } from 'react';
import { toothToNumber } from '@/utils/toothUtils';
import { getMeasuredToothGeometry } from './odontogram/measuredToothGeometry';

const CONDITION_META = {
    Healthy: { label: 'سليم' },
    Decayed: { label: 'تسوس' },
    Filled: { label: 'حشو' },
    Missing: { label: 'سن مفقود' },
    Crown: { label: 'تاج' },
    RootCanal: { label: 'علاج عصب' },
};

const ADULT_UPPER = Array.from({ length: 16 }, (_, index) => index + 1);
const ADULT_LOWER = [32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17];
const PRIMARY_UPPER = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'];
const PRIMARY_LOWER = ['T', 'S', 'R', 'Q', 'P', 'O', 'N', 'M', 'L', 'K'];

const normalizeCondition = (value) => {
    const normalized = String(value || 'Healthy').toLowerCase().replace(/[^a-z]/g, '');

    if (normalized === 'decayed' || normalized === 'caries') return 'Decayed';
    if (normalized === 'filled' || normalized === 'filling' || normalized === 'restored') return 'Filled';
    if (normalized === 'missing' || normalized === 'extracted') return 'Missing';
    if (normalized === 'crown' || normalized === 'crowned') return 'Crown';
    if (normalized === 'rootcanal' || normalized === 'rct' || normalized === 'endo') return 'RootCanal';

    return 'Healthy';
};

const getCanalXs = (rootCount, width) => {
    if (rootCount >= 3) return [width * 0.27, width * 0.5, width * 0.73];
    if (rootCount === 2) return [width * 0.35, width * 0.65];
    return [width * 0.5];
};

const ClinicalOverlay = memo(function ClinicalOverlay({ condition, geometry, clipId, crownGradientId }) {
    const { width, height, cej, roots } = geometry;
    const crownDepth = Math.max(height - cej, 8);
    const crownMidY = cej + crownDepth * 0.58;

    if (condition === 'Missing') {
        return (
            <>
                <path
                    d={geometry.base}
                    fill="rgba(248,250,252,0.28)"
                    stroke="#94a3b8"
                    strokeWidth="1.15"
                    strokeDasharray="2.8 2.8"
                    vectorEffect="non-scaling-stroke"
                />
                <g clipPath={`url(#${clipId})`} opacity="0.78">
                    <path
                        d={`M${width * 0.23} ${cej + crownDepth * 0.22} L${width * 0.77} ${cej + crownDepth * 0.82}`}
                        stroke="#64748b"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                    />
                    <path
                        d={`M${width * 0.77} ${cej + crownDepth * 0.22} L${width * 0.23} ${cej + crownDepth * 0.82}`}
                        stroke="#64748b"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                    />
                </g>
            </>
        );
    }

    if (condition === 'Crown') {
        return (
            <g clipPath={`url(#${clipId})`}>
                <rect
                    x="-2"
                    y={cej - 1.4}
                    width={width + 4}
                    height={crownDepth + 4}
                    fill={`url(#${crownGradientId})`}
                />
                <line
                    x1={width * 0.08}
                    x2={width * 0.92}
                    y1={cej + 0.35}
                    y2={cej + 0.35}
                    stroke="#9a670f"
                    strokeWidth="1.25"
                    vectorEffect="non-scaling-stroke"
                    opacity="0.78"
                />
            </g>
        );
    }

    if (condition === 'Decayed') {
        return (
            <g clipPath={`url(#${clipId})`}>
                <ellipse
                    cx={width * 0.64}
                    cy={crownMidY}
                    rx={Math.max(width * 0.16, 3.4)}
                    ry={Math.max(crownDepth * 0.2, 2.8)}
                    fill="#b42318"
                    opacity="0.9"
                />
                <ellipse
                    cx={width * 0.66}
                    cy={crownMidY - 0.5}
                    rx={Math.max(width * 0.085, 1.8)}
                    ry={Math.max(crownDepth * 0.105, 1.4)}
                    fill="#7f1d1d"
                    opacity="0.68"
                />
            </g>
        );
    }

    if (condition === 'Filled') {
        return (
            <g clipPath={`url(#${clipId})`}>
                <path
                    d={`M${width * 0.27} ${cej + crownDepth * 0.34}
                        Q${width * 0.5} ${cej + crownDepth * 0.18} ${width * 0.72} ${cej + crownDepth * 0.36}
                        L${width * 0.67} ${cej + crownDepth * 0.68}
                        Q${width * 0.5} ${cej + crownDepth * 0.79} ${width * 0.31} ${cej + crownDepth * 0.66} Z`}
                    fill="#2563eb"
                    fillOpacity="0.8"
                    stroke="#1d4ed8"
                    strokeWidth="1.15"
                    vectorEffect="non-scaling-stroke"
                />
                <path
                    d={`M${width * 0.34} ${cej + crownDepth * 0.43} Q${width * 0.5} ${cej + crownDepth * 0.34} ${width * 0.64} ${cej + crownDepth * 0.45}`}
                    fill="none"
                    stroke="#dbeafe"
                    strokeWidth="0.9"
                    vectorEffect="non-scaling-stroke"
                    opacity="0.85"
                />
            </g>
        );
    }

    if (condition === 'RootCanal') {
        const canalXs = getCanalXs(roots, width);
        const chamberY = cej + crownDepth * 0.42;

        return (
            <g clipPath={`url(#${clipId})`}>
                <ellipse
                    cx={width * 0.5}
                    cy={chamberY}
                    rx={Math.max(width * 0.14, 2.8)}
                    ry={Math.max(crownDepth * 0.12, 1.9)}
                    fill="#7c3aed"
                    fillOpacity="0.2"
                    stroke="#6d28d9"
                    strokeWidth="1"
                    vectorEffect="non-scaling-stroke"
                />
                {canalXs.map((x, index) => {
                    const apexX = roots === 1 ? width * 0.5 : x + (index - (canalXs.length - 1) / 2) * width * 0.025;
                    return (
                        <path
                            key={`${x}-${index}`}
                            d={`M${width * 0.5} ${chamberY} Q${x} ${cej * 0.62} ${apexX} ${Math.max(height * 0.075, 3)}`}
                            fill="none"
                            stroke="#7c3aed"
                            strokeWidth="1.75"
                            strokeLinecap="round"
                            vectorEffect="non-scaling-stroke"
                            opacity="0.92"
                        />
                    );
                })}
            </g>
        );
    }

    return null;
});

const ClinicalTooth = memo(function ClinicalTooth({ number, status, onClick, isPediatric, isUpper }) {
    const rawId = useId();
    const uid = rawId.replace(/:/g, '');
    const fdi = toothToNumber(number);
    const condition = normalizeCondition(status?.condition);
    const meta = CONDITION_META[condition];
    const geometry = getMeasuredToothGeometry(fdi, isPediatric);

    const enamelGradientId = `dentix-enamel-${uid}`;
    const crownGradientId = `dentix-crown-${uid}`;
    const clipId = `dentix-tooth-clip-${uid}`;

    const targetWidth = isPediatric ? 40 : 46;
    const targetHeight = isPediatric ? 76 : 86;
    const scale = Math.min(
        targetWidth / (geometry.width * geometry.scaleX),
        targetHeight / (geometry.height * geometry.scaleY),
    );
    const renderedWidth = geometry.width * geometry.scaleX * scale;
    const renderedHeight = geometry.height * geometry.scaleY * scale;
    const offsetX = (64 - renderedWidth) / 2;
    const offsetY = (100 - renderedHeight) / 2;
    const innerScaleX = geometry.scaleX * scale;
    const innerScaleY = geometry.scaleY * scale;

    const canonicalArtwork = (
        <g transform={`translate(${offsetX} ${offsetY}) scale(${innerScaleX} ${innerScaleY})`}>
            <g transform={geometry.mirror ? `translate(${geometry.width} 0) scale(-1 1)` : undefined}>
                <defs>
                    <linearGradient id={enamelGradientId} x1="0" x2="0.8" y1="0" y2="1">
                        <stop offset="0%" stopColor="#f8f4eb" />
                        <stop offset="52%" stopColor="#fffdf8" />
                        <stop offset="100%" stopColor="#e7dfd0" />
                    </linearGradient>
                    <linearGradient id={crownGradientId} x1="0" x2="0.9" y1="0" y2="1">
                        <stop offset="0%" stopColor="#f8e29a" />
                        <stop offset="52%" stopColor="#d8ad49" />
                        <stop offset="100%" stopColor="#a46f18" />
                    </linearGradient>
                    <clipPath id={clipId}>
                        <path d={geometry.base} />
                    </clipPath>
                </defs>

                {condition !== 'Missing' && (
                    <>
                        <path
                            d={geometry.base}
                            fill={`url(#${enamelGradientId})`}
                            stroke="#98a2ad"
                            strokeWidth="1.15"
                            vectorEffect="non-scaling-stroke"
                        />
                        <line
                            x1={geometry.width * 0.1}
                            x2={geometry.width * 0.9}
                            y1={geometry.cej}
                            y2={geometry.cej}
                            clipPath={`url(#${clipId})`}
                            stroke="#c9bda9"
                            strokeWidth="0.8"
                            vectorEffect="non-scaling-stroke"
                            opacity="0.58"
                        />
                    </>
                )}

                <ClinicalOverlay
                    condition={condition}
                    geometry={geometry}
                    clipId={clipId}
                    crownGradientId={crownGradientId}
                />
            </g>
        </g>
    );

    return (
        <button
            type="button"
            onClick={() => onClick?.(number)}
            className="group relative flex w-[50px] shrink-0 flex-col items-center rounded-lg px-0.5 py-0.5 transition-colors hover:bg-white/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-1 dark:hover:bg-slate-800/50 sm:w-[53px]"
            aria-label={`Tooth ${fdi} — ${meta.label}`}
            data-tooth={fdi}
            data-condition={condition}
            data-template-id={geometry.templateId}
        >
            {isUpper && (
                <span className="mb-0.5 font-mono text-[10px] font-semibold leading-none text-slate-500 dark:text-slate-400">
                    {fdi}
                </span>
            )}

            <svg
                width="64"
                height="100"
                viewBox="0 0 64 100"
                className="h-[88px] w-[48px] overflow-visible transition-transform duration-150 group-hover:scale-[1.035] sm:h-[94px] sm:w-[51px]"
                aria-hidden="true"
            >
                <g transform={isUpper ? undefined : 'translate(0 100) scale(1 -1)'}>
                    {canonicalArtwork}
                </g>
            </svg>

            {!isUpper && (
                <span className="mt-0.5 font-mono text-[10px] font-semibold leading-none text-slate-500 dark:text-slate-400">
                    {fdi}
                </span>
            )}
        </button>
    );
});

const ChartRow = memo(function ChartRow({ numbers, teethStatus, onToothClick, isPediatric, isUpper }) {
    return (
        <div className="relative flex justify-center gap-0 px-2 sm:gap-0.5 sm:px-3">
            <div
                className="pointer-events-none absolute inset-y-2 start-1/2 z-0 w-px bg-slate-300/60 dark:bg-slate-600/70"
                aria-hidden="true"
            />
            {numbers.map((number) => {
                const fdi = toothToNumber(number);
                return (
                    <ClinicalTooth
                        key={number}
                        number={number}
                        status={teethStatus[fdi]}
                        onClick={onToothClick}
                        isPediatric={isPediatric}
                        isUpper={isUpper}
                    />
                );
            })}
        </div>
    );
});

export default memo(function DentalChartSVG({ teethStatus = {}, onToothClick, isPediatric = false }) {
    const upper = isPediatric ? PRIMARY_UPPER : ADULT_UPPER;
    const lower = isPediatric ? PRIMARY_LOWER : ADULT_LOWER;
    const minWidth = isPediatric ? 'min-w-[560px]' : 'min-w-[860px]';

    return (
        <div className="min-w-0 overflow-hidden rounded-2xl bg-slate-50/80 dark:bg-slate-900/50">
            <div className="min-w-0 overflow-x-auto overscroll-x-contain touch-pan-x">
                <div className={`${minWidth} mx-auto px-2 py-4 sm:px-3 sm:py-5`} dir="ltr">
                    <ChartRow
                        numbers={upper}
                        teethStatus={teethStatus}
                        onToothClick={onToothClick}
                        isPediatric={isPediatric}
                        isUpper
                    />

                    <div className="relative my-2.5 h-px bg-slate-300/65 dark:bg-slate-600/70 sm:my-3" aria-hidden="true">
                        <span className="absolute start-1/2 top-1/2 h-3 w-px -translate-y-1/2 bg-slate-400/80 dark:bg-slate-500" />
                    </div>

                    <ChartRow
                        numbers={lower}
                        teethStatus={teethStatus}
                        onToothClick={onToothClick}
                        isPediatric={isPediatric}
                        isUpper={false}
                    />
                </div>
            </div>
        </div>
    );
});
