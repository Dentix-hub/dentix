import { memo } from 'react';
import { getOrganicToothType } from './dentalPaths';
// LAYERED TOOTH COMPONENT (High Fidelity)
// 1. Root Layer: Handles RCT, Implants, Abscess
// 2. Crown Body Layer: Handles Crowns, Veneers, Missing
// 3. Surface Layer: Handles Fillings, Decay (On top of crown)
const SegmentedTooth = memo(function SegmentedTooth({
    number,
    procedures = [],
    status = 'Sound',
    onSegmentClick,
    onToothClick,
    isActive,
    selectedSegments = [],
    activeTool = 'cursor'
}) {
    // Get specific paths for this tooth number
    const pathData = getOrganicToothType(number);
    if (!pathData) return null;
    const { isMirror } = pathData;
    const paths = pathData; // Structure is { Root: "...", CrownBox: {...} }
    // --- LOGIC: EXTRACT LAYERS FROM HISTORY ---
    // 1. Root Condition
    const rootProc = procedures.find(p => ['rct', 'implant', 'apicoectomy'].includes(p.type));
    const isRCT = rootProc?.type === 'rct';
    const isImplant = rootProc?.type === 'implant';
    // 2. Crown Condition (Whole Tooth Coverage)
    const crownProc = procedures.find(p => ['crown', 'bridge', 'veneer', 'extraction'].includes(p.type));
    const isCrown = crownProc?.type === 'crown';
    const isMissing = status === 'Missing' || crownProc?.type === 'extraction';
    // 3. Surfaces (Fillings/Decay)
    const getSurfaceColor = (segName) => {
        // A. Tool Interaction
        if (selectedSegments.includes(segName)) return 'fill-blue-400 animate-pulse';
        // B. Existing Procedures
        if (isMissing) return 'fill-transparent';
        const relevant = procedures.filter(p => !p.isWholeTooth && p.segments?.includes(segName));
        if (relevant.length === 0) return 'fill-transparent';
        const last = relevant[relevant.length - 1];
        if (last.type === 'filling') return 'fill-blue-500';
        if (last.type === 'decay') return 'fill-red-500';
        if (last.type === 'sealant') return 'fill-pink-300';
        return 'fill-transparent';
    };
    // --- STYLES ---
    // Root Fill
    const rootFill = isImplant ? 'fill-slate-200' : isRCT ? 'fill-red-100' : 'fill-white';
    // Crown Body Fill
    const crownFill = isMissing ? 'fill-slate-100 opacity-20' : isCrown ? 'fill-yellow-100' : 'fill-white';
    const containerClasses = `
        relative flex flex-col items-center justify-center p-1 rounded-xl transition-all duration-200
        ${isActive ? 'bg-blue-100/50 ring-2 ring-blue-500 shadow-lg scale-110 z-20' : 'hover:bg-slate-100/50'}
        ${activeTool !== 'cursor' ? 'cursor-crosshair' : 'cursor-pointer'}
        ${isMissing ? 'opacity-60' : ''}
    `;
    return (
        <div className={containerClasses} onClick={() => onToothClick(number)}>
            {/* Tooth Number */}
            <span className={`text-[10px] font-bold mb-1 leading-none ${isActive ? 'text-blue-600' : 'text-slate-400'}`}>
                {number}
            </span>
            <svg
                width="40"
                height="70"
                viewBox="0 0 100 150"
                className={`overflow-visible drop-shadow-sm transition-transform ${isMirror ? '-scale-x-100' : ''}`} // MIRROR FLIP
            >
                {/* LAYER 1: ROOTS */}
                <g id="layer-roots">
                    <path
                        d={paths.Root}
                        className={`stroke-slate-400 stroke-[1.5] ${rootFill}`}
                    />
                    {isRCT && (
                        // Gutta Percha Lines
                        <path d={number <= 16 ? "M50,30 L50,85 M35,45 L35,80 M65,45 L65,80" : "M50,80 L50,140 M35,90 L35,135 M65,90 L65,135"}
                            stroke="#ef4444" strokeWidth="2" fill="none" opacity="0.8" />
                    )}
                    {isImplant && (
                        // Implant Screw
                        <path d={number <= 16 ? "M50,10 L50,90" : "M50,60 L50,140"}
                            stroke="#6366f1" strokeWidth="6" strokeDasharray="4 2" strokeLinecap="round" />
                    )}
                </g>
                {/* LAYER 2: CROWN BODY */}
                <g id="layer-crown-body">
                    {Object.values(paths.CrownBox).map((d, i) => (
                        <path key={i} d={d} className={`stroke-none ${crownFill}`} />
                    ))}
                    {/* Visual Cues */}
                    {isCrown && (
                        <circle cx="70" cy={number <= 16 ? "110" : "30"} r="5" fill="white" opacity="0.6" />
                    )}
                </g>
                {/* LAYER 3: SURFACES */}
                <g id="layer-surfaces">
                    {Object.entries(paths.CrownBox).map(([seg, path]) => (
                        <path
                            key={seg}
                            d={path}
                            className={`
                                stroke-slate-300 stroke-[1] stroke-linejoin-round 
                                transition-colors duration-200 
                                ${getSurfaceColor(seg)} 
                                ${!isMissing ? 'hover:fill-blue-100 hover:opacity-70' : ''}
                            `}
                            onClick={(e) => {
                                e.stopPropagation();
                                if (!isMissing) onSegmentClick(number, seg);
                            }}
                        />
                    ))}
                </g>
                {/* LAYER 4: OVERLAYS */}
                {isMissing && (
                    <path d="M20,40 L80,120 M80,40 L20,120" stroke="#ef4444" strokeWidth="3" opacity="0.5" strokeLinecap="round" />
                )}
            </svg>
            {/* Status Dot */}
            {!isMissing && status !== 'Sound' && (
                <div className={`w-1.5 h-1.5 rounded-full mt-1 ${status.includes('Decay') ? 'bg-red-500' :
                    status === 'Impacted' ? 'bg-purple-500' :
                        'bg-slate-300'
                    }`} />
            )}
        </div>
    );
});

SegmentedTooth.displayName = 'SegmentedTooth';

export default SegmentedTooth;
