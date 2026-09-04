import { memo, useId } from 'react';
import { getClinicalToothGeometry } from './toothGeometry';
import {
    describeClinicalState,
    getLifecycleVisual,
    getProcedure,
    getSurfaceProcedures,
    PROCEDURE_VISUALS,
} from './procedureLayers';
import {
    normalizeClinicalToothState,
    parseFdiTooth,
    PROCEDURE_LIFECYCLE,
    PROCEDURE_TYPE,
} from './toothTypes';

function ToothDefinitions({ ids }) {
    return (
        <defs>
            <linearGradient id={ids.enamel} x1="0.08" x2="0.88" y1="0" y2="1">
                <stop offset="0%" stopColor="#d8ccba" />
                <stop offset="22%" stopColor="#faf7ee" />
                <stop offset="58%" stopColor="#fffefa" />
                <stop offset="100%" stopColor="#d9cfbf" />
            </linearGradient>
            <linearGradient id={ids.root} x1="0" x2="1" y1="0" y2="0.8">
                <stop offset="0%" stopColor="#c7b9a6" />
                <stop offset="30%" stopColor="#f0eadf" />
                <stop offset="68%" stopColor="#fbf8f1" />
                <stop offset="100%" stopColor="#c8b9a4" />
            </linearGradient>
            <linearGradient id={ids.crown} x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stopColor="#8c6322" />
                <stop offset="23%" stopColor="#dfbc69" />
                <stop offset="55%" stopColor="#f3dea0" />
                <stop offset="100%" stopColor="#9c6d24" />
            </linearGradient>
            <linearGradient id={ids.metal} x1="0" x2="1" y1="0" y2="0">
                <stop offset="0%" stopColor="#3e4b57" />
                <stop offset="24%" stopColor="#b8c0c7" />
                <stop offset="48%" stopColor="#eef1f3" />
                <stop offset="72%" stopColor="#87939e" />
                <stop offset="100%" stopColor="#46535f" />
            </linearGradient>
            <linearGradient id={ids.implantCrown} x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stopColor="#d7ebe8" />
                <stop offset="38%" stopColor="#f8fbfa" />
                <stop offset="100%" stopColor="#8bbab5" />
            </linearGradient>
            <radialGradient id={ids.pulp} cx="50%" cy="42%" r="62%">
                <stop offset="0%" stopColor="#d9c9f2" />
                <stop offset="100%" stopColor="#6e4aa3" />
            </radialGradient>
            <filter id={ids.shadow} x="-25%" y="-20%" width="150%" height="155%">
                <feDropShadow dx="0" dy="1.5" stdDeviation="1.8" floodColor="#263442" floodOpacity="0.18" />
            </filter>
        </defs>
    );
}

function RootAnatomy({ geometry, ids, subdued = false }) {
    return (
        <g data-testid="root-anatomy" opacity={subdued ? 0.66 : 0.94}>
            {geometry.roots.map((path, index) => (
                <path
                    key={path}
                    d={path}
                    fill={`url(#${ids.root})`}
                    stroke="#65717b"
                    strokeWidth="1.35"
                    strokeLinejoin="round"
                    vectorEffect="non-scaling-stroke"
                    data-root-index={index}
                />
            ))}
        </g>
    );
}

function CrownAnatomy({ geometry, ids }) {
    return (
        <g data-testid="crown-anatomy" filter={`url(#${ids.shadow})`}>
            <path
                d={geometry.crown}
                fill={`url(#${ids.enamel})`}
                stroke="#53606b"
                strokeWidth="1.55"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
            />
            <path
                d={geometry.cervicalLine}
                fill="none"
                stroke="#9a8b79"
                strokeWidth="1.1"
                strokeLinecap="round"
                vectorEffect="non-scaling-stroke"
                opacity="0.6"
            />
            {geometry.anatomyLines.map((path) => (
                <path
                    key={path}
                    d={path}
                    fill="none"
                    stroke="#8d8275"
                    strokeWidth="0.9"
                    strokeLinecap="round"
                    vectorEffect="non-scaling-stroke"
                    opacity="0.43"
                />
            ))}
            <path
                d={geometry.crown}
                fill="none"
                stroke="#ffffff"
                strokeWidth="0.65"
                vectorEffect="non-scaling-stroke"
                opacity="0.72"
                transform="translate(-1 -1)"
            />
        </g>
    );
}

function RootCanalLayer({ geometry, procedure, ids }) {
    if (!procedure) return null;
    const visual = PROCEDURE_VISUALS[PROCEDURE_TYPE.RCT];
    const lifecycle = getLifecycleVisual(procedure.lifecycle);

    return (
        <g
            data-testid="rct-layer"
            data-lifecycle={procedure.lifecycle}
            aria-label={visual.label}
            opacity={lifecycle.opacity}
        >
            <path
                d={geometry.pulpChamber}
                fill={`url(#${ids.pulp})`}
                stroke={visual.darkColor}
                strokeWidth={lifecycle.strokeWidth}
                strokeDasharray={lifecycle.strokeDasharray}
                vectorEffect="non-scaling-stroke"
            />
            {geometry.canals.map((path) => (
                <g key={path}>
                    <path
                        d={path}
                        fill="none"
                        stroke="#fffaf0"
                        strokeWidth="5"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                        opacity="0.84"
                    />
                    <path
                        d={path}
                        fill="none"
                        stroke={visual.color}
                        strokeWidth="2.65"
                        strokeLinecap="round"
                        strokeDasharray={lifecycle.strokeDasharray}
                        vectorEffect="non-scaling-stroke"
                    />
                    <path
                        d={path}
                        fill="none"
                        stroke={visual.highlight}
                        strokeWidth="0.7"
                        strokeLinecap="round"
                        strokeDasharray={lifecycle.strokeDasharray}
                        vectorEffect="non-scaling-stroke"
                        opacity="0.72"
                    />
                </g>
            ))}
        </g>
    );
}

function SurfaceProcedureLayers({ geometry, state, ids }) {
    return getSurfaceProcedures(state).map((procedure) => {
        const visual = PROCEDURE_VISUALS[procedure.type];
        const lifecycle = getLifecycleVisual(procedure.lifecycle);
        const pathKey = procedure.type === PROCEDURE_TYPE.CARIES ? 'lesion' : 'restoration';
        const surfaces = procedure.surfaces.length ? procedure.surfaces : ['O'];

        return (
            <g
                key={`${procedure.type}-${surfaces.join('')}-${procedure.lifecycle}`}
                data-testid={`${procedure.type}-layer`}
                data-lifecycle={procedure.lifecycle}
                aria-label={`${visual.label} ${surfaces.join('')}`}
                opacity={lifecycle.opacity}
            >
                {surfaces.map((surface) => {
                    const surfaceGeometry = geometry.surfaces[surface];
                    if (!surfaceGeometry) return null;

                    const fill = procedure.type === PROCEDURE_TYPE.AMALGAM
                        ? `url(#${ids.metal})`
                        : visual.color;

                    return (
                        <g key={surface} data-testid={`${procedure.type}-surface-${surface}`}>
                            <path
                                d={surfaceGeometry[pathKey]}
                                fill={fill}
                                stroke={visual.darkColor}
                                strokeWidth={lifecycle.strokeWidth}
                                strokeDasharray={lifecycle.strokeDasharray}
                                strokeLinejoin="round"
                                vectorEffect="non-scaling-stroke"
                            />
                            <path
                                d={surfaceGeometry[pathKey]}
                                fill="none"
                                stroke={visual.highlight}
                                strokeWidth="0.75"
                                strokeDasharray={lifecycle.strokeDasharray}
                                vectorEffect="non-scaling-stroke"
                                opacity={procedure.type === PROCEDURE_TYPE.CARIES ? 0.35 : 0.78}
                                transform="translate(-0.8 -0.8)"
                            />
                        </g>
                    );
                })}
            </g>
        );
    });
}

function CrownLayer({ geometry, procedure, ids }) {
    if (!procedure) return null;
    const visual = PROCEDURE_VISUALS[PROCEDURE_TYPE.CROWN];
    const lifecycle = getLifecycleVisual(procedure.lifecycle);

    return (
        <g
            data-testid="crown-layer"
            data-lifecycle={procedure.lifecycle}
            aria-label={visual.label}
            opacity={lifecycle.opacity}
        >
            <path
                data-testid="crown-shell"
                d={geometry.crownShell}
                fill={`url(#${ids.crown})`}
                fillOpacity="0.84"
                stroke={visual.darkColor}
                strokeWidth={lifecycle.strokeWidth}
                strokeDasharray={lifecycle.strokeDasharray}
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
            />
            {geometry.anatomyLines.map((path) => (
                <path
                    key={path}
                    d={path}
                    fill="none"
                    stroke={visual.darkColor}
                    strokeWidth="0.75"
                    strokeDasharray={lifecycle.strokeDasharray}
                    vectorEffect="non-scaling-stroke"
                    opacity="0.46"
                />
            ))}
        </g>
    );
}

function ImplantLayer({ geometry, procedure, ids }) {
    if (!procedure) return null;
    const visual = PROCEDURE_VISUALS[PROCEDURE_TYPE.IMPLANT];
    const lifecycle = getLifecycleVisual(procedure.lifecycle);

    return (
        <g
            data-testid="implant-layer"
            data-lifecycle={procedure.lifecycle}
            aria-label={visual.label}
            opacity={lifecycle.opacity}
        >
            <path
                d={geometry.implant.fixture}
                fill={`url(#${ids.metal})`}
                stroke={visual.darkColor}
                strokeWidth={lifecycle.strokeWidth}
                strokeDasharray={lifecycle.strokeDasharray}
                vectorEffect="non-scaling-stroke"
            />
            {geometry.implant.threads.map((path) => (
                <path
                    key={path}
                    d={path}
                    fill="none"
                    stroke="#f3f7f7"
                    strokeWidth="1.25"
                    strokeLinecap="round"
                    vectorEffect="non-scaling-stroke"
                    opacity="0.92"
                />
            ))}
            <path
                d={geometry.implant.abutment}
                fill={`url(#${ids.metal})`}
                stroke={visual.darkColor}
                strokeWidth={lifecycle.strokeWidth}
                strokeDasharray={lifecycle.strokeDasharray}
                vectorEffect="non-scaling-stroke"
            />
            <path
                d={geometry.crownShell}
                fill={`url(#${ids.implantCrown})`}
                stroke={visual.darkColor}
                strokeWidth={lifecycle.strokeWidth}
                strokeDasharray={lifecycle.strokeDasharray}
                vectorEffect="non-scaling-stroke"
            />
        </g>
    );
}

function BridgeLayer({ geometry, role, procedure, ids }) {
    if (!role) return null;
    const visual = PROCEDURE_VISUALS[PROCEDURE_TYPE.BRIDGE];
    const lifecycle = getLifecycleVisual(procedure?.lifecycle || PROCEDURE_LIFECYCLE.COMPLETED);

    return (
        <g
            data-testid="bridge-layer"
            data-bridge-role={role}
            aria-label={`Bridge ${role}`}
            opacity={lifecycle.opacity}
        >
            <path
                d={geometry.crownShell}
                fill={`url(#${ids.crown})`}
                fillOpacity="0.74"
                stroke={visual.darkColor}
                strokeWidth={lifecycle.strokeWidth}
                strokeDasharray={lifecycle.strokeDasharray}
                vectorEffect="non-scaling-stroke"
            />
            {role === 'pontic' && (
                <path
                    d={geometry.arch === 'maxillary'
                        ? 'M42 153 Q60 174 78 153 Q73 164 60 168 Q47 164 42 153 Z'
                        : 'M42 34 Q60 12 78 34 Q73 22 60 18 Q47 22 42 34 Z'}
                    fill={visual.color}
                    fillOpacity="0.5"
                    stroke={visual.darkColor}
                    strokeWidth="1.25"
                    vectorEffect="non-scaling-stroke"
                />
            )}
        </g>
    );
}

function MissingLayer({ geometry, ids }) {
    return (
        <g data-testid="missing-layer" aria-label="Missing tooth">
            <g opacity="0.22">
                <RootAnatomy geometry={geometry} ids={ids} />
                <CrownAnatomy geometry={geometry} ids={ids} />
            </g>
            <path d="M33 44 L87 139" stroke="#667585" strokeWidth="3" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
            <path d="M87 44 L33 139" stroke="#667585" strokeWidth="3" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
        </g>
    );
}

const ClinicalToothRenderer = memo(function ClinicalToothRenderer({
    fdi,
    state = { procedures: [] },
    size = 112,
    showLabel = true,
    className = '',
}) {
    const tooth = parseFdiTooth(fdi);
    const geometry = getClinicalToothGeometry(fdi);
    const clinicalState = normalizeClinicalToothState(state, fdi);
    const missing = getProcedure(clinicalState, PROCEDURE_TYPE.MISSING);
    const implant = getProcedure(clinicalState, PROCEDURE_TYPE.IMPLANT);
    const rct = getProcedure(clinicalState, PROCEDURE_TYPE.RCT);
    const crown = getProcedure(clinicalState, PROCEDURE_TYPE.CROWN);
    const bridge = getProcedure(clinicalState, PROCEDURE_TYPE.BRIDGE);
    const bridgeRole = clinicalState.bridgeRole || bridge?.role;
    const uid = useId().replace(/:/g, '');
    const ids = {
        enamel: `clinical-enamel-${uid}`,
        root: `clinical-root-${uid}`,
        crown: `clinical-crown-${uid}`,
        metal: `clinical-metal-${uid}`,
        implantCrown: `clinical-implant-crown-${uid}`,
        pulp: `clinical-pulp-${uid}`,
        shadow: `clinical-shadow-${uid}`,
    };
    const description = describeClinicalState(clinicalState);
    const artworkTransform = geometry.mirror ? 'translate(120 0) scale(-1 1)' : undefined;
    const hideNaturalRoots = Boolean(implant || bridgeRole === 'pontic');

    return (
        <div
            className={`inline-flex flex-col items-center ${className}`}
            data-fdi={tooth.fdi}
            data-template={geometry.templateKey}
            data-root-count={geometry.rootCount}
        >
            <svg
                viewBox="0 0 120 180"
                width={size}
                height={Math.round(size * 1.5)}
                className="block h-auto max-w-full overflow-visible"
                role="img"
                aria-label={`Tooth ${tooth.fdi}: ${description}`}
            >
                <ToothDefinitions ids={ids} />
                <g transform={artworkTransform}>
                    {missing ? (
                        <MissingLayer geometry={geometry} ids={ids} />
                    ) : (
                        <>
                            {!hideNaturalRoots && <RootAnatomy geometry={geometry} ids={ids} subdued={!rct} />}
                            {!implant && <CrownAnatomy geometry={geometry} ids={ids} />}
                            <ImplantLayer geometry={geometry} procedure={implant} ids={ids} />
                            <RootCanalLayer geometry={geometry} procedure={rct} ids={ids} />
                            <SurfaceProcedureLayers geometry={geometry} state={clinicalState} ids={ids} />
                            <CrownLayer geometry={geometry} procedure={crown} ids={ids} />
                            <BridgeLayer geometry={geometry} role={bridgeRole} procedure={bridge} ids={ids} />
                        </>
                    )}
                </g>
            </svg>
            {showLabel && (
                <span className="mt-1 font-mono text-xs font-semibold text-text-muted">
                    {tooth.fdi}
                </span>
            )}
        </div>
    );
});

export const ClinicalBridgeRenderer = memo(function ClinicalBridgeRenderer({ size = 108 }) {
    const bridgeState = (role) => ({
        bridgeRole: role,
        procedures: [{
            type: PROCEDURE_TYPE.BRIDGE,
            role,
            lifecycle: PROCEDURE_LIFECYCLE.COMPLETED,
        }],
    });
    const totalWidth = size * 3;
    const totalHeight = Math.round(size * 1.5);

    return (
        <div className="inline-flex flex-col items-center" role="group" aria-label="Three-unit bridge from tooth 14 to 16">
            <div className="relative inline-flex items-start" dir="ltr">
                <svg
                    viewBox={`0 0 ${totalWidth} ${totalHeight}`}
                    width={totalWidth}
                    height={totalHeight}
                    className="pointer-events-none absolute inset-0 z-10 overflow-visible"
                    aria-hidden="true"
                >
                    <path
                        d={`M${size * 0.76} ${size * 1.08} C${size * 0.92} ${size * 0.98} ${size * 1.08} ${size * 0.98} ${size * 1.24} ${size * 1.08}`}
                        fill="none"
                        stroke="#6f4024"
                        strokeWidth="5"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                    />
                    <path
                        d={`M${size * 1.76} ${size * 1.08} C${size * 1.92} ${size * 0.98} ${size * 2.08} ${size * 0.98} ${size * 2.24} ${size * 1.08}`}
                        fill="none"
                        stroke="#6f4024"
                        strokeWidth="5"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                    />
                    <path
                        d={`M${size * 0.78} ${size * 1.06} C${size * 0.94} ${size} ${size * 1.06} ${size} ${size * 1.22} ${size * 1.06}`}
                        fill="none"
                        stroke="#e6c09d"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                    />
                    <path
                        d={`M${size * 1.78} ${size * 1.06} C${size * 1.94} ${size} ${size * 2.06} ${size} ${size * 2.22} ${size * 1.06}`}
                        fill="none"
                        stroke="#e6c09d"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                        vectorEffect="non-scaling-stroke"
                    />
                </svg>
                <ClinicalToothRenderer fdi={14} state={bridgeState('abutment')} size={size} showLabel={false} />
                <ClinicalToothRenderer fdi={15} state={bridgeState('pontic')} size={size} showLabel={false} />
                <ClinicalToothRenderer fdi={16} state={bridgeState('abutment')} size={size} showLabel={false} />
            </div>
            <div className="mt-1 flex gap-10 font-mono text-xs font-semibold text-text-muted" dir="ltr">
                <span>14</span><span>15</span><span>16</span>
            </div>
        </div>
    );
});

export default ClinicalToothRenderer;
