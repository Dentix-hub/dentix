import React, { useState } from 'react';
import AdvancedTooth from './components/AdvancedTooth';
import SidePanel from './components/SidePanel';
import { PROCEDURE_STATUS } from './assets/dentalConstants';

export default function DentalChartContainer() {
    const [activeTooth, setActiveTooth] = useState(null);

    // MOCK DATABASE
    const [procedures, setProcedures] = useState([
        { id: 'p1', tooth: 3, type: 'filling', segments: ['Occlusal'], status: 'completed', date: '2023-01-01', notes: 'Old amalgam' },
        { id: 'p2', tooth: 3, type: 'filling', segments: ['Mesial'], status: 'completed', date: '2023-06-01', notes: 'Recurrent decay' },
        { id: 'p3', tooth: 14, type: 'rct', segments: [], status: 'completed', date: '2023-02-15' },
        { id: 'p4', tooth: 14, type: 'crown', segments: [], status: 'completed', date: '2023-03-01' },
    ]);

    const handleAddProcedure = (procData) => {
        const newProc = {
            id: `p${Date.now()}`, // Temporary ID
            ...procData,
            status: PROCEDURE_STATUS.COMPLETED
        };
        setProcedures(prev => [...prev, newProc]);
    };

    return (
        <div className="flex h-screen bg-slate-50 overflow-hidden">

            {/* MAIN CHART AREA */}
            <div className="flex-1 flex flex-col relative overflow-hidden">
                {/* TOOLBAR (Optional for v3 if Wizard is primary) */}
                <div className="h-16 bg-white border-b border-slate-200 flex items-center px-6 justify-between z-10">
                    <h1 className="font-bold text-slate-800 tracking-tight">Advanced Dental Chart <span className="text-blue-500 text-xs uppercase bg-blue-50 px-2 py-1 rounded ml-2">v3.0 Production</span></h1>
                    <div className="flex gap-2">
                        <button className="text-xs font-bold text-slate-500 bg-slate-100 px-3 py-1.5 rounded hover:bg-slate-200">Print Record</button>
                        <button className="text-xs font-bold text-blue-600 bg-blue-50 px-3 py-1.5 rounded hover:bg-blue-100">Treatment Plan Mode</button>
                    </div>
                </div>

                {/* CANVAS */}
                <div className="flex-1 overflow-auto p-10 flex items-center justify-center bg-slate-100/50">
                    <div className="bg-white p-12 rounded-[3rem] shadow-xl border border-white/50 backdrop-blur min-w-[1000px] flex flex-col gap-12 relative">

                        {/* Upper Arch */}
                        <div className="flex justify-center gap-1">
                            {Array.from({ length: 16 }, (_, i) => i + 1).map(num => (
                                <AdvancedTooth
                                    key={num}
                                    number={num}
                                    procedures={procedures.filter(p => p.tooth === num)}
                                    isActive={activeTooth === num}
                                    onToothClick={setActiveTooth}
                                />
                            ))}
                        </div>

                        {/* Lower Arch */}
                        <div className="flex justify-center gap-1 border-t-2 border-dashed border-slate-100 pt-12 relative">
                            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-slate-200 text-slate-500 text-[10px] px-3 py-0.5 rounded-full font-bold">LOWER JAW</div>
                            {Array.from({ length: 16 }, (_, i) => 32 - i).map(num => (
                                <AdvancedTooth
                                    key={num}
                                    number={num}
                                    procedures={procedures.filter(p => p.tooth === num)}
                                    isActive={activeTooth === num}
                                    onToothClick={setActiveTooth}
                                />
                            ))}
                        </div>

                    </div>
                </div>
            </div>

            {/* SIDE PANEL */}
            <div className={`transition-all duration-500 ease-in-out ${activeTooth ? 'w-96 translate-x-0' : 'w-0 translate-x-full opacity-0'} relative z-20`}>
                {activeTooth && (
                    <SidePanel
                        activeTooth={activeTooth}
                        procedures={procedures}
                        onAddProcedure={handleAddProcedure}
                    />
                )}
            </div>

        </div>
    );
}
