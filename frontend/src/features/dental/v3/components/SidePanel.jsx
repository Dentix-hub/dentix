import { useState } from 'react';
import { PROCEDURE_TYPES, PROCEDURE_STATUS, SEGMENTS } from '../assets/dentalConstants';
export default function SidePanel({ activeTooth, procedures, onAddProcedure }) {
    // Mode: VIEW | WIZARD
    const [mode, setMode] = useState('VIEW');
    // Wizard State
    const [wizStep, setWizStep] = useState(1);
    const [newProc, setNewProc] = useState({ type: null, segments: [], price: 0, notes: '' });
    if (!activeTooth) return <div className="w-full h-full flex items-center justify-center text-slate-400">Select a tooth</div>;
    const toothProcs = procedures.filter(p => p.tooth === activeTooth).sort((a, b) => new Date(b.date) - new Date(a.date));
    // --- WIZARD HANDLERS ---
    const startWizard = () => {
        setMode('WIZARD');
        setWizStep(1);
        setNewProc({ type: null, segments: [], price: 0, notes: '' });
    };
    const handleTypeSelect = (typeKey) => {
        const typeDef = PROCEDURE_TYPES[typeKey];
        setNewProc(prev => ({ ...prev, type: typeKey.toLowerCase(), price: 0 })); // Reset price or set default
        if (typeDef.isWholeTooth || typeDef.isRoot) {
            // Skip segment selection
            setWizStep(3);
        } else {
            setWizStep(2);
        }
    };
    const toggleSegment = (seg) => {
        setNewProc(prev => ({
            ...prev,
            segments: prev.segments.includes(seg)
                ? prev.segments.filter(s => s !== seg)
                : [...prev.segments, seg]
        }));
    };
    const commitProcedure = () => {
        onAddProcedure({
            ...newProc,
            tooth: activeTooth,
            status: PROCEDURE_STATUS.COMPLETED,
            date: new Date().toISOString()
        });
        setMode('VIEW');
    };
    return (
        <div className="w-96 bg-white flex flex-col h-full shadow-2xl border-l border-slate-100 font-sans">
            {/* HEADER */}
            <div className="p-6 bg-slate-900 text-white">
                <div className="flex justify-between items-baseline mb-2">
                    <h2 className="text-3xl font-bold">#{activeTooth}</h2>
                    <span className="opacity-50 text-sm">Universal System</span>
                </div>
                {/* Tooth Status Summary */}
                <div className="flex gap-2">
                    <span className="px-2 py-1 bg-slate-800 rounded text-xs">Status: Healthy</span>
                </div>
            </div>
            {/* CONTENT AREA */}
            <div className="flex-1 overflow-y-auto bg-slate-50 p-4">
                {/* MODE: VIEW TIMELINE */}
                {mode === 'VIEW' && (
                    <div className="space-y-6">
                        <div className="flex justify-between items-center">
                            <h3 className="font-bold text-slate-700">Timeline</h3>
                            <button
                                onClick={startWizard}
                                className="bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm font-bold shadow-lg shadow-blue-200 hover:bg-blue-700 transition"
                            >
                                + Add Procedure
                            </button>
                        </div>
                        <div className="space-y-4 relative before:absolute before:inset-y-0 before:left-4 before:w-0.5 before:bg-slate-200">
                            {toothProcs.length === 0 && (
                                <p className="text-center text-slate-400 text-sm py-4 ml-8">No medical history</p>
                            )}
                            {toothProcs.map(proc => (
                                <div key={proc.id} className="relative pl-8">
                                    {/* Dot */}
                                    <div className={`absolute left-[13px] top-3 w-2 h-2 rounded-full ring-4 ring-slate-50 ${proc.status === 'completed' ? 'bg-green-500' : 'bg-slate-400'
                                        }`} />
                                    {/* Card */}
                                    <div className="bg-white p-3 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition">
                                        <div className="flex justify-between mb-1">
                                            <span className="font-bold text-slate-800">
                                                {PROCEDURE_TYPES[proc.type.toUpperCase()]?.label || proc.type}
                                            </span>
                                            <span className="text-xs text-slate-400 font-mono">
                                                {new Date(proc.date).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <div className="text-xs text-slate-500 mb-2">
                                            {proc.segments?.join(', ')}
                                        </div>
                                        {proc.notes && (
                                            <div className="bg-slate-50 p-2 rounded text-xs text-slate-600 mb-2">
                                                {proc.notes}
                                            </div>
                                        )}
                                        <div className="flex justify-end gap-2">
                                            <button className="text-[10px] text-red-400 hover:text-red-600 font-bold">Remove</button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
                {/* MODE: WIZARD STEP 1 (TYPE) */}
                {mode === 'WIZARD' && wizStep === 1 && (
                    <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                        <button onClick={() => setMode('VIEW')} className="text-slate-400 text-xs mb-4">← Cancel</button>
                        <h3 className="font-bold text-lg mb-4">Select Procedure</h3>
                        <div className="grid grid-cols-2 gap-2">
                            {Object.entries(PROCEDURE_TYPES).map(([key, def]) => (
                                <button
                                    key={key}
                                    onClick={() => handleTypeSelect(key)}
                                    className="p-3 text-left bg-white border border-slate-200 rounded-xl hover:border-blue-500 hover:ring-1 hover:ring-blue-500 transition group"
                                >
                                    <div className="font-bold text-slate-700 group-hover:text-blue-600">{def.label}</div>
                                    <div className="text-[10px] text-slate-400 capitalize">{def.category}</div>
                                </button>
                            ))}
                        </div>
                    </div>
                )}
                {/* MODE: WIZARD STEP 2 (SEGMENTS) */}
                {mode === 'WIZARD' && wizStep === 2 && (
                    <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                        <button onClick={() => setWizStep(1)} className="text-slate-400 text-xs mb-4">← Back</button>
                        <h3 className="font-bold text-lg mb-4">Select Segments</h3>
                        <div className="flex flex-wrap gap-2 justify-center py-8">
                            {/* Mock Segment Selector Visual */}
                            <div className="relative w-32 h-32 bg-slate-100 rounded-full flex items-center justify-center">
                                {Object.values(SEGMENTS).map(seg => (
                                    <button
                                        key={seg}
                                        onClick={() => toggleSegment(seg)}
                                        className={`absolute w-10 h-10 rounded-full text-[10px] font-bold transition-all
                                            ${newProc.segments.includes(seg) ? 'bg-blue-600 text-white scale-110' : 'bg-white text-slate-500 shadow-sm hover:scale-105'}
                                            ${seg === 'Occlusal' ? 'inset-0 m-auto z-10' : ''}
                                            ${seg === 'Mesial' ? 'left-0 top-1/2 -translate-y-1/2' : ''}
                                            ${seg === 'Distal' ? 'right-0 top-1/2 -translate-y-1/2' : ''}
                                            ${seg === 'Buccal' ? 'top-0 left-1/2 -translate-x-1/2' : ''}
                                            ${seg === 'Lingual' ? 'bottom-0 left-1/2 -translate-x-1/2' : ''}
                                        `}
                                    >
                                        {seg[0]}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <button
                            onClick={() => setWizStep(3)}
                            disabled={newProc.segments.length === 0}
                            className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold disabled:opacity-50"
                        >
                            Next Step →
                        </button>
                    </div>
                )}
                {/* MODE: WIZARD STEP 3 (DETAILS) */}
                {mode === 'WIZARD' && wizStep === 3 && (
                    <div className="animate-in fade-in slide-in-from-right-4 duration-300">
                        <button onClick={() => setWizStep(newProc.segments.length ? 2 : 1)} className="text-slate-400 text-xs mb-4">← Back</button>
                        <h3 className="font-bold text-lg mb-4">Procedure Details</h3>
                        <div className="space-y-4">
                            <div>
                                <label className="text-xs font-bold text-slate-500 block mb-1">Notes</label>
                                <textarea
                                    className="w-full p-3 bg-white border border-slate-200 rounded-xl text-sm"
                                    rows={3}
                                    placeholder="Clinical notes..."
                                    value={newProc.notes}
                                    onChange={(e) => setNewProc(prev => ({ ...prev, notes: e.target.value }))}
                                />
                            </div>
                            <div>
                                <label className="text-xs font-bold text-slate-500 block mb-1">Price</label>
                                <input
                                    type="number"
                                    className="w-full p-3 bg-white border border-slate-200 rounded-xl font-bold"
                                    value={newProc.price}
                                    onChange={(e) => setNewProc(prev => ({ ...prev, price: Number(e.target.value) }))}
                                />
                            </div>
                        </div>
                        <button
                            onClick={commitProcedure}
                            className="w-full mt-8 bg-green-500 hover:bg-green-600 text-white py-3 rounded-xl font-bold shadow-lg shadow-green-200 transition"
                        >
                            Confirm Procedure ✓
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
