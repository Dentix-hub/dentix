import { memo, useId } from 'react';
import { toothToNumber } from '@/utils/toothUtils';

const PROCEDURE_META = {
    Healthy: { label: 'سليم', color: '#94a3b8' },
    Decayed: { label: 'تسوس', color: '#b42318' },
    Filled: { label: 'حشو', color: '#2563eb' },
    Missing: { label: 'سن مفقود', color: '#64748b' },
    Crown: { label: 'تاج', color: '#b7791f' },
    RootCanal: { label: 'علاج عصب', color: '#7c3aed' },
};

const ADULT_UPPER = Array.from({ length: 16 }, (_, index) => index + 1);
const ADULT_LOWER = [32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17];
const PRIMARY_UPPER = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'];
const PRIMARY_LOWER = ['T', 'S', 'R', 'Q', 'P', 'O', 'N', 'M', 'L', 'K'];

const CROWN_PATHS = {
    incisor: 'M18 10 C21 6 27 5 32 6 C37 5 43 6 46 10 C47 19 47 29 44 38 C40 43 36 45 32 45 C28 45 24 43 20 38 C17 29 17 19 18 10 Z',
    canine: 'M18 12 C22 9 27 8 32 3 C37 8 42 9 46 12 C48 22 47 31 44 39 C40 44 36 46 32 47 C28 46 24 44 20 39 C17 31 16 22 18 12 Z',
    premolar: 'M14 13 C18 7 24 6 31 9 C38 5 45 8 50 13 C52 22 51 32 47 41 C43 46 38 48 32 48 C26 48 21 46 17 41 C13 32 12 22 14 13 Z',
    molar: 'M9 14 C12 8 18 6 24 8 C29 4 35 5 39 8 C45 5 51 8 55 13 C58 20 56 27 55 32 C57 39 53 46 47 49 C41 52 36 51 32 49 C27 52 21 52 15 48 C9 44 7 37 9 31 C6 25 6 19 9 14 Z',
};

const FISSURE_PATHS = {
    incisor: 'M22 18 C27 20 37 20 42 18',
    canine: 'M23 20 C28 18 30 15 32 12 C34 15 36 18 41 20',
    premolar: 'M20 20 C24 25 27 27 32 24 C37 27 40 24 44 20 M32 16 L32 38',
    molar: 'M17 20 C22 24 25 28 31 25 C36 29 40 25 47 20 M18 36 C24 31 27 32 32 36 C37 31 41 32 48 36 M32 18 L32 42',
};

const normalizeCondition = (value) => {
    const normalized = String(value || 'Healthy').toLowerCase().replace(/[^a-z]/g, '');
    if (normalized === 'decayed' || normalized === 'caries') return 'Decayed';
    if (normalized === 'filled' || normalized === 'filling' || normalized === 'restored') return 'Filled';
    if (normalized === 'missing' || normalized === 'extracted') return 'Missing';
    if (normalized === 'crown' || normalized === 'crowned') return 'Crown';
    if (normalized === 'rootcanal' || normalized === 'rct' || normalized === 'endo') return 'RootCanal';
    return 'Healthy';
};

const getToothKind = (fdi, isPediatric) => {
    const position = Number(fdi) % 10;
    if (position <= 2) return 'incisor';
    if (position === 3) return 'canine';
    if (isPediatric) return 'molar';
    if (position <= 5) return 'premolar';
    return 'molar';
};

const getRootPaths = ({ kind, isUpper, fdi, isPediatric }) => {
    if (kind === 'incisor') {
        return ['M23 43 C23 58 24 78 27 99 C28 106 35 108 37 99 C40 78 41 58 41 43 C35 46 29 46 23 43 Z'];
    }
    if (kind === 'canine') {
        return ['M22 44 C21 61 23 83 28 104 C29 111 35 112 37 104 C42 82 43 61 42 44 C35 47 29 47 22 44 Z'];
    }
    if (kind === 'premolar') {
        const firstPremolar = Number(fdi) % 10 === 4;
        if (isUpper && firstPremolar) {
            return [
                'M20 43 C20 60 18 80 20 100 C21 107 26 109 29 101 C31 83 31 62 30 45 C26 46 23 45 20 43 Z',
                'M34 45 C33 62 34 83 36 101 C38 109 43 108 44 100 C46 80 44 60 44 43 C41 45 38 46 34 45 Z',
            ];
        }
        return ['M21 44 C21 62 23 83 27 101 C28 108 35 109 37 101 C41 83 43 62 43 44 C36 47 28 47 21 44 Z'];
    }

    if (isUpper) {
        return [
            'M15 43 C14 57 11 74 12 91 C13 99 18 102 22 95 C26 79 27 61 27 46 C23 47 19 46 15 43 Z',
            'M27 46 C27 62 28 83 30 103 C31 111 36 112 38 103 C40 82 40 62 39 46 C35 48 31 48 27 46 Z',
            'M39 46 C39 61 40 79 44 95 C47 102 52 99 52 91 C53 74 50 57 49 43 C45 46 43 47 39 46 Z',
        ];
    }

    if (isPediatric) {
        return [
            'M15 43 C14 58 11 76 13 94 C14 101 20 103 23 96 C27 80 28 61 27 46 C23 47 19 46 15 43 Z',
            'M37 46 C36 61 37 80 41 96 C44 103 50 101 51 94 C53 76 50 58 49 43 C45 46 42 47 37 46 Z',
        ];
    }

    return [
        'M15 43 C14 58 12 77 14 96 C15 104 21 106 24 98 C28 80 29 61 28 46 C23 47 19 46 15 43 Z',
        'M36 46 C35 61 36 80 40 98 C43 106 49 104 50 96 C52 77 50 58 49 43 C45 46 41 47 36 46 Z',
    ];
};

const getCanalPaths = ({ kind, rootCount }) => {
    if (kind === 'incisor' || kind === 'canine') {
        return ['M32 34 C32 53 32 75 32 99'];
    }
    if (kind === 'premolar' && rootCount === 2) {
        return ['M27 35 C25 53 24 76 24 100', 'M37 35 C39 53 40 76 40 100'];
    }
    if (kind === 'premolar') {
        return ['M32 34 C32 55 32 78 32 101'];
    }
    if (rootCount === 3) {
        return ['M22 35 C20 52 18 72 18 94', 'M32 34 C32 55 33 79 34 103', 'M42 35 C45 52 47 72 47 94'];
    }
    return ['M23 35 C21 54 20 76 20 98', 'M41 35 C43 54 44 76 44 98'];
};

const RestorationOverlay = ({ condition, crownPath, clipId, enamelId, crownId }) => {
    if (condition === 'Decayed') {
        return (
            <g clipPath={`url(#${clipId})`}>
                <path
                    d="M34 22 C40 17 48 19 51 25 C52 31 48 37 42 38 C37 36 33 31 34 22 Z"
                    fill="#b42318"
                    opacity="0.92"
                />
                <path
                    d="M38 24 C42 21 47 22 49 26 C49 30 46 33 42 34 C39 32 37 29 38 24 Z"
                    fill="#7f1d1d"
                    opacity="0.62"
                />
            </g>
        );
    }

    if (condition === 'Filled') {
        return (
            <g clipPath={`url(#${clipId})`}>
                <path
                    d="M20 24 C24 19 29 19 32 23 C36 19 42 20 46 24 L45 34 C41 38 36 37 32 34 C28 38 23 37 19 33 Z"
                    fill="#2563eb"
                    fillOpacity="0.82"
                    stroke="#1d4ed8"
                    strokeWidth="1.3"
                />
                <path d="M23 27 C28 29 36 29 42 26" fill="none" stroke="#dbeafe" strokeWidth="1" opacity="0.7" />
            </g>
        );
    }

    if (condition === 'Crown') {
        return (
            <>
                <path d={crownPath} fill={`url(#${crownId})`} stroke="#a16207" strokeWidth="1.7" />
                <path d="M17 39 C25 44 39 45 47 39" fill="none" stroke="#8a5a16" strokeWidth="1" opacity="0.7" />
            </>
        );
    }

    return <path d={crownPath} fill={`url(#${enamelId})`} stroke="#9aa7b5" strokeWidth="1.35" />;
};

const ClinicalTooth = memo(function ClinicalTooth({ number, status, onClick, isPediatric, isUpper }) {
    const rawId = useId();
    const uid = rawId.replace(/:/g, '');
    const fdi = toothToNumber(number);
    const kind = getToothKind(fdi, isPediatric);
    const condition = normalizeCondition(status?.condition);
    const crownPath = CROWN_PATHS[kind];
    const rootPaths = getRootPaths({ kind, isUpper, fdi, isPediatric });
    const canalPaths = getCanalPaths({ kind, rootCount: rootPaths.length });
    const isMissing = condition === 'Missing';
    const meta = PROCEDURE_META[condition];

    const enamelId = `dentix-enamel-${uid}`;
    const rootId = `dentix-root-${uid}`;
    const crownId = `dentix-crown-${uid}`;
    const clipId = `dentix-crown-clip-${uid}`;

    const artwork = (
        <g transform={isUpper ? 'translate(0 112) scale(1 -1)' : undefined}>
            <defs>
                <linearGradient id={enamelId} x1="0" x2="1" y1="0" y2="1">
                    <stop offset="0%" stopColor="#fffefa" />
                    <stop offset="58%" stopColor="#f5f1e8" />
                    <stop offset="100%" stopColor="#e7dfd0" />
                </linearGradient>
                <linearGradient id={rootId} x1="0" x2="1" y1="0" y2="1">
                    <stop offset="0%" stopColor="#fbf8ef" />
                    <stop offset="62%" stopColor="#eee6d7" />
                    <stop offset="100%" stopColor="#d9cdb9" />
                </linearGradient>
                <linearGradient id={crownId} x1="0" x2="1" y1="0" y2="1">
                    <stop offset="0%" stopColor="#f8df8b" />
                    <stop offset="45%" stopColor="#d7aa3c" />
                    <stop offset="100%" stopColor="#9b6816" />
                </linearGradient>
                <clipPath id={clipId}>
                    <path d={crownPath} />
                </clipPath>
            </defs>

            {rootPaths.map((path, index) => (
                <path
                    key={path}
                    d={path}
                    fill={isMissing ? 'none' : `url(#${rootId})`}
                    stroke={isMissing ? '#94a3b8' : '#a9a093'}
                    strokeWidth="1.25"
                    strokeDasharray={isMissing ? '3 3' : undefined}
                    opacity={isMissing ? 0.42 : 1}
                />
            ))}

            {isMissing ? (
                <>
                    <path
                        d={crownPath}
                        fill="none"
                        stroke="#94a3b8"
                        strokeWidth="1.4"
                        strokeDasharray="3 3"
                        opacity="0.48"
                    />
                    <path d="M19 17 L45 42 M45 17 L19 42" stroke="#64748b" strokeWidth="2" strokeLinecap="round" opacity="0.62" />
                </>
            ) : (
                <>
                    <RestorationOverlay condition={condition} crownPath={crownPath} clipId={clipId} enamelId={enamelId} crownId={crownId} />
                    <path
                        d={FISSURE_PATHS[kind]}
                        fill="none"
                        stroke={condition === 'Crown' ? '#8a5a16' : '#a9a093'}
                        strokeWidth="0.9"
                        strokeLinecap="round"
                        opacity={condition === 'Filled' || condition === 'Decayed' ? 0.48 : 0.65}
                    />
                    <path d="M22 42 C27 44 37 44 42 42" fill="none" stroke="#c8bba8" strokeWidth="0.9" opacity="0.7" />
                </>
            )}

            {condition === 'RootCanal' && !isMissing && (
                <>
                    <path
                        d="M24 29 C26 25 29 24 32 26 C35 24 38 25 40 29 L39 37 C36 40 28 40 25 37 Z"
                        fill="#7c3aed"
                        fillOpacity="0.18"
                        stroke="#6d28d9"
                        strokeWidth="1.2"
                    />
                    {canalPaths.map((path) => (
                        <path
                            key={path}
                            d={path}
                            fill="none"
                            stroke="#7c3aed"
                            strokeWidth="2.15"
                            strokeLinecap="round"
                            opacity="0.92"
                        />
                    ))}
                </>
            )}
        </g>
    );

    return (
        <button
            type="button"
            onClick={() => onClick(number)}
            className="group relative flex w-[56px] shrink-0 flex-col items-center rounded-xl px-0.5 py-1 transition-colors hover:bg-white/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 dark:hover:bg-slate-800/60 sm:w-[60px]"
            aria-label={`Tooth ${fdi} — ${meta.label}`}
            data-tooth={fdi}
            data-condition={condition}
        >
            {isUpper && <span className="mb-1 font-mono text-[11px] font-bold text-slate-600 dark:text-slate-300">{fdi}</span>}
            <svg
                width="64"
                height="112"
                viewBox="0 0 64 112"
                className="h-[96px] w-[55px] overflow-visible transition-transform duration-150 group-hover:scale-[1.035] sm:h-[104px] sm:w-[58px]"
                aria-hidden="true"
            >
                {artwork}
            </svg>
            {!isUpper && <span className="mt-1 font-mono text-[11px] font-bold text-slate-600 dark:text-slate-300">{fdi}</span>}
        </button>
    );
});

const ChartRow = memo(function ChartRow({ numbers, teethStatus, onToothClick, isPediatric, isUpper }) {
    return (
        <div className="relative flex justify-center gap-0.5 px-3 sm:gap-1 sm:px-5">
            <div className="absolute inset-y-2 start-1/2 z-0 w-px bg-slate-300/80 dark:bg-slate-600" aria-hidden="true" />
            {numbers.map((number, index) => (
                <ClinicalTooth
                    key={number}
                    number={number}
                    status={teethStatus[toothToNumber(number)]}
                    onClick={onToothClick}
                    isPediatric={isPediatric}
                    isUpper={isUpper}
                />
            ))}
        </div>
    );
});

export default memo(function DentalChartSVG({ teethStatus = {}, onToothClick, isPediatric }) {
    const upper = isPediatric ? PRIMARY_UPPER : ADULT_UPPER;
    const lower = isPediatric ? PRIMARY_LOWER : ADULT_LOWER;
    const minWidth = isPediatric ? 'min-w-[660px]' : 'min-w-[1020px]';

    return (
        <div className="min-w-0 overflow-hidden rounded-2xl border border-slate-200/80 bg-gradient-to-b from-slate-50 to-white shadow-sm dark:border-slate-700 dark:from-slate-900 dark:to-slate-900 sm:rounded-3xl">
            <div className="flex items-center justify-between gap-3 border-b border-slate-200/70 px-3 py-2.5 dark:border-slate-700 sm:px-5 sm:py-3">
                <div className="min-w-0">
                    <p className="text-sm font-bold text-slate-800 dark:text-white">
                        {isPediatric ? 'الأسنان اللبنية' : 'الأسنان الدائمة'}
                    </p>
                    <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">ترقيم FDI · اضغط على السن لإضافة أو تعديل العلاج</p>
                </div>
                <span className="shrink-0 rounded-full border border-slate-200 bg-white px-2.5 py-1 font-mono text-[10px] font-bold text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    FDI
                </span>
            </div>

            <div className="min-w-0 overflow-x-auto overscroll-x-contain touch-pan-x">
                <div className={`${minWidth} mx-auto px-2 py-4 sm:px-4 sm:py-5`} dir="ltr">
                    <ChartRow
                        numbers={upper}
                        teethStatus={teethStatus}
                        onToothClick={onToothClick}
                        isPediatric={isPediatric}
                        isUpper
                    />

                    <div className="relative my-3 h-px bg-slate-300/90 dark:bg-slate-600 sm:my-4" aria-hidden="true">
                        <span className="absolute start-1/2 top-1/2 h-4 w-px -translate-y-1/2 bg-slate-400 dark:bg-slate-500" />
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

            <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 border-t border-slate-200/70 bg-white/70 px-3 py-3 text-[11px] dark:border-slate-700 dark:bg-slate-900/70 sm:gap-x-6 sm:px-5">
                {Object.entries(PROCEDURE_META)
                    .filter(([status]) => status !== 'Healthy')
                    .map(([status, meta]) => (
                        <span key={status} className="inline-flex items-center gap-1.5 font-medium text-slate-600 dark:text-slate-300">
                            <span
                                className={`h-2.5 w-2.5 shrink-0 ${status === 'Missing' ? 'rotate-45 border border-slate-500 bg-transparent' : 'rounded-full'}`}
                                style={status === 'Missing' ? undefined : { backgroundColor: meta.color }}
                                aria-hidden="true"
                            />
                            {meta.label}
                        </span>
                    ))}
            </div>
        </div>
    );
});
