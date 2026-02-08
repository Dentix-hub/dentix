import React, { useState } from 'react';

// Simplified representation of teeth locations for a visual chart
// In a real app, this might be SVGs. Here we use CSS circles/squares arranged in arches.
const TEETH_UPPER = Array.from({ length: 16 }, (_, i) => 18 - i).filter(t => t > 10 || t < 9); // 18..11, 21..28 (FDI)
// Let's use Universal Numbering (1-32) for simplicity in internal logic, but display can vary.
// Upper Arch: 1 (Right Wisdom) to 16 (Left Wisdom)
// Lower Arch: 17 (Left Wisdom) to 32 (Right Wisdom)

const TEETH_NUMBERS = {
    // Original: 1..16 (Right to Left). New: 16..1 (Left to Right)
    upper: Array.from({ length: 16 }, (_, i) => 16 - i),
    // Original: 32..17 (Right to Left). New: 17..32 (Left to Right)
    lower: Array.from({ length: 16 }, (_, i) => 17 + i),
};

const STATUS_COLORS = {
    Healthy: 'bg-white border-slate-300',
    Decayed: 'bg-red-500 border-red-600',
    Filled: 'bg-blue-500 border-blue-600',
    Missing: 'bg-slate-900 border-slate-900 opacity-20',
    Crown: 'bg-yellow-400 border-yellow-500',
    RootCanal: 'bg-purple-500 border-purple-600',
};

function Tooth({ number, status, onClick }) {
    const colorClass = STATUS_COLORS[status?.condition || 'Healthy'] || STATUS_COLORS.Healthy;

    return (
        <div
            onClick={() => onClick(number)}
            className="flex flex-col items-center gap-1 cursor-pointer group"
        >
            <div className={`
        w-10 h-10 md:w-12 md:h-14 rounded-t-xl rounded-b-md border-2 shadow-sm transition-all transform group-hover:scale-110
        ${colorClass}
      `} />
            <span className="text-xs font-bold text-slate-500">{number}</span>
        </div>
    );
}

export default function DentalChart({ teethStatus, onToothClick }) {
    // teethStatus is a key-value map: { tooth_number: { condition: '...', notes: '...' } }

    return (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 overflow-x-auto">
            <h3 className="text-lg font-bold mb-6 text-center text-slate-700">مخطط الأسنان (Dental Chart)</h3>

            <div className="min-w-[600px] flex flex-col gap-8 items-center">
                {/* Upper Arch */}
                <div className="flex gap-2 pb-6 border-b border-dashed border-slate-200 justify-center">
                    {TEETH_NUMBERS.upper.map(num => (
                        <div key={num} className={num === 8 ? "mr-4" : ""}>
                            {/* Gap between 8 and 9 separate quadrants */}
                            <Tooth
                                number={num}
                                status={teethStatus[num]}
                                onClick={onToothClick}
                            />
                        </div>
                    ))}
                </div>

                {/* Lower Arch */}
                <div className="flex gap-2 pt-2 justify-center">
                    {TEETH_NUMBERS.lower.map(num => (
                        <div key={num} className={num === 24 ? "mr-4" : ""}>
                            {/* Gap between 24 and 25 */}
                            <Tooth
                                number={num}
                                status={teethStatus[num]}
                                onClick={onToothClick}
                            />
                        </div>
                    ))}
                </div>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap gap-4 mt-8 justify-center text-sm">
                {Object.entries(STATUS_COLORS).map(([status, color]) => (
                    <div key={status} className="flex items-center gap-2">
                        <div className={`w-4 h-4 rounded-sm border ${color}`} />
                        <span className="text-slate-600">{status === 'Healthy' ? 'سليم' : status}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
