import React, { useState, useEffect } from 'react';
import ToothSegmentMap from './ToothSegmentMap';
import { PROCEDURE_CATEGORIES, TOOTH_STATUS_OPTIONS } from './dentalData';

export default function DentalSidePanelV2({ activeTooth, procedures, onAddProcedure, chartSelectedSegments = [] }) {
    const [selectedSegments, setSelectedSegments] = useState([]);

    // UI State
    const [view, setView] = useState('ADD'); // ADD | HISTORY
    const [selectedCategory, setSelectedCategory] = useState('restorative');
    const [selectedProcedure, setSelectedProcedure] = useState(null);
    const [quickStatus, setQuickStatus] = useState(null); // For fast status updates

    // Form inputs
    const [price, setPrice] = useState(0);
    const [notes, setNotes] = useState('');

    // Sync Chart Selection
    useEffect(() => {
        if (chartSelectedSegments && chartSelectedSegments.length > 0) {
            setSelectedSegments(chartSelectedSegments);
        } else if (chartSelectedSegments.length === 0) {
            // Keep user selection if they are working on it, unless they clicked a different tooth
            setSelectedSegments([]);
        }
    }, [chartSelectedSegments, activeTooth]);

    if (!activeTooth) return <div className="p-6 text-center text-slate-400 font-medium">Select a tooth to begin</div>;

    const handleCategoryClick = (catId) => {
        setSelectedCategory(catId);
        setSelectedProcedure(null); // Reset procedure when category changes
    };

    const handleProcedureSelect = (proc) => {
        setSelectedProcedure(proc);
        setPrice(proc.price);
        // Auto-select segments if needed or whole tooth logic
        if (proc.isWholeTooth) {
            setSelectedSegments([]); // Clear segments for whole tooth
        }
    };

    const toggleSegment = (seg) => {
        if (selectedProcedure?.isWholeTooth) return; // Block segment picking for whole tooth procs
        setSelectedSegments(prev => prev.includes(seg) ? prev.filter(s => s !== seg) : [...prev, seg]);
    };

    const handleSubmit = () => {
        if (selectedProcedure) {
            onAddProcedure({
                tooth: activeTooth,
                type: selectedProcedure.id, // ID maps to internal logic (color etc)
                label: selectedProcedure.label,
                segments: selectedProcedure.isWholeTooth ? [] : selectedSegments,
                price,
                date: new Date().toISOString().split('T')[0],
                isWholeTooth: selectedProcedure.isWholeTooth
            });
            // Reset
            setNotes('');
            setView('HISTORY');
        }
    };

    const handleQuickStatus = (status) => {
        // Defines general status (missing, sound, etc.)
        // In a real app this might be a separate API call "updateToothStatus"
        // Here we add it as a "Status Change" procedure event or similar
        onAddProcedure({
            tooth: activeTooth,
            type: status.code.toLowerCase(), // e.g., missing
            label: `Marked as ${status.label}`,
            segments: [],
            price: 0,
            date: new Date().toISOString().split('T')[0],
            isStatusChange: true
        });
        setQuickStatus(status.id);
    };

    return (
        <div className="w-96 bg-white border-l border-slate-200 flex flex-col h-full shadow-2xl z-20 font-sans">
            {/* Header */}
            <div className="p-4 bg-slate-900 text-white shrink-0">
                <div className="flex justify-between items-center mb-2">
                    <h2 className="text-2xl font-bold">Tooth #{activeTooth}</h2>
                    <span className="text-xs bg-slate-700 px-2 py-1 rounded">Universal</span>
                </div>

                {/* Tabs */}
                <div className="flex gap-1 p-1 bg-slate-800 rounded-lg">
                    <button
                        onClick={() => setView('ADD')}
                        className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all ${view === 'ADD' ? 'bg-blue-500 text-white shadow-sm' : 'text-slate-400 hover:text-white'}`}
                    >
                        Treatment
                    </button>
                    <button
                        onClick={() => setView('HISTORY')}
                        className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all ${view === 'HISTORY' ? 'bg-blue-500 text-white shadow-sm' : 'text-slate-400 hover:text-white'}`}
                    >
                        History ({procedures.filter(p => p.tooth === activeTooth).length})
                    </button>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto bg-slate-50">
                {view === 'ADD' && (
                    <div className="p-4 space-y-6">

                        {/* 1. Quick Status (Always visible on top) */}
                        <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm">
                            <h4 className="text-xs font-bold text-slate-400 uppercase mb-2 text-right">الحالة العامة</h4>
                            <div className="flex flex-wrap gap-2 justify-end">
                                {TOOTH_STATUS_OPTIONS.map(s => (
                                    <button
                                        key={s.id}
                                        onClick={() => handleQuickStatus(s)}
                                        className={`px-3 py-1 rounded-full text-[10px] font-bold transition-all border ${quickStatus === s.id ? 'bg-slate-800 text-white border-slate-800' : 'bg-slate-50 text-slate-600 border-slate-200 hover:border-slate-300'}`}
                                    >
                                        {s.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* 2. Categories */}
                        <div>
                            <h4 className="text-xs font-bold text-slate-400 uppercase mb-2 text-right">التصنيف</h4>
                            <div className="grid grid-cols-4 gap-1">
                                {PROCEDURE_CATEGORIES.map(cat => (
                                    <button
                                        key={cat.id}
                                        onClick={() => handleCategoryClick(cat.id)}
                                        className={`flex flex-col items-center justify-center p-2 rounded-xl transition-all border ${selectedCategory === cat.id ? 'bg-blue-50 border-blue-500 text-blue-700' : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-100'}`}
                                    >
                                        <span className="text-xl mb-1">{cat.icon}</span>
                                        <span className="text-[9px] font-bold text-center leading-tight">{cat.label.split(' ')[0]}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* 3. Procedures List */}
                        <div>
                            <h4 className="text-xs font-bold text-slate-400 uppercase mb-2 text-right">الإجراءات المتاحة</h4>
                            <div className="space-y-1">
                                {PROCEDURE_CATEGORIES.find(c => c.id === selectedCategory)?.items.map(proc => (
                                    <button
                                        key={proc.id}
                                        onClick={() => handleProcedureSelect(proc)}
                                        className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all text-right ${selectedProcedure?.id === proc.id ? 'bg-blue-600 border-blue-600 text-white shadow-md' : 'bg-white border-slate-200 text-slate-700 hover:border-blue-300'}`}
                                    >
                                        <span className="font-bold text-sm">{proc.label}</span>
                                        <span className={`text-xs ${selectedProcedure?.id === proc.id ? 'text-blue-200' : 'text-slate-400'}`}>{proc.price} LE</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* 4. Details Panel (Shows when procedure selected) */}
                        {selectedProcedure && (
                            <div className="animate-in slide-in-from-bottom-5 fade-in duration-300 bg-white border border-blue-100 rounded-xl p-4 shadow-lg ring-1 ring-blue-50">

                                {/* Segments (If required) */}
                                {selectedProcedure.requiresSegments && !selectedProcedure.isWholeTooth && (
                                    <div className="mb-4 text-center">
                                        <h5 className="text-xs font-bold text-slate-400 mb-2">تحديد الأسطح</h5>
                                        <ToothSegmentMap selectedSegments={selectedSegments} onToggleSegment={toggleSegment} />
                                    </div>
                                )}

                                <div className="flex gap-2">
                                    <div className="flex-1">
                                        <label className="text-[10px] font-bold text-slate-400 block mb-1">السعر النهائي</label>
                                        <input
                                            type="number"
                                            value={price}
                                            onChange={(e) => setPrice(e.target.value)}
                                            className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-bold"
                                        />
                                    </div>
                                    <button
                                        onClick={handleSubmit}
                                        className="flex-[2] bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-md transition-all active:scale-95"
                                    >
                                        Confirm
                                    </button>
                                </div>
                            </div>
                        )}

                    </div>
                )}

                {view === 'HISTORY' && (
                    <div className="p-4 space-y-2">
                        {procedures.filter(p => p.tooth === activeTooth).length === 0 && <div className="text-center text-slate-400 text-sm py-10">No history</div>}

                        {procedures.filter(p => p.tooth === activeTooth).map((proc, idx) => (
                            <div key={idx} className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm flex justify-between items-center group">
                                <div dir="rtl">
                                    <div className="font-bold text-slate-800 text-sm">{proc.label}</div>
                                    <div className="text-[10px] text-slate-400">{proc.date} • {proc.segments?.join(', ')}</div>
                                </div>
                                <div className="text-right">
                                    <div className="font-mono text-xs font-bold text-blue-600">{proc.price}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
