import React from 'react';

// A generic molar map used for segment selection
// Segments: Occlusal (Center), Mesial, Distal, Buccal, Lingual
const SEGMENT_PATHS = {
    Occlusal: "M35,35 L65,35 L65,65 L35,65 Z", // Center square
    Buccal: "M35,35 L65,35 L80,10 L20,10 Z",   // Top trapezoid
    Lingual: "M35,65 L65,65 L80,90 L20,90 Z",  // Bottom trapezoid
    Mesial: "M35,35 L35,65 L10,80 L10,20 Z",   // Left trapezoid
    Distal: "M65,35 L65,65 L90,80 L90,20 Z"    // Right trapezoid
};

// Colors for conditions
const CONDITION_COLORS = {
    Healthy: 'fill-white',
    Decayed: 'fill-red-400',
    Filled: 'fill-blue-400',
    Crown: 'fill-green-400',
    Missing: 'fill-slate-800'
};

export default function ToothSegmentMap({ selectedSegments = [], onToggleSegment }) {
    // selectedSegments is an array of strings: ['Mesial', 'Occlusal']

    const renderSegment = (name, path) => {
        const isSelected = selectedSegments.includes(name);
        return (
            <path
                key={name}
                d={path}
                onClick={() => onToggleSegment(name)}
                className={`
                    cursor-pointer transition-colors duration-200 stroke-slate-300 stroke-1
                    ${isSelected ? 'fill-blue-600 hover:fill-blue-700' : 'fill-white hover:fill-slate-100'}
                `}
            />
        );
    };

    return (
        <div className="flex flex-col items-center">
            <svg width="100" height="100" viewBox="0 0 100 100" className="drop-shadow-md">
                {Object.entries(SEGMENT_PATHS).map(([name, path]) => renderSegment(name, path))}

                {/* Text Labels */}
                <text x="50" y="52" textAnchor="middle" className="text-[10px] fill-slate-400 pointer-events-none">O</text>
                <text x="50" y="25" textAnchor="middle" className="text-[10px] fill-slate-400 pointer-events-none">B</text>
                <text x="50" y="80" textAnchor="middle" className="text-[10px] fill-slate-400 pointer-events-none">L</text>
                <text x="20" y="52" textAnchor="middle" className="text-[10px] fill-slate-400 pointer-events-none">M</text>
                <text x="80" y="52" textAnchor="middle" className="text-[10px] fill-slate-400 pointer-events-none">D</text>
            </svg>
            <span className="text-xs text-slate-400 mt-2">اضغط على الأجزاء لتحديدها</span>
        </div>
    );
}
