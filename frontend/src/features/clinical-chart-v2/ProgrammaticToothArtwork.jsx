import { memo, useId } from 'react';
import { PROCEDURE_TYPE } from './toothTypes';

const FDI_46 = Object.freeze({
    crown: 'M15 61 C25 51 45 55 57 60 C70 51 104 51 124 63 C128 78 125 104 115 119 C101 133 84 128 69 126 C53 132 32 131 20 117 C12 101 10 77 15 61 Z',
    occlusalRestoration: 'M43 69 C49 63 58 65 68 72 C78 64 91 63 99 70 L93 84 C84 89 76 86 68 82 C59 88 49 87 42 81 Z',
    occlusalLesion: 'M53 70 C59 66 64 69 69 75 C74 69 82 67 87 72 C83 80 77 83 69 80 C63 84 56 80 53 70 Z',
    pulp: 'M47 99 C54 91 82 91 91 100 L84 116 C78 121 59 121 52 115 Z',
    canals: [
        'M57 111 C50 137 43 176 35 224',
        'M66 113 C61 143 58 184 54 226',
        'M78 112 C86 144 94 183 103 227',
    ],
    fracture: 'M91 56 L124 63 L123 82 L111 87 L100 76 L91 72 Z',
    implantFixture: 'M57 126 L82 126 L78 226 Q70 241 61 226 Z',
    implantThreads: [143, 157, 171, 185, 199, 213],
});

function Definitions({ ids }) {
    return (
        <defs>
            <linearGradient id={ids.composite} x1="0" x2="1" y1="0" y2="1">
                <stop offset="0" stopColor="#85c8f6" />
                <stop offset="0.5" stopColor="#3182ce" />
                <stop offset="1" stopColor="#1f5f9d" />
            </linearGradient>
            <linearGradient id={ids.metal} x1="0" x2="1">
                <stop offset="0" stopColor="#4b5563" />
                <stop offset="0.34" stopColor="#e5e7eb" />
                <stop offset="0.62" stopColor="#778391" />
                <stop offset="1" stopColor="#cbd5e1" />
            </linearGradient>
            <linearGradient id={ids.gold} x1="0" x2="1" y1="0" y2="1">
                <stop offset="0" stopColor="#7c4a08" />
                <stop offset="0.28" stopColor="#f6d365" />
                <stop offset="0.58" stopColor="#b7790b" />
                <stop offset="0.82" stopColor="#ffe69a" />
                <stop offset="1" stopColor="#8b5a0a" />
            </linearGradient>
            <linearGradient id={ids.implant} x1="0" x2="1">
                <stop offset="0" stopColor="#3f4b57" />
                <stop offset="0.42" stopColor="#e2e8f0" />
                <stop offset="0.7" stopColor="#64748b" />
                <stop offset="1" stopColor="#cbd5e1" />
            </linearGradient>
            <radialGradient id={ids.caries} cx="50%" cy="45%" r="65%">
                <stop offset="0" stopColor="#3b120d" />
                <stop offset="0.55" stopColor="#7f1d1d" />
                <stop offset="1" stopColor="#c24135" stopOpacity="0.7" />
            </radialGradient>
            <filter id={ids.shadow} x="-30%" y="-30%" width="160%" height="160%">
                <feDropShadow dx="0" dy="1" stdDeviation="1.4" floodColor="#172033" floodOpacity="0.35" />
            </filter>
            <mask id={ids.fractureMask}>
                <rect width="140" height="300" fill="white" />
                <path d={FDI_46.fracture} fill="black" />
            </mask>
            <clipPath id={ids.crownClip}><path d={FDI_46.crown} /></clipPath>
        </defs>
    );
}

function SurfaceEffect({ type, ids }) {
    if (type === PROCEDURE_TYPE.CARIES) {
        return <path data-testid="programmatic-caries" d={FDI_46.occlusalLesion} fill={`url(#${ids.caries})`} stroke="#5c1712" strokeWidth="1.2" filter={`url(#${ids.shadow})`} />;
    }
    if (type === PROCEDURE_TYPE.COMPOSITE || type === PROCEDURE_TYPE.AMALGAM) {
        const gradient = type === PROCEDURE_TYPE.COMPOSITE ? ids.composite : ids.metal;
        return (
            <g data-testid={`programmatic-${type}`} filter={`url(#${ids.shadow})`}>
                <path d={FDI_46.occlusalRestoration} fill={`url(#${gradient})`} stroke={type === PROCEDURE_TYPE.COMPOSITE ? '#174f82' : '#46515d'} strokeWidth="1.1" />
                <path d="M48 73 C57 69 61 76 68 78 C76 72 85 70 94 74" fill="none" stroke="#fff" strokeWidth="0.9" opacity="0.65" strokeLinecap="round" />
            </g>
        );
    }
    return null;
}

function RootCanalEffect() {
    return (
        <g data-testid="programmatic-rct">
            <path d={FDI_46.pulp} fill="#b84c57" fillOpacity="0.72" stroke="#7f1d2d" strokeWidth="1" />
            {FDI_46.canals.map((path) => (
                <g key={path}>
                    <path d={path} fill="none" stroke="#fff3e7" strokeWidth="5" strokeLinecap="round" opacity="0.78" />
                    <path d={path} fill="none" stroke="#d45d64" strokeWidth="2.5" strokeLinecap="round" />
                    <path d={path} fill="none" stroke="#ffd0c6" strokeWidth="0.65" strokeLinecap="round" />
                </g>
            ))}
        </g>
    );
}

function ImplantEffect({ healthyAsset, ids }) {
    return (
        <g data-testid="programmatic-implant">
            <image href={healthyAsset} width="140" height="300" clipPath={`url(#${ids.crownClip})`} />
            <rect x="57" y="115" width="25" height="18" rx="4" fill={`url(#${ids.implant})`} stroke="#3f4b57" />
            <path d={FDI_46.implantFixture} fill={`url(#${ids.implant})`} stroke="#3f4b57" strokeWidth="1.5" />
            {FDI_46.implantThreads.map((y) => <path key={y} d={`M58 ${y} L80 ${y + 5}`} stroke="#36414c" strokeWidth="2" />)}
        </g>
    );
}

const ProgrammaticToothArtwork = memo(function ProgrammaticToothArtwork({ healthyAsset, procedure, fdi, testId }) {
    const rawId = useId().replace(/:/g, '');
    const ids = {
        composite: `${rawId}-composite`, metal: `${rawId}-metal`, gold: `${rawId}-gold`, implant: `${rawId}-implant`,
        caries: `${rawId}-caries`, shadow: `${rawId}-shadow`, fractureMask: `${rawId}-fracture`, crownClip: `${rawId}-crown`,
    };
    const type = procedure?.type;
    const isMissing = type === PROCEDURE_TYPE.MISSING;
    const isImplant = type === PROCEDURE_TYPE.IMPLANT;
    const isFracture = type === PROCEDURE_TYPE.FRACTURE;

    return (
        <svg viewBox="0 0 140 300" className="h-full w-full" role="img" aria-label={`السن ${fdi}: تأثير برمجي ${type}`} data-testid={testId} data-renderer="programmatic" data-effect={type}>
            <Definitions ids={ids} />
            {!isImplant && (
                <image href={healthyAsset} width="140" height="300" opacity={isMissing ? 0.2 : type === PROCEDURE_TYPE.RCT ? 0.72 : 1} mask={isFracture ? `url(#${ids.fractureMask})` : undefined} />
            )}
            <SurfaceEffect type={type} ids={ids} />
            {type === PROCEDURE_TYPE.RCT && <RootCanalEffect />}
            {type === PROCEDURE_TYPE.CROWN && <path data-testid="programmatic-crown" d={FDI_46.crown} fill={`url(#${ids.gold})`} fillOpacity="0.88" stroke="#7c4a08" strokeWidth="1.25" />}
            {isImplant && <ImplantEffect healthyAsset={healthyAsset} ids={ids} />}
            {isMissing && <g data-testid="programmatic-missing" stroke="#64748b" strokeWidth="5" strokeLinecap="round"><path d="M43 104 L96 181" /><path d="M96 104 L43 181" /></g>}
            {isFracture && <path data-testid="programmatic-fracture" d={FDI_46.fracture} fill="none" stroke="#b99375" strokeWidth="1.4" strokeDasharray="3 2" />}
        </svg>
    );
});

export default ProgrammaticToothArtwork;
