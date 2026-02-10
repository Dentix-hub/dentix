import { useState } from 'react';
import SegmentedTooth from './SegmentedTooth';
import DentalSidePanelV2 from './DentalSidePanelV2';
// TOOL CONFIGURATION
const TOOLS = [
    { id: 'cursor', label: 'تحديد', icon: '👆', color: 'bg-slate-800' },
    { id: 'exam', label: 'كشف', icon: '🔍', color: 'bg-blue-600', code: 'D0120' },
    { id: 'filling', label: 'حشو', icon: '🦷', color: 'bg-indigo-600', code: 'D2391' },
    { id: 'rct', label: 'عصب', icon: '⚡', color: 'bg-red-600', code: 'D3330', isWholeTooth: true },
    { id: 'crown', label: 'طربوش', icon: '👑', color: 'bg-yellow-500', code: 'D2740', isWholeTooth: true },
    { id: 'extract', label: 'خلع', icon: '❌', color: 'bg-slate-500', code: 'D7140', isWholeTooth: true },
    { id: 'clear', label: 'مسح', icon: '🧹', color: 'bg-white text-red-500 border border-red-200' },
];
export default function DentalChartV2() {
    const [activeTooth, setActiveTooth] = useState(null);
    const [selectedSegments, setSelectedSegments] = useState({});
    const [activeTool, setActiveTool] = useState('cursor');
    // Procedure History
    const [procedures, setProcedures] = useState([
        { tooth: 3, type: 'filling', label: 'حشو كمبوزيت', segments: ['Occlusal'], date: '2023-10-10', price: 450 },
        { tooth: 14, type: 'rct', label: 'علاج عصب', segments: [], date: '2023-09-01', isWholeTooth: true },
    ]);
    // Derived Status
    const getToothStatus = (toothId) => {
        const procs = procedures.filter(p => p.tooth === toothId);
        if (procs.some(p => p.type === 'extract')) return 'Missing';
        if (procs.some(p => p.type === 'crown')) return 'Crown';
        if (procs.some(p => p.type === 'rct')) return 'RCT';
        return 'Sound';
    };
    // --- INTERACTION LOGIC ---
    const handleToothClick = (toothId) => {
        if (activeTool === 'cursor') {
            setActiveTooth(toothId);
            return;
        }
        // TOOL ACTION: Whole Tooth (RCT, Crown, Extract)
        const tool = TOOLS.find(t => t.id === activeTool);
        if (tool.isWholeTooth) {
            applyProcedure(toothId, tool, []);
        } else if (tool.id === 'clear') {
            // Remove procedures for this tooth
            setProcedures(prev => prev.filter(p => p.tooth !== toothId));
        } else {
            // If tool is segment-based (Exam/Filling) but clicked on root/body, 
            // maybe just select the tooth? Or apply to all? 
            // Let's open panel for detail if ambiguous, or select tooth.
            setActiveTooth(toothId);
        }
    };
    const handleSegmentClick = (toothId, segment) => {
        if (activeTool === 'cursor') {
            setActiveTooth(toothId);
            setSelectedSegments(prev => {
                const current = prev[toothId] || [];
                const updated = current.includes(segment) ? current.filter(s => s !== segment) : [...current, segment];
                return { ...prev, [toothId]: updated };
            });
            return;
        }
        // TOOL ACTION: Segment Based (Filling)
        const tool = TOOLS.find(t => t.id === activeTool);
        if (!tool.isWholeTooth && tool.id !== 'clear') {
            applyProcedure(toothId, tool, [segment]);
        }
    };
    const applyProcedure = (toothId, tool, segments) => {
        const newProc = {
            tooth: toothId,
            type: tool.id,
            label: tool.label, // Simplified label
            code: tool.code,
            segments: segments,
            price: 0, // Should come from a pricelist lookup in real app
            isWholeTooth: tool.isWholeTooth,
            date: new Date().toISOString().split('T')[0]
        };
        // If whole tooth, maybe remove existing conflicting whole tooth procs?
        // e.g. cant be missing AND crown.
        setProcedures(prev => {
            let filtered = prev;
            if (tool.isWholeTooth) {
                // If adding Extract, remove Crowns/RCTs? Or keep history?
                // Usually keep history. But for visual "Current State", latest wins.
            }
            return [...filtered, newProc];
        });
    };
    const handleAddFromPanel = (data) => {
        setProcedures(prev => [...prev, data]);
        setSelectedSegments(prev => ({ ...prev, [data.tooth]: [] }));
    };
    return (
        <div className="flex h-screen bg-slate-50 overflow-hidden font-sans" dir="rtl">
            <div className="flex-1 flex flex-col relative">
                {/* 1. SMART TOOLBAR */}
                <div className="h-20 bg-white border-b border-slate-200 flex items-center px-4 justify-between shadow-[0_4px_12px_rgba(0,0,0,0.02)] z-30 shrink-0">
                    <div className="flex items-center gap-2 overflow-x-auto py-2 no-scrollbar">
                        {TOOLS.map(tool => (
                            <button
                                key={tool.id}
                                onClick={() => setActiveTool(tool.id)}
                                className={`
                                    flex flex-col items-center justify-center min-w-[4rem] h-14 rounded-xl transition-all duration-200 border
                                    ${activeTool === tool.id
                                        ? `${tool.color.includes('white') ? 'bg-slate-100' : tool.color} text-white border-transparent shadow-md scale-105`
                                        : 'bg-white border-slate-100 text-slate-500 hover:bg-slate-50 hover:border-slate-200'}
                                `}
                            >
                                <span className="text-xl mb-0.5">{tool.icon}</span>
                                <span className={`text-[10px] font-bold ${activeTool === tool.id ? 'text-white' : 'text-slate-500'}`}>{tool.label}</span>
                            </button>
                        ))}
                    </div>
                    {/* Mode Indicator */}
                    <div className="bg-slate-100 px-4 py-2 rounded-lg text-xs font-bold text-slate-500 border border-slate-200">
                        {activeTool === 'cursor' ? 'وضع التحديد (Selection Mode)' : `أداة نشطة: ${TOOLS.find(t => t.id === activeTool).label}`}
                    </div>
                </div>
                {/* 2. CHART AREA */}
                <div className={`flex-1 overflow-auto bg-slate-100/50 p-8 flex items-center justify-center relative cursor-${activeTool === 'cursor' ? 'default' : 'crosshair'}`}>
                    {/* Grid Background */}
                    <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 1px)', backgroundSize: '20px 20px' }} />
                    <div className="bg-white/80 backdrop-blur-sm p-12 rounded-[2.5rem] shadow-xl border border-white min-w-[1000px] flex flex-col gap-10 relative z-10 transition-all">
                        {/* Upper Arch */}
                        <div className="flex justify-center gap-2">
                            {Array.from({ length: 16 }, (_, i) => i + 1).map(num => (
                                <SegmentedTooth
                                    key={num}
                                    number={num}
                                    activeTool={activeTool}
                                    isActive={activeTooth === num}
                                    status={getToothStatus(num)}
                                    procedures={procedures.filter(p => p.tooth === num)}
                                    selectedSegments={selectedSegments[num] || []}
                                    onToothClick={handleToothClick}
                                    onSegmentClick={handleSegmentClick}
                                />
                            ))}
                        </div>
                        {/* Lower Arch */}
                        <div className="flex justify-center gap-2 border-t-2 border-dashed border-slate-100 pt-10 relative">
                            <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-slate-100 text-slate-400 text-[10px] px-2 rounded-full font-bold">LOWER ARCH</span>
                            {Array.from({ length: 16 }, (_, i) => 32 - i).map(num => (
                                <SegmentedTooth
                                    key={num}
                                    number={num}
                                    activeTool={activeTool}
                                    isActive={activeTooth === num}
                                    status={getToothStatus(num)}
                                    procedures={procedures.filter(p => p.tooth === num)}
                                    selectedSegments={selectedSegments[num] || []}
                                    onToothClick={handleToothClick}
                                    onSegmentClick={handleSegmentClick}
                                />
                            ))}
                        </div>
                    </div>
                </div>
            </div>
            {/* 3. SIDE PANEL */}
            <div className={`transition-all duration-300 ${activeTooth ? 'w-96 translate-x-0 opacity-100' : 'w-0 translate-x-full opacity-0'} overflow-hidden shadow-2xl z-40 bg-white`}>
                {activeTooth && (
                    <DentalSidePanelV2
                        activeTooth={activeTooth}
                        procedures={procedures}
                        onAddProcedure={handleAddFromPanel}
                        chartSelectedSegments={selectedSegments[activeTooth] || []}
                    />
                )}
            </div>
        </div>
    );
}
