import { memo, useId } from 'react';
import { getCrownGeometry } from '@/features/clinical-chart/rendering/crownGeometry';
import { ROOT_VIEW_BOX, getRootGeometry } from '@/features/clinical-chart/rendering/rootGeometry';
import { getSurfaceGeometry } from '@/features/clinical-chart/rendering/surfaceGeometry';
import {
    CrownVisualLayers,
    RootVisualLayers,
} from '@/features/clinical-chart/rendering/ClinicalToothVisualLayers';
import {
    getBaseAnatomyOpacity,
    shouldHideNaturalRoots,
} from '@/features/clinical-chart/rendering/visualInstructionSelectors';
import {
    DEFAULT_CHART_NOTATION_MODE,
    getChartNotationConfig,
    resolveToothNotation,
} from '@/features/clinical-chart/domain/chartNotation';
import { toothToNumber } from '@/utils/toothUtils';

const TOOTH_PATHS = {
    upperMolarRight: "M10,5 C15,0 35,0 40,5 C45,15 45,35 40,45 C35,50 15,50 10,45 C5,35 5,15 10,5 Z M15,15 L20,20 M30,15 L25,20 M25,25 L25,35",
    upperPremolarRight: "M12,8 C17,3 33,3 38,8 C42,15 42,30 38,40 C33,45 17,45 12,40 C8,30 8,15 12,8 Z M25,15 L25,30",
    upperCanineRight: "M15,10 C20,5 30,5 35,10 C40,20 35,40 25,48 C15,40 10,20 15,10 Z",
    upperIncisorRight: "M10,10 C15,8 35,8 40,10 C42,20 40,40 35,45 C30,48 20,48 15,45 C10,40 8,20 10,10 Z",
    upperIncisorLeft: "M10,10 C15,8 35,8 40,10 C42,20 40,40 35,45 C30,48 20,48 15,45 C10,40 8,20 10,10 Z",
    upperCanineLeft: "M15,10 C20,5 30,5 35,10 C40,20 35,40 25,48 C15,40 10,20 15,10 Z",
    upperPremolarLeft: "M12,8 C17,3 33,3 38,8 C42,15 42,30 38,40 C33,45 17,45 12,40 C8,30 8,15 12,8 Z M25,15 L25,30",
    upperMolarLeft: "M10,5 C15,0 35,0 40,5 C45,15 45,35 40,45 C35,50 15,50 10,45 C5,35 5,15 10,5 Z M15,15 L20,20 M30,15 L25,20 M25,25 L25,35",
    lowerMolar: "M10,5 C15,0 35,0 40,5 C45,15 45,35 40,45 C35,50 15,50 10,45 C5,35 5,15 10,5 Z M15,15 L20,20 M30,15 L25,20 M25,25 L25,35",
    lowerPremolar: "M12,8 C17,3 33,3 38,8 C42,15 42,30 38,40 C33,45 17,45 12,40 C8,30 8,15 12,8 Z M25,15 L25,30",
    lowerCanine: "M15,10 C20,5 30,5 35,10 C40,20 35,40 25,48 C15,40 10,20 15,10 Z",
    lowerIncisor: "M15,12 C18,10 32,10 35,12 C36,20 35,35 32,40 C28,42 22,42 18,40 C15,35 14,20 15,12 Z",
};

const getToothPath = (id, isPediatric) => {
    if (isPediatric) {
        switch (id) {
            case 'A': return TOOTH_PATHS.upperMolarRight;
            case 'B': return TOOTH_PATHS.upperMolarRight;
            case 'C': return TOOTH_PATHS.upperCanineRight;
            case 'D': return TOOTH_PATHS.upperIncisorRight;
            case 'E': return TOOTH_PATHS.upperIncisorRight;
            case 'F': return TOOTH_PATHS.upperIncisorLeft;
            case 'G': return TOOTH_PATHS.upperIncisorLeft;
            case 'H': return TOOTH_PATHS.upperCanineLeft;
            case 'I': return TOOTH_PATHS.upperMolarLeft;
            case 'J': return TOOTH_PATHS.upperMolarLeft;
            case 'K': return TOOTH_PATHS.lowerMolar;
            case 'L': return TOOTH_PATHS.lowerMolar;
            case 'M': return TOOTH_PATHS.lowerCanine;
            case 'N': return TOOTH_PATHS.lowerIncisor;
            case 'O': return TOOTH_PATHS.lowerIncisor;
            case 'P': return TOOTH_PATHS.lowerIncisor;
            case 'Q': return TOOTH_PATHS.lowerIncisor;
            case 'R': return TOOTH_PATHS.lowerCanine;
            case 'S': return TOOTH_PATHS.lowerMolar;
            case 'T': return TOOTH_PATHS.lowerMolar;
            default: return TOOTH_PATHS.upperMolarRight;
        }
    }
    const number = parseInt(id, 10);
    if (number >= 1 && number <= 3) return TOOTH_PATHS.upperMolarRight;
    if (number >= 4 && number <= 5) return TOOTH_PATHS.upperPremolarRight;
    if (number === 6) return TOOTH_PATHS.upperCanineRight;
    if (number >= 7 && number <= 8) return TOOTH_PATHS.upperIncisorRight;
    if (number >= 9 && number <= 10) return TOOTH_PATHS.upperIncisorLeft;
    if (number === 11) return TOOTH_PATHS.upperCanineLeft;
    if (number >= 12 && number <= 13) return TOOTH_PATHS.upperPremolarLeft;
    if (number >= 14 && number <= 16) return TOOTH_PATHS.upperMolarLeft;
    if (number >= 17 && number <= 19) return TOOTH_PATHS.lowerMolar;
    if (number >= 20 && number <= 21) return TOOTH_PATHS.lowerPremolar;
    if (number === 22) return TOOTH_PATHS.lowerCanine;
    if (number >= 23 && number <= 26) return TOOTH_PATHS.lowerIncisor;
    if (number === 27) return TOOTH_PATHS.lowerCanine;
    if (number >= 28 && number <= 29) return TOOTH_PATHS.lowerPremolar;
    if (number >= 30 && number <= 32) return TOOTH_PATHS.lowerMolar;
    return TOOTH_PATHS.upperMolarRight;
};

const STATUS_STYLES = {
    Healthy: { fill: '#ffffff', stroke: '#94a3b8' },
    Decayed: { fill: '#fecaca', stroke: '#ef4444' },
    Filled: { fill: '#bfdbfe', stroke: '#3b82f6' },
    Missing: { fill: '#f1f5f9', stroke: '#e2e8f0', opacity: 0.3 },
    Crown: { fill: '#fef08a', stroke: '#eab308' },
    RootCanal: { fill: '#e9d5ff', stroke: '#a855f7' },
};
const ADULT_LAYOUT = Object.freeze({
    upperLeft: Object.freeze([16, 15, 14, 13, 12, 11, 10, 9]),
    upperRight: Object.freeze([8, 7, 6, 5, 4, 3, 2, 1]),
    lowerLeft: Object.freeze([17, 18, 19, 20, 21, 22, 23, 24]),
    lowerRight: Object.freeze([25, 26, 27, 28, 29, 30, 31, 32]),
});

const PRIMARY_LAYOUT = Object.freeze({
    upperLeft: Object.freeze(['J', 'I', 'H', 'G', 'F']),
    upperRight: Object.freeze(['E', 'D', 'C', 'B', 'A']),
    lowerLeft: Object.freeze(['K', 'L', 'M', 'N', 'O']),
    lowerRight: Object.freeze(['P', 'Q', 'R', 'S', 'T']),
});

const SOURCE_IDS = Object.freeze([
    ...Object.values(ADULT_LAYOUT).flat(),
    ...Object.values(PRIMARY_LAYOUT).flat(),
]);

const SOURCE_ID_BY_TOOTH_KEY = Object.freeze(Object.fromEntries(
    SOURCE_IDS.map((sourceId) => [String(toothToNumber(sourceId)), sourceId]),
));

const createLayoutEntry = (sourceId) => Object.freeze({
    sourceId,
    toothKey: String(toothToNumber(sourceId)),
    isPediatric: typeof sourceId === 'string',
});

const createLegacyLayout = (isPediatric) => {
    const sourceLayout = isPediatric ? PRIMARY_LAYOUT : ADULT_LAYOUT;
    return Object.freeze(Object.fromEntries(Object.entries(sourceLayout).map(([quadrant, sourceIds]) => [
        quadrant,
        Object.freeze(sourceIds.map(createLayoutEntry)),
    ])));
};

const MIXED_LAYOUT_QUADRANTS = Object.freeze({
    upperLeft: Object.freeze(['2', '6']),
    upperRight: Object.freeze(['1', '5']),
    lowerLeft: Object.freeze(['3', '7']),
    lowerRight: Object.freeze(['4', '8']),
});

const createMixedLayout = (toothOrder) => Object.freeze(Object.fromEntries(
    Object.entries(MIXED_LAYOUT_QUADRANTS).map(([quadrant, quadrantCodes]) => [
        quadrant,
        Object.freeze(toothOrder
            .map(String)
            .filter((toothKey) => quadrantCodes.includes(toothKey[0]))
            .map((toothKey) => {
                const sourceId = SOURCE_ID_BY_TOOTH_KEY[toothKey];
                return Object.freeze({
                    sourceId,
                    toothKey,
                    isPediatric: typeof sourceId === 'string',
                });
            })),
    ]),
));

const ToothRootLayer = memo(function ToothRootLayer({ toothKey, arch, opacity, toothVisual }) {
    const roots = getRootGeometry(toothKey);
    const { x: rootScaleX, y: rootScaleY } = roots[0].displayScale;
    const rootScaleTransform = `translate(25 0) scale(${rootScaleX} ${rootScaleY}) translate(-25 0)`;
    const baseOpacity = shouldHideNaturalRoots(toothVisual)
        ? 0
        : getBaseAnatomyOpacity(toothVisual);

    return (
        <svg
            aria-hidden="true"
            className={`pointer-events-none absolute ${arch === 'upper' ? 'top-0' : 'bottom-0'}`}
            data-layer="roots"
            data-root-count={roots.length}
            data-tooth-key={toothKey}
            height="48"
            opacity={opacity}
            viewBox={ROOT_VIEW_BOX}
            width="50"
        >
            <g data-root-orientation="apical" transform={arch === 'upper' ? 'rotate(180 25 24)' : undefined}>
                <g data-root-scale={`${rootScaleX} ${rootScaleY}`} transform={rootScaleTransform}>
                    <g data-layer-index="0" data-layer-role="base-anatomy" opacity={baseOpacity}>
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
                    <RootVisualLayers roots={roots} toothVisual={toothVisual} />
                </g>
            </g>
        </svg>
    );
});

const ToothSurfaceLayer = memo(function ToothSurfaceLayer({
    toothKey,
    toothNumber,
    toothLabel,
    clipPathId,
    selectedSurfaceCode,
    onSurfaceClick,
    disabled,
}) {
    const geometry = getSurfaceGeometry(toothKey);

    const emitSelection = (event, surfaceCode) => {
        event.preventDefault();
        event.stopPropagation();
        if (disabled) return;
        onSurfaceClick?.({ toothKey, toothNumber, surfaceCode });
    };

    return (
        <g
            clipPath={`url(#${clipPathId})`}
            data-layer="surfaces"
            data-layer-index="5"
            data-layer-role="selection-focus"
            data-surface-model={geometry.model}
        >
            {geometry.surfaces.map((surface) => {
                const isSelected = selectedSurfaceCode === surface.surfaceCode;
                return (
                    <path
                        aria-label={`Tooth ${toothLabel} — ${surface.label} (${surface.surfaceCode})`}
                        aria-disabled={disabled}
                        aria-pressed={isSelected}
                        className={disabled
                            ? 'cursor-not-allowed fill-slate-100 stroke-slate-300 outline-none'
                            : (isSelected
                            ? 'cursor-pointer fill-blue-200 stroke-blue-600 outline-none transition-colors duration-150'
                            : 'cursor-pointer fill-transparent stroke-transparent outline-none transition-colors duration-150 hover:fill-blue-100 hover:stroke-blue-400 focus:fill-blue-100 focus:stroke-blue-500')}
                        d={surface.path}
                        data-region={surface.region}
                        data-surface-code={surface.surfaceCode}
                        key={surface.surfaceCode}
                        onClick={(event) => emitSelection(event, surface.surfaceCode)}
                        onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') emitSelection(event, surface.surfaceCode);
                        }}
                        role="button"
                        strokeLinejoin="round"
                        strokeWidth="1.25"
                        tabIndex={disabled ? -1 : 0}
                        vectorEffect="non-scaling-stroke"
                    />
                );
            })}
        </g>
    );
});

const SVGTooth = memo(function SVGTooth({
    number,
    toothKey: explicitToothKey,
    status,
    onClick,
    isPediatric,
    showRoots,
    arch,
    enableSurfaceSelection,
    selectedSurface,
    onSurfaceClick,
    readOnly,
    toothVisual,
    notationMode,
}) {
    const reactId = useId();
    const toothKey = explicitToothKey ?? String(toothToNumber(number));
    const crownGeometry = getCrownGeometry(toothKey);
    const isOrganic = crownGeometry?.source === 'dental-v3-organic';
    const legacyPath = getToothPath(number, isPediatric);
    const condition = status?.condition || 'Healthy';
    const style = STATUS_STYLES[condition];
    const disabled = Boolean(status?.disabled);
    const notation = resolveToothNotation({
        toothKey,
        notationMode,
    });
    const toothLabel = notation.label;
    const crownClipId = `dentix-crown-${reactId.replace(/:/g, '')}`;
    const crownBaseOpacity = getBaseAnatomyOpacity(toothVisual);
    const needsCrownClip = enableSurfaceSelection || (toothVisual?.instructions.length ?? 0) > 0;
    const organicTransform = isOrganic
        ? (arch === 'upper'
            ? `${crownGeometry.isMirror ? 'translate(25 0) scale(-1 1) translate(-25 0) ' : ''}translate(0 10) scale(0.5 0.70) translate(0 -85)`
            : `${crownGeometry.isMirror ? 'translate(25 0) scale(-1 1) translate(-25 0) ' : ''}translate(0 4) scale(0.5 0.62)`)
        : undefined;
    const crownClipPath = isOrganic
        ? Object.values(crownGeometry.paths).join(' ')
        : (crownGeometry?.paths?.outline ?? legacyPath);
    const crownSvg = (
        <svg
            aria-hidden={enableSurfaceSelection ? undefined : true}
            className={`${showRoots ? `absolute ${arch === 'upper' ? 'bottom-0' : 'top-0'}` : ''} transform transition-transform duration-200 group-hover:scale-105 group-focus-visible:scale-105`}
            data-layer="crown"
            data-tooth-key={toothKey}
            height="60"
            viewBox="0 0 50 60"
            width="50"
        >
            <g data-crown-scale="1">
                <g data-crown-orientation="baseline">
                    <g data-layer-index="0" data-layer-role="base-anatomy" opacity={crownBaseOpacity}>
                        {isOrganic ? (
                            <g transform={organicTransform}>
                                {Object.entries(crownGeometry.paths).map(([surfaceKey, surfacePath]) => (
                                    <path
                                        key={surfaceKey}
                                        d={surfacePath}
                                        data-surface={surfaceKey}
                                        fill={style.fill}
                                        stroke={style.stroke}
                                        strokeWidth={crownGeometry.style?.strokeWidth ?? 1}
                                        strokeLinejoin="round"
                                        className="transition-colors duration-300"
                                    />
                                ))}
                            </g>
                        ) : (
                            <path
                                d={crownGeometry?.paths?.outline ?? legacyPath}
                                fill={style.fill}
                                stroke={style.stroke}
                                strokeWidth="2"
                                className="transition-colors duration-300"
                            />
                        )}
                    </g>
                    {needsCrownClip && (
                        <defs>
                            <clipPath id={crownClipId}>
                                <path d={crownClipPath} transform={organicTransform} />
                            </clipPath>
                        </defs>
                    )}
                    {condition === 'Decayed' && (
                        <circle
                            cx={25}
                            cy={isOrganic ? (arch === 'upper' ? 28 : 20) : 25}
                            r={5}
                            fill="#ef4444"
                        />
                    )}
                    <CrownVisualLayers
                        crownClipId={crownClipId}
                        crownPath={crownClipPath}
                        crownTransform={organicTransform}
                        toothKey={toothKey}
                        toothVisual={toothVisual}
                    />
                    {enableSurfaceSelection && (
                        <ToothSurfaceLayer
                            toothKey={toothKey}
                            toothNumber={number}
                            toothLabel={toothLabel}
                            clipPathId={crownClipId}
                            selectedSurfaceCode={selectedSurface?.toothKey === toothKey ? selectedSurface.surfaceCode : null}
                            onSurfaceClick={onSurfaceClick}
                            disabled={disabled}
                        />
                    )}
                </g>
            </g>
        </svg>
    );

    const toothContent = (
        <>
            {showRoots ? (
                <span
                    aria-hidden={enableSurfaceSelection ? undefined : true}
                    className={`relative block w-[50px] ${arch === 'upper' ? 'h-[96px]' : 'h-[82px]'}`}
                >
                    <ToothRootLayer toothKey={toothKey} arch={arch} opacity={style.opacity} toothVisual={toothVisual} />
                    {crownSvg}
                </span>
            ) : crownSvg}
            <span className="absolute -bottom-5 flex w-full flex-col items-center">
                <span
                    className="w-full whitespace-nowrap border-t border-slate-300 pt-1 text-center font-mono text-sm font-bold leading-none text-slate-600"
                    data-layer="notation-label"
                    data-notation-mode={notation.mode}
                    data-tooth-key={notation.toothKey}
                >
                    {toothLabel}
                </span>
            </span>
        </>
    );

    const toothClassName = `group relative flex min-w-[50px] shrink-0 flex-col items-center gap-1 rounded-lg focus-visible:ring-focus ${showRoots ? (arch === 'upper' ? 'min-h-[112px]' : 'min-h-[98px]') : 'min-h-[76px]'}`;

    if (enableSurfaceSelection) {
        return (
            <div className={`${toothClassName} cursor-default`} role="group" aria-disabled={disabled} aria-label={`Tooth ${toothLabel} surfaces`}>
                {toothContent}
            </div>
        );
    }

    if (readOnly) {
        return (
            <div
                aria-label={`Tooth ${toothLabel} — ${condition}`}
                className={`${toothClassName} cursor-default`}
            >
                {toothContent}
            </div>
        );
    }

    return (
        <button
            type="button"
            className={`${toothClassName} cursor-pointer`}
            disabled={disabled}
            onClick={() => onClick(number)}
            aria-label={`Tooth ${toothLabel} — ${condition}`}
        >
            {toothContent}
        </button>
    );
});

export default memo(function DentalChartSVG({
    teethStatus,
    toothVisuals = {},
    onToothClick,
    isPediatric,
    toothOrder,
    showRoots = false,
    enableSurfaceSelection = false,
    selectedSurface = null,
    onSurfaceClick,
    readOnly = false,
    notationMode = DEFAULT_CHART_NOTATION_MODE,
}) {
    const isMixedDentition = Array.isArray(toothOrder);
    const layout = isMixedDentition
        ? createMixedLayout(toothOrder)
        : createLegacyLayout(isPediatric);
    const chartMinWidth = isMixedDentition
        ? 'min-w-[600px]'
        : (isPediatric ? 'min-w-[480px]' : 'min-w-[700px]');
    const chartTitle = isMixedDentition
        ? 'مخطط الأسنان (مختلط)'
        : (isPediatric ? 'مخطط الأسنان (أطفال)' : 'مخطط الأسنان (بالغين)');
    const surfaceSelectionEnabled = enableSurfaceSelection && !readOnly;
    const notationConfig = getChartNotationConfig(notationMode);
    const renderTooth = (tooth, arch) => (
        <SVGTooth
            arch={arch}
            enableSurfaceSelection={surfaceSelectionEnabled}
            isPediatric={tooth.isPediatric}
            key={tooth.toothKey}
            notationMode={notationMode}
            number={tooth.sourceId}
            onClick={onToothClick}
            onSurfaceClick={onSurfaceClick}
            readOnly={readOnly}
            selectedSurface={selectedSurface}
            showRoots={showRoots}
            status={teethStatus[tooth.toothKey]}
            toothKey={tooth.toothKey}
            toothVisual={toothVisuals[tooth.toothKey]}
        />
    );


    return (
        <div
            className="min-w-0 overflow-x-auto overscroll-x-contain rounded-2xl bg-slate-50 p-3 text-center shadow-inner touch-pan-x sm:rounded-3xl sm:p-5 lg:p-8"
            data-dentition={isMixedDentition ? 'mixed' : (isPediatric ? 'primary' : 'permanent')}
            data-interaction-mode={readOnly ? 'read-only' : 'edit'}
            data-notation-mode={notationMode}
        >
            <div className={`${chartMinWidth} inline-flex flex-col`} dir="ltr">
                <h3 className="mb-7 text-lg font-bold text-slate-700 sm:mb-8">
                    {chartTitle}
                    <span className="mt-1 block text-xs font-normal text-slate-500">{notationConfig.displayName}</span>
                </h3>

                <div className="inline-flex flex-col gap-14 sm:gap-16">
                    <div className="relative flex justify-center gap-1">
                        <div className="absolute inset-y-0 start-1/2 w-0.5 bg-slate-300" aria-hidden="true" />
                        <div className="absolute inset-x-0 bottom-0 h-0.5 bg-slate-300" aria-hidden="true" />
                        <div className="flex gap-1 px-3 pb-4 sm:px-4">
                            {layout.upperLeft.map((tooth) => renderTooth(tooth, 'upper'))}
                        </div>
                        <div className="w-0.5" />
                        <div className="flex gap-1 px-3 pb-4 sm:px-4">
                            {layout.upperRight.map((tooth) => renderTooth(tooth, 'upper'))}
                        </div>
                    </div>

                    <div className="relative flex justify-center gap-1">
                        <div className="absolute inset-y-0 start-1/2 w-0.5 bg-slate-300" aria-hidden="true" />
                        <div className="absolute inset-x-0 top-0 h-0.5 bg-slate-300" aria-hidden="true" />
                        <div className="flex gap-1 px-3 pt-4 sm:px-4">
                            {layout.lowerLeft.map((tooth) => renderTooth(tooth, 'lower'))}
                        </div>
                        <div className="w-0.5" />
                        <div className="flex gap-1 px-3 pt-4 sm:px-4">
                            {layout.lowerRight.map((tooth) => renderTooth(tooth, 'lower'))}
                        </div>
                    </div>
                </div>

                <div className="mt-10 flex flex-wrap justify-center gap-3 border-t border-slate-200 pt-5 text-sm sm:mt-12 sm:gap-6 sm:pt-6" dir="rtl">
                    {Object.entries(STATUS_STYLES).map(([status, statusStyle]) => (
                        <div key={status} className="flex min-h-8 items-center gap-2">
                            <div className="h-5 w-5 shrink-0 rounded-full border shadow-sm" style={{ backgroundColor: statusStyle.fill, borderColor: statusStyle.stroke, borderWidth: 2 }} aria-hidden="true" />
                            <span className="font-medium text-slate-600">
                                {status === 'Healthy' ? 'سليم' :
                                    status === 'Decayed' ? 'تسوس' :
                                        status === 'Filled' ? 'حشو' :
                                            status === 'Missing' ? 'مخلوع' :
                                                status === 'Crown' ? 'طربوش' : 'عصب'}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
});
