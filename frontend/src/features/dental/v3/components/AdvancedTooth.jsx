import React, { memo, useMemo } from 'react';
import { getOrganicToothType } from '../assets/dentalPaths';
import { PROCEDURE_TYPES, PROCEDURE_STATUS } from '../assets/dentalConstants';

/**
 * Advanced Tooth Component
 * Renders anatomical layers: Root -> Crown -> Procedures -> Status Overlay
 */
const AdvancedTooth = memo(({
    number,
    procedures = [],
    status = 'Healthy',
    onToothClick,
    isActive
}) => {

    // 1. Resolve Geometry
    const pathData = useMemo(() => getOrganicToothType(number), [number]);
    if (!pathData) return null;
    const { Root, CrownBox, isMirror } = pathData;

    // 2. Resolve Active Procedures derived from History
    // We categorize procedures to determine rendering layers

    const activeProcedures = useMemo(() =>
        procedures.filter(p => !p.removedAt && p.status !== PROCEDURE_STATUS.FAILED),
        [procedures]);

    const rootProcs = activeProcedures.filter(p => PROCEDURE_TYPES[p.type.toUpperCase()]?.isRoot);
    const crownProcs = activeProcedures.filter(p => PROCEDURE_TYPES[p.type.toUpperCase()]?.id === 'crown' || PROCEDURE_TYPES[p.type.toUpperCase()]?.id === 'veneer');
    const surfaceProcs = activeProcedures.filter(p => PROCEDURE_TYPES[p.type.toUpperCase()]?.isSurface);
    const extraction = activeProcedures.find(p => p.type === 'extraction');

    // 3. Determine Visual State
    const isMissing = status === 'Missing' || status === 'Extracted' || extraction;
    const isImplant = rootProcs.some(p => p.type === 'implant');
    const isRCT = rootProcs.some(p => p.type === 'rct');
    const hasCrown = crownProcs.length > 0;

    // --- RENDER HELPERS ---

    const getSurfaceColor = (segmentKey) => {
        // Find latest procedure on this segment
        const proc = surfaceProcs
            .filter(p => p.segments?.includes(segmentKey))
            .sort((a, b) => new Date(b.date) - new Date(a.date))[0]; // Latest wins

        if (proc) {
            const typeDef = PROCEDURE_TYPES[proc.type.toUpperCase()];
            return typeDef?.color || '#3b82f6';
        }
        return 'transparent'; // Show crown/enamel underneath
    };

    const rootFill = isImplant ? '#e0e7ff' : isRCT ? '#fee2e2' : '#ffffff';
    const crownFill = hasCrown ? '#dcfce7' : '#ffffff';

    return (
        <div
            onClick={() => onToothClick(number)}
            className={`
                relative flex flex-col items-center justify-center p-1 rounded-xl transition-all duration-200
                ${isActive ? 'bg-blue-50 ring-2 ring-blue-500 shadow-lg scale-110 z-30' : 'hover:bg-slate-50 cursor-pointer'}
                ${isMissing ? 'opacity-40 grayscale' : ''}
            `}
        >
            <span className={`text-[10px] font-bold mb-1 leading-none ${isActive ? 'text-blue-600' : 'text-slate-400'}`}>
                {number}
            </span>

            <svg
                width="40"
                height="70"
                viewBox="0 0 100 150"
                className={`overflow-visible drop-shadow-sm transition-transform ${isMirror ? '-scale-x-100' : ''}`}
            >
                {/* LAYER 1: ROOTS */}
                <g id="layer-roots">
                    <path
                        d={Root}
                        fill={rootFill}
                        stroke="#94a3b8"
                        strokeWidth="1.5"
                    />
                    {isRCT && (
                        // Gutta Percha visualization
                        <path
                            d={number <= 16 ? "M50,30 L50,85 M35,45 L35,80 M65,45 L65,80" : "M50,80 L50,140 M35,90 L35,135 M65,90 L65,135"}
                            stroke="#ef4444"
                            strokeWidth="2"
                            fill="none"
                            opacity="0.8"
                        />
                    )}
                    {isImplant && (
                        // Fixture visualization
                        <path
                            d={number <= 16 ? "M50,10 L50,90" : "M50,60 L50,140"}
                            stroke="#6366f1"
                            strokeWidth="6"
                            strokeDasharray="4 2"
                            strokeLinecap="round"
                        />
                    )}
                </g>

                {/* LAYER 2: CROWN BODY */}
                <g id="layer-crown">
                    {Object.values(CrownBox).map((d, i) => (
                        <path key={i} d={d} fill={crownFill} stroke="none" />
                    ))}

                    {hasCrown && (
                        <circle cx="70" cy={number <= 16 ? "110" : "30"} r="5" fill="#166534" opacity="0.2" />
                    )}
                </g>

                {/* LAYER 3: SURFACES (Interactive & Colored) */}
                <g id="layer-surfaces">
                    {Object.entries(CrownBox).map(([seg, path]) => {
                        const fill = getSurfaceColor(seg);
                        return (
                            <path
                                key={seg}
                                d={path}
                                fill={fill}
                                stroke={fill !== 'transparent' ? 'none' : '#cbd5e1'}
                                strokeWidth="1"
                                className="transition-colors duration-150"
                            />
                        );
                    })}
                </g>

                {/* LAYER 4: STATUS OVERLAYS */}
                {(isMissing || extraction) && (
                    <path d="M20,40 L80,120 M80,40 L20,120" stroke="#ef4444" strokeWidth="3" opacity="0.8" strokeLinecap="round" />
                )}

            </svg>

            {/* Status Dot for generic states */}
            {status === 'Impacted' && <div className="w-2 h-2 rounded-full bg-purple-500 mt-1" />}
        </div>
    );
});

export default AdvancedTooth;
